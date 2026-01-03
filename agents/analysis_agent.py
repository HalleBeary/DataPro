import sqlite3
import json
import time
from typing import List, Tuple, Dict, Any
from openai import OpenAI

"""
USER QUERY: "Show me top 5 genres by track count"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    ANALYSIS AGENT                           │
│                                                             │
│  1. _get_schema()      → Reads tables/columns from SQLite   │
│                                                             │
│  2. _generate_sql()    → OpenAI converts NL to SQL          │
│                          "SELECT g.Name, COUNT(t.TrackId)   │
│                           FROM genres g JOIN tracks t..."   │
│                                                             │
│  3. _execute_sql()     → Runs SQL, gets raw rows            │
│                                                             │
│  4. Structure output   → Converts to list of dicts          │
│                                                             │
│  OUTPUT:                                                    │
│  {                                                          │
│    "success": True,                                         │
│    "data": [{"Name": "Rock", "track_count": 1297}, ...],    │
│    "metadata": {"columns": [...], "sql": "..."}             │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
"""


class AnalysisAgent:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.max_retries = 3

    def run(self, query: str, database_path: str, context: dict = None) -> dict:
        """
        ReAct Loop: 
        1. Identifies tables -> 2. Gets Schema -> 3. Generates SQL -> 4. Observes Errors -> 5. Retries
        """
        try:
            # STEP 1: Schema Filtering (The "Pre-flight")
            relevant_tables = self._identify_relevant_tables(query, database_path)
            schema = self._get_detailed_schema(database_path, relevant_tables)

            # STEP 2: Initialize Message History for ReAct
            messages = [
                {"role": "system", "content": self._get_system_prompt(schema, context)},
                {"role": "user", "content": f"User Question: {query}"}
            ]

            # STEP 3: The ReAct Loop
            for attempt in range(self.max_retries):
                try:
                    # Generate SQL using tool calling
                    sql, explanation = self._generate_sql(messages)
                    
                    # Execute SQL
                    results, columns = self._execute_sql(database_path, sql)

                    # Success! Structure and return
                    data = [dict(zip(columns, row)) for row in results]
                    return {
                        "success": True,
                        "data": data,
                        "metadata": {
                            "columns": columns,
                            "sql": sql,
                            "explanation": explanation,
                            "tables_used": relevant_tables
                        }
                    }

                except Exception as e:
                    # SELF-CORRECTION: Feed the error back to the LLM
                    error_msg = str(e)
                    print(f"⚠️ Attempt {attempt + 1} failed. Error: {error_msg}")
                    
                    messages.append({"role": "assistant", "content": f"Thought: My previous SQL failed. I will fix it.\nSQL: {sql}"})
                    messages.append({
                        "role": "user", 
                        "content": f"That query failed with this error: {error_msg}. Please check the schema, fix the SQL syntax or logic, and try again."
                    })

            raise Exception("Maximum retries reached. Could not generate valid SQL.")

        except Exception as e:
            return {"success": False, "error": str(e), "data": [], "metadata": {}}

    def _identify_relevant_tables(self, query: str, database_path: str) -> List[str]:
        """Ask a cheaper model to pick only the necessary tables."""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        prompt = (
            f"Given the user query: '{query}'\n"
            f"And these SQLite tables: {', '.join(all_tables)}\n"
            "Return a JSON object with a key 'tables' containing a list of table names "
            "needed to answer the query. Only include tables that are absolutely necessary."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("tables", [])

    def _get_detailed_schema(self, database_path: str, tables: List[str]) -> str:
        """Extract schema only for the filtered list of tables."""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        schema_parts = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info(\"{table}\")")
            columns = cursor.fetchall()
            col_strings = [f"  {c[1]} ({c[2]})" for c in columns]
            schema_parts.append(f"Table: \"{table}\"\n" + "\n".join(col_strings))
        conn.close()
        return "\n\n".join(schema_parts)

    def _get_system_prompt(self, schema: str, context: dict) -> str:
        return f"""You are a SQL expert. Generate SQLite-compatible SQL queries.

DATABASE SCHEMA:
{schema}

STRICT RULES:
1. READ-ONLY: Generate ONLY 'SELECT' statements.
2. NO SELECT ALL: Never use 'SELECT *'. Specify columns.
3. QUOTING: Wrap table and column names in double quotes (e.g. "Order").
4. NULL SAFETY: Use COALESCE(col, 0) or IFNULL for numeric aggregations.
5. ALIASES: Use clear, descriptive names for calculated columns.
6. LIMIT: Always limit results to 100 rows unless specified.
7. ERROR HANDLING: If you receive a SQL error, analyze it and fix your query.

CONTEXT:
{json.dumps(context) if context else "No previous context."}
"""

    def _generate_sql(self, messages: List[Dict]) -> Tuple[str, str]:
        """Call OpenAI to generate the SQL."""
        tools = [{
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "Run the SQL query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "explanation": {"type": "string"}
                    },
                    "required": ["sql", "explanation"]
                }
            }
        }]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "execute_sql"}},
            temperature=0
        )

        tool_call = response.choices[0].message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        return args["sql"], args["explanation"]

    def _execute_sql(self, database_path: str, sql: str) -> Tuple[List, List]:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            columns = [d[0] for d in cursor.description]
            return results, columns
        finally:
            conn.close()