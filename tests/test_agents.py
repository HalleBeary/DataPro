import os
import sys
import pytest
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.core import Core

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")


@pytest.fixture  # instead of creating a new Core() instance manually in every test, pytest injects it automatically when a test function requests it as an argument.
def core():
    return Core(api_key=API_KEY)


class TestSecurity: # Security and access control

    def test_1_unknown_user_rejected(self, core):
        """
        Test 1: Unknown user is rejected
        - Most fundamental security check
        - No API call needed
        """
        # Example user: Use my own name
        result = core.run(
            user="Tim Faber",
            database="chinook",
            query="Top 5 selling artists in the US"
        )

        assert result["success"] == False # If result returns succes, the test fails in this case as the user is not part of userbase in user.yaml file
        assert "Unknown user" in result["error"] # Test success if unkown user error is thrown

        print(f"   Test 1 passed: Unknown user rejected")
        print(f"   Error: {result['error']}")

    def test_2_permission_denied(self, core):
        """
        Test 2: Database rescriction to specific users:
        - Users without specific access is denied
        - Bob has only access to northwind
        """
        result = core.run(
            user="bob",
            database="chinook",
            query="Show me top 5 genres"
        )

        assert result["success"] == False  
        assert "Access denied" in result["error"] or "cannot access" in result["error"].lower() 

        print(f"   Test 2 passed: Permission denied")
        print(f"   Error: {result['error']}")


class TestCoreFunctionality:

    def test_3_valid_query_returns_data(self, core):
        """
        Test 3: This test shows the workings of the full pipeline: Core functionality tested: core.py

        1. Query: "Show me top 5 genres by number of tracks" 
        2. Analysis agent: convert query to SQL -> retrieve data from database -> pass data to visualization agent.
        3.  Visualisation agent: convert SQL data to appropriate visualization
        
        """
        result = core.run(
            user="alice",
            database="chinook",
            query="Show me top 5 genres by number of tracks"
        )

        assert result["success"] == True, f"Query failed: {result.get('error')}"
        
        # Check length of data corresponding with Query
        assert len(result["analysis"]["data"]) == 5, "Expected 5 rows" # Querey was top 5 genres
        
        # See if metadata exists
        assert "sql" in result["analysis"]["metadata"]
        assert "columns" in result["analysis"]["metadata"]
        
        # Is visualization created
        assert result["visualization"]["path"] is not None
        assert os.path.exists(result["visualization"]["path"])

        print(f"   Test 3 passed: Full pipeline works")
        print(f"   Rows: {len(result['analysis']['data'])}")
        print(f"   SQL: {result['analysis']['metadata']['sql'][:80]}...")

    


    def test_4_multiple_databases(self, core):
        """
        Test 4: Checks multiple database intergration
        - Proves multi-database support
        - Easy integration done via YAML file.
        """
        result = core.run(
            user="bob",
            database="northwind",
            query="Show me top 5 products by quantity sold"
        )

        assert result["success"] == True, f"Query failed: {result.get('error')}"
        assert len(result["analysis"]["data"]) > 0, "Expected some data"

        print(f"   Test 4 passed: Second database works")
        print(f"   Rows: {len(result['analysis']['data'])}")


class TestEdgeCases:

    def test_5_empty_result(self, core):
        """
        Test 5: Empty result doesn't crash
        - Query returns no data, system handles in user friendly manner 
        """
        result = core.run(
            user="alice",
            database="chinook",
            query="Show me top 5 artists with sales in Antarctica"
        )

        # Should not crash
        assert "success" in result
        
        # If successful, check it handled empty data
        if result["success"]:
            viz = result.get("visualization", {})
            # Either no chart or chart with "no data" message
            if viz.get("path") is None:
                assert any("No data" in str(i) for i in viz.get("insights", []))

        print(f"   Test 5 passed: Empty result handled")
        print(f"   Success: {result['success']}")




# Run tests in order
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
