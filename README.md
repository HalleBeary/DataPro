
## DataPro -- An Autonomous AI Agent for Data Analysis and Visualization. 


Twin agent system for data analysis/visualization for Natural Language Queries 


## Setup

1. Clone this repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python main.py`


## Core Functionality

This project contains a two-agent system, that work in tandem to analyze and visualize data

- Data Anlysis agent (agent/analysis_agent.py): Takes in a NL query via the command line interface, generates SQL command, and retrieves desired SQL data from the relevant library. The agent can access different types of SQL databases. Databases currently are chinook.db, northwind_small.sqlite, and are included in `data/`. Easy integration of additional databases is done via YAML configuration
- Visualization agent (agent/visaualization_agent.py): Takes SQL data from Data Analysis agent and generates a relevant visualization, appropriate for the retrieved data. It can generate line, bar, pie and scatter plots. Next to a visualization, the AI generates actionable insights and provides a suggestion is made on what to analyze next.

## Project Structure
```
prosus-agents/
├── agents/
│   ├── analysis_agent.py      # NL → SQL → Data
│   └── visualization_agent.py # Data → Chart
├── config/
│   ├── databases.yaml         # Database connections
│   └── users.yaml             # User permissions
├── core/
│   └── core.py                # Orchestration
├── data/
│   ├── chinook.db             # Music store database
│   └── northwind_small.sqlite # Business ERP database
├── output/                    # Generated charts
├── styles/
│   └── company_style.py       # Prosus branding
├── tests/
│   └── test_agents.py         # Automated tests
├── main.py                    # CLI entry point
├── requirements.txt
└── README.md
```

### Example Queries

| Query | What It Does |
|-------|--------------|
| "Top 10 artists by sales" | Bar chart of best-selling artists |
| "Monthly sales trends for 2012" | Line chart over time |
| "Distribution of tracks by media type" | Pie chart |
| "Top 5 customers in Germany by spending" | Filtered bar chart |


## User Permissions

Configured in `config/users.yaml`:

## Running Tests
```bash
pytest tests/test_agents.py -v -s
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | OpenAI GPT-4o |
| Agentic Pattern | Function Calling |
| Database | SQLite |
| Visualization | Matplotlib |
| Config | YAML |
| Testing | Pytest |
