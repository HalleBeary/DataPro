import os
import webbrowser # Added to open charts automatically
from dotenv import load_dotenv
from core.core import Core

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found")
        return

    core = Core(api_key=api_key)

    # Header
    print("\n" + "=" * 50)
    print("🤖 Prosus Data Analysis Agent")
    print("=" * 50)

    # Show available users
    print(f"\nAvailable users: {', '.join(core.list_users())}")

    # Get and validate user
    print("\n" + "-" * 50)
    user = input("Username: ").strip()

    if user not in core.list_users():
        print(f"\n❌ Unknown user: '{user}'")
        return

    # Get allowed databases for this user
    allowed_dbs = core.users["users"][user].get("allowed_databases", [])

    if not allowed_dbs:
        print(f"\n❌ User '{user}' has no database access")
        return

    # Show databases with descriptions
    print(f"\nAvailable databases for {user}:\n")
    for i, db_name in enumerate(allowed_dbs, 1):
        description = core.databases["databases"][db_name].get("description", "No description")
        print(f"  [{i}] {db_name}")
        print(f"      {description}\n")

    # Auto-select if only one database, otherwise prompt
    if len(allowed_dbs) == 1:
        database = allowed_dbs[0]
        print(f"Database: {database} (auto-selected)")
    else:
        selection = input("Select database [1-{}]: ".format(len(allowed_dbs))).strip()
        
        try:
            index = int(selection) - 1
            if 0 <= index < len(allowed_dbs):
                database = allowed_dbs[index]
            else:
                print(f"\n❌ Invalid selection")
                return
        except ValueError:
            if selection in allowed_dbs:
                database = selection
            else:
                print(f"\n❌ Invalid selection")
                return

    # Main query loop
    print("\n" + "=" * 50)
    print(f"Ready! Using database: {database}")
    print("Type 'exit' to quit, '/switch' to change database")
    print("=" * 50)

    last_result = None 

    while True:
        print()
        query = input("What would you like to analyze? ").strip()

        if query.lower() in ["exit", "quit", "q"]:
            break

        # Handle database switch
        if query.lower() == "/switch":
            if len(allowed_dbs) == 1:
                print("Only one database available.")
                continue
            
            print()
            for i, db_name in enumerate(allowed_dbs, 1):
                description = core.databases["databases"][db_name].get("description", "No description")
                print(f"  [{i}] {db_name} - {description}")
            
            selection = input("\nSelect database [1-{}]: ".format(len(allowed_dbs))).strip()
            try:
                index = int(selection) - 1
                if 0 <= index < len(allowed_dbs):
                    database = allowed_dbs[index]
                    print(f"✅ Switched to: {database}")
                    last_result = None  # Clear context on database switch
                else:
                    print("❌ Invalid selection")
            except ValueError:
                print("❌ Invalid selection")
            continue

        # Skip empty queries
        if not query:
            continue

        # Build context from previous result
        context = None
        if last_result and last_result.get("success"):
            context = {
                "previous_query": last_result.get("query"),
                "previous_data": last_result.get("analysis", {}).get("data", [])[:10],
                "previous_suggestions": last_result.get("visualization", {}).get("suggestions", [])
            }

        print("\n" + "-" * 50)
        result = core.run(user=user, database=database, query=query, context=context)

        if result.get("success"):
            last_result = result
            
            # --- Display Logic --
            ana = result['analysis']
            viz = result['visualization']

            print(f"\n✅ Analysis Complete")
            print(f"📝 Thought: {ana['metadata'].get('explanation', 'N/A')}")
            print(f"💾 SQL: {ana['metadata']['sql']}")
            
            if viz.get("html_path"):
                print(f"🌐 Plotly Chart: {viz['html_path']}")
                # Automatically open the browser to see the interactive chart
                webbrowser.open(f"file://{os.path.abspath(viz['html_path'])}")
            
            if viz["insights"]:
                print(f"\n💡 Insights:")
                for i in viz["insights"]: print(f"   • {i}")

            if viz["suggestions"]:
                print(f"\n🔍 Next Steps:")
                for s in viz["suggestions"]: print(f"   • {s}")
        else:
            print(f"\n❌ Error: {result['error']}")

        print("-" * 50)

if __name__ == "__main__":
    main()