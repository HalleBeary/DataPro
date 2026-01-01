import sqlite3
import json
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
│  2. _generate_sql()    → OpenAI converts NL to SQL ⭐       │
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


# IMRPOVEMENT COULD BE USING REACT LOOP

class AnalysisAgent:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def run(self, query: str, database_path: str) -> dict:
        """
        Main entry point: natural language query → structured data
        """
        try:
            # Step 1: Get database schema
            schema = self._get_schema(database_path)

            # Step 2: Generate SQL from natural language
            sql = self._generate_sql(query, schema)

            # Step 3: Execute SQL
            results, columns = self._execute_sql(database_path, sql)

            # Step 4: Structure output
            data = [dict(zip(columns, row)) for row in results]

            return {
                "success": True,
                "data": data,
                "metadata": {
                    "columns": columns,
                    "row_count": len(data),
                    "sql": sql
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "metadata": {}
            }

    def _get_schema(self, database_path: str) -> str:
        """
        Extract schema from SQLite database
        """
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        schema_parts = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            column_defs = [f"  {col[1]} ({col[2]})" for col in columns]
            schema_parts.append(f"{table}:\n" + "\n".join(column_defs))

        conn.close()
        return "\n\n".join(schema_parts)

    def _generate_sql(self, query: str, schema: str) -> str:
        """
        Use OpenAI to generate SQL from natural language
        """
        system_prompt = f"""You are a SQL expert. Generate SQLite-compatible SQL queries.

DATABASE SCHEMA:
{schema}

RULES:
- Return ONLY the SQL query, no explanations
- Use SQLite syntax
- Always limit results to 100 rows max unless user specifies
- Use appropriate JOINs when needed
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0
        )

        sql = response.choices[0].message.content.strip()
        
        # Clean up if wrapped in markdown code blocks
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1]  # Remove first line
            sql = sql.rsplit("```", 1)[0]  # Remove last ```
        
        return sql.strip()

    def _execute_sql(self, database_path: str, sql: str) -> tuple:
        """
        Execute SQL and return results + column names
        """
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        conn.close()
        return results, columns
    
