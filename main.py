import os
from dotenv import load_dotenv
from core.core import Core


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

    # Show available options
    print(f"\nAvailable users: {', '.join(core.list_users())}")
    print(f"Available databases: {', '.join(core.list_databases())}")

    # Get user input
    print("\n" + "-" * 50)
    user = input("Username: ").strip()
    database = input("Database: ").strip()
    query = input("What would you like to analyze? ").strip()

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