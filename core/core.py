import os
import yaml
from agents.analysis_agent import AnalysisAgent
from agents.visualization_agent import VisualizationAgent


class Core:

    """
    Core pipeline of Data Analysis & Visualization Twin-Agent:

    1. Check user permissions: Is user in system, and does it have access to database it tries to access. Ensure user restriction via yaml files. 
    2. Run Analysis Agent: Analyzes user query and passes SQL data to Visualization agent.
    3. Run Visualization Agent: Decides how to visualize data and generates appropriate graph
    4. Return combined results

    Input: active user and requested database, user query and context from previous query (if available)
    Returns: Dictionary with analysis and visualization results.     

    """

    def __init__(self, config_path: str = "config", api_key: str = None):
        self.config_path = config_path
        self.api_key = api_key
        
        # Load configs on init: 
        self.databases = self._load_yaml("databases.yaml")
        self.users = self._load_yaml("users.yaml")
        
        # Initialize agents
        self.analysis_agent = AnalysisAgent(api_key=api_key)
        self.visualization_agent = VisualizationAgent(api_key=api_key)


    def _load_yaml(self, filename: str) -> dict:
        filepath = os.path.join(self.config_path, filename)
        with open(filepath, "r") as f:
            return yaml.safe_load(f)

    def list_databases(self) -> list:
        return list(self.databases["databases"].keys())

    def list_users(self) -> list:
        return list(self.users["users"].keys())

    def check_access(self, user: str, database: str) -> bool:
        if user not in self.users["users"]:
            return False
        allowed = self.users["users"][user].get("allowed_databases", [])
        return database in allowed

    def get_database_path(self, database: str) -> str:
        return self.databases["databases"][database]["path"]


    def get_allowed_databases(self, user: str) -> list: # connect users to allowed databases automatically.
        if user not in self.users["users"]:
            return []
        return self.users["users"][user].get("allowed_databases", [])
    
    def run(self, user: str, database: str, query: str, context: dict = None) -> dict:

        # Step 1: Check permissions of user 
        if user not in self.users["users"]: 
            return {
                "success": False,
                "error": f"Unknown user: '{user}'"
            }

        if not self.check_access(user, database): 
            return {
                "success": False,
                "error": f"Access denied: '{user}' cannot access '{database}'"
            }

        # Step 2: Get database path
        if database not in self.databases["databases"]:
            return {
                "success": False,
                "error": f"Unknown database: '{database}'"
            }
        
        db_path = self.get_database_path(database)

        # Step 3: Run Analysis Agent

        print(f"🔍 Analyzing: {query}")
        analysis_result = self.analysis_agent.run(
            query=query,
            database_path=db_path,
            context=context
        )

        # Add source to metadata
        if analysis_result.get("success"):
            analysis_result["metadata"]["source"] = database

        if not analysis_result["success"]:
            return {
                "success": False,
                "error": f"Analysis failed: {analysis_result.get('error', 'Unknown error')}",
                "analysis": analysis_result
            }

        # Step 4: Run Visualization Agent
        print(f"📊 Generating visualization...")
        viz_result = self.visualization_agent.run(
            data=analysis_result["data"],
            metadata=analysis_result["metadata"],
            user_query=query
        )

        # If visualization failed:
        if not viz_result["success"]:
            return {
                "success": False,
                "error": f"Visualization failed: {viz_result.get('error', 'Unknown error')}",
                "analysis": analysis_result,
                "visualization": viz_result
            }

        # Step 5: Return combined results
        return {
            "success": True,
            "user": user,
            "database": database,
            "query": query,
            "analysis": analysis_result,
            "visualization": viz_result
        }