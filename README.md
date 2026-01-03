
## Agentic AI for Data Analysis and Visualization. (Prosus Assignment)

Agentic AI project on data analysis/visualization. 

## Setup

1. Clone this repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python main.py`


## Core Functionality

This project contains a two-agent system, that work in tandem to analyze and visualize data

- Data Anlysis agent (agent/analysis_agent.py): Takes in a NL query via the command line interface, generates SQL command, and retrieves desired data from the relevant library. The agent can access different SQLite databases. Databases currently are chinook.db, northwind_small.sqlite, and are included in `data/`. Easy integration of additional databases is done via YAML configuration
- Visualization agent (agent/visaualization_agent.py): Takes SQL data from Data Analysis agent and generates a relevant visualization, appropriate for the retrieved data. It can generate line, bar, pie and scatter plots. Next to a visualization, a suggestion is made on what to analyze next.


### Example Queries

| Query | What It Does |
|-------|--------------|
| "Top 10 artists by sales" | Bar chart of best-selling artists |
| "Monthly sales trends for 2012" | Line chart over time |
| "Distribution of tracks by media type" | Pie chart |
| "Top 5 customers in Germany by spending" | Filtered bar chart |
