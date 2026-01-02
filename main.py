import os
from dotenv import load_dotenv
from core.core import Core



# Currently CLI

def main():
    # Load API key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        return

    # Initialize core
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

    # Show databases. Name and description for user convenience
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
        
        # Validate selection
        try:
            index = int(selection) - 1
            if 0 <= index < len(allowed_dbs):
                database = allowed_dbs[index]
            else:
                print(f"\n❌ Invalid selection")
                return
        except ValueError:
            # Maybe they typed the name directly
            if selection in allowed_dbs:
                database = selection
            else:
                print(f"\n❌ Invalid selection")
                return

    # Get query
    query = input("\nWhat would you like to analyze? ").strip()

    if not query:
        print("\n❌ No query provided")
        return

    # Run the pipeline
    print("\n" + "-" * 50)
    result = core.run(user=user, database=database, query=query)

    # Display results
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    if not result["success"]:
        print(f"\n❌ Error: {result['error']}")
        return

    # Analysis info
    print(f"\n📊 SQL executed:")
    print(f"   {result['analysis']['metadata']['sql']}")
    print(f"\n📋 Rows returned: {result['analysis']['metadata']['row_count']}")

    # Visualization info
    print(f"\n🎨 Chart saved to: {result['visualization']['path']}")
    print(f"   Chart type: {result['visualization']['chart_type']}")

    # Insights
    if result["visualization"]["insights"]:
        print(f"\n💡 Insights:")
        for insight in result["visualization"]["insights"]:
            print(f"   • {insight}")

    # Suggestions
    if result["visualization"]["suggestions"]:
        print(f"\n🔍 Suggestions:")
        for suggestion in result["visualization"]["suggestions"]:
            print(f"   • {suggestion}")

    print("\n" + "=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()