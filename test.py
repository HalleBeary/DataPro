import os
from dotenv import load_dotenv
from agents.analysis_agent import AnalysisAgent
from agents.visualization_agent import VisualizationAgent

# Load API key from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# --- Test Analysis Agent ---
print("=" * 50)
print("TESTING ANALYSIS AGENT")
print("=" * 50)

analysis_agent = AnalysisAgent(api_key=api_key)
analysis_result = analysis_agent.run(
    query="Show me top 5 genres by number of tracks",
    database_path="./data/chinook.db"
)

print(f"\nSuccess: {analysis_result['success']}")
print(f"SQL: {analysis_result['metadata'].get('sql', 'N/A')}")
print(f"Rows: {analysis_result['metadata'].get('row_count', 0)}")
print(f"Data: {analysis_result['data']}")

# --- Test Visualization Agent ---
if analysis_result["success"]:
    print("\n" + "=" * 50)
    print("TESTING VISUALIZATION AGENT")
    print("=" * 50)

    viz_agent = VisualizationAgent(api_key=api_key)
    viz_result = viz_agent.run(
        data=analysis_result["data"],
        metadata=analysis_result["metadata"],
        user_query="Show me top 5 genres by number of tracks"
    )

    print(f"\nSuccess: {viz_result['success']}")
    print(f"Chart: {viz_result.get('path', 'N/A')}")
    print(f"Type: {viz_result.get('chart_type', 'N/A')}")
    print(f"Insights: {viz_result.get('insights', [])}")
    print(f"Suggestions: {viz_result.get('suggestions', [])}")

OPENAI_API_KEY=sk-your-key-here