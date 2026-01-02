import sqlite3
import json
import time
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    BadRequestError,
    APIError
)

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


# TODO IMRPOVEMENT COULD BE USING REACT LOOP ??

class AnalysisAgent:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.max_retries = 3

        # Define the tool for SQL execution
        self.tools = [{
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "Execute a SQL query on the SQLite database to answer the user's question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The SQLite-compatible SQL query to execute"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query does"
                        }
                    },
                    "required": ["sql", "explanation"]
                }
            }
        }]

    def run(self, query: str, database_path: str, context: dict = None) -> dict:
        """
        Main entry point: natural language query → structured data
        """
        try:
            # Step 1: Get database schema
            schema = self._get_schema(database_path)

            # Step 2: Generate SQL using function calling
            sql, explanation = self._generate_sql(query, schema, context)

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
                    "sql": sql,
                    "explanation": explanation
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

    def _generate_sql(self, query: str, schema: str, context: dict = None) -> tuple:
        """
        Use OpenAI function calling to generate SQL from natural language
        """
        # Build context string if available
        context_str = ""
        if context:
            suggestions_str = ""
            if context.get("previous_suggestions"):
                suggestions_str = f"\nPREVIOUS SUGGESTIONS: {context.get('previous_suggestions')}"
            
            context_str = f"""
PREVIOUS QUERY: {context.get('previous_query', 'None')}
PREVIOUS RESULTS (first 10 rows): {context.get('previous_data', [])}{suggestions_str}

Use this context to understand references like "these", "those", "the same", "that suggestion", etc.
If user says "follow that suggestion" or similar, use the PREVIOUS SUGGESTIONS to determine what to do.
"""

        system_prompt = f"""You are a SQL expert. Generate SQLite-compatible SQL queries based on user questions.

DATABASE SCHEMA:
{schema}

{context_str}

RULES:
- Use the execute_sql function to run your query
- Use SQLite syntax only
- Always limit results to 100 rows max unless user specifies otherwise
- Use appropriate JOINs when data spans multiple tables
- Use clear column aliases for aggregations
- For time-based trends, prefer yearly aggregations unless user asks specifically for montly/daily
- If the user refers to previous results, use the context to understand what they mean
"""
    
# Rules why?

  #  RULES:
  #  - Return ONLY the SQL query, no explanations ----> No text around SQL query, else you need to get rid of "here is the query or other shit"
  #  - Use SQLite syntax ----> #Different from MySQL/PostgreSQL. Avoids incompatibility issues
  #  - Always limit results to 100 rows max unless user specifies ----> Safety, prevents returning millions rows by accident for example
  #  - Use appropriate JOINs when needed ---->   Encourages proper relational queries instead of lazy single-table selects

  # TODO How can this rule list be improved? 


        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    tools=self.tools,
                    tool_choice={"type": "function", "function": {"name": "execute_sql"}},
                    temperature=0
                )

                # Extract function call
                tool_call = response.choices[0].message.tool_calls[0]
                arguments = json.loads(tool_call.function.arguments)

                sql = arguments.get("sql", "")
                explanation = arguments.get("explanation", "")

                return sql, explanation

            except AuthenticationError:
                raise Exception("Invalid API key. Please check your OPENAI_API_KEY.")

            except RateLimitError:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise Exception("Rate limit exceeded. Please try again later.")

            except APIConnectionError:
                if attempt < self.max_retries - 1:
                    print("🔄 Connection error. Retrying...")
                    time.sleep(1)
                else:
                    raise Exception("Could not connect to OpenAI. Check your internet.")

            except BadRequestError as e:
                raise Exception(f"Invalid request: {str(e)}")

            except APIError as e:
                if attempt < self.max_retries - 1:
                    print("🔄 OpenAI server error. Retrying...")
                    time.sleep(1)
                else:
                    raise Exception(f"OpenAI error: {str(e)}")


    def _execute_sql(self, database_path: str, sql: str) -> tuple: # returns output and column names

        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        except sqlite3.Error as e:
            conn.close()
            raise Exception(f"SQL execution error: {str(e)}")

        conn.close()
        return results, columns
    





