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
            """
            Main orchestration flow:
            1. Check permissions
            2. Run Analysis Agent
            3. Run Visualization Agent
            4. Return combined results
            """
            # Step 1 & 2: Permissions and Path (Keep your existing logic)
            if user not in self.users["users"]:
                return {"success": False, "error": f"Unknown user: '{user}'"}
            if not self.check_access(user, database):
                return {"success": False, "error": f"Access denied: '{user}'"}
            
            db_path = self.get_database_path(database)

            # Step 3: Run Analysis Agent (ReAct Loop)
            print(f"🔍 Analyzing with ReAct loop: {query}")
            analysis_result = self.analysis_agent.run(
                query=query,
                database_path=db_path,
                context=context
            )

            if not analysis_result["success"]:
                return {
                    "success": False,
                    "error": f"Analysis failed: {analysis_result.get('error')}",
                    "analysis": analysis_result
                }

            # Step 4: Run Visualization Agent (Plotly)
            print(f"📊 Generating Plotly visualization...")
            viz_result = self.visualization_agent.run(
                data=analysis_result["data"],
                metadata=analysis_result["metadata"],
                user_query=query
            )

            # Step 5: Return combined results
            return {
                "success": True,
                "user": user,
                "database": database,
                "query": query,
                "analysis": analysis_result, # Contains SQL, data, explanation
                "visualization": viz_result   # Contains html_path, png_path, insights
            }