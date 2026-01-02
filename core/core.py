import os
import yaml
from agents.analysis_agent import AnalysisAgent
from agents.visualization_agent import VisualizationAgent


class Core:
    def __init__(self, config_path: str = "config", api_key: str = None):
        self.config_path = config_path
        self.api_key = api_key
        
        # Load configs
        self.databases = self._load_yaml("databases.yaml")
        self.users = self._load_yaml("users.yaml")
        
        # Initialize agents
        self.analysis_agent = AnalysisAgent(api_key=api_key)
        self.visualization_agent = VisualizationAgent(api_key=api_key)

    def _load_yaml(self, filename: str) -> dict:
        """Load a YAML config file"""
        filepath = os.path.join(self.config_path, filename)
        with open(filepath, "r") as f:
            return yaml.safe_load(f)

    def list_databases(self) -> list:
        """Return available database names"""
        return list(self.databases["databases"].keys())

    def list_users(self) -> list:
        """Return available usernames"""
        return list(self.users["users"].keys())

    def check_access(self, user: str, database: str) -> bool:
        """Check if user has access to database"""
        if user not in self.users["users"]:
            return False
        allowed = self.users["users"][user].get("allowed_databases", [])
        return database in allowed

    def get_database_path(self, database: str) -> str:
        """Get file path for a database"""
        return self.databases["databases"][database]["path"]


    def get_allowed_databases(self, user: str) -> list: # connect users to allowed databases automatically.
        """Get list of databases user can access"""
        if user not in self.users["users"]:
            return []
        return self.users["users"][user].get("allowed_databases", [])
    
    def run(self, user: str, database: str, query: str) -> dict: 
        """
        Core pipeline:

        1. Check permissions (User restrictions)
        2. Run Analysis Agent
        3. Run Visualization Agent
        4. Return results
        """
        # Step 1: Check permissions
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
            database_path=db_path
        )

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