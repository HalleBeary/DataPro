import os
import json
from datetime import datetime
from openai import OpenAI
import matplotlib.pyplot as plt
from styles.company_style import COMPANY_STYLE


"""
┌─────────────────────────────────────────────────────────────┐
│                  VISUALIZATION AGENT                        │
│                                                             │
│  1. _analyze_data()    → OpenAI decides:                    │
│                          - chart_type: "bar"                │
│                          - title: "Top 5 Genres..."         │
│                          - insights: ["Rock dominates..."]  │
│                          - suggestions: ["See by artist?"]  │
│                                                             │
│  2. _create_chart()    → Matplotlib renders with style      │
│                          - Applies company colors           │
│                          - Highlights key data points       │
│                          - Saves to output/                 │
│                                                             │
│  OUTPUT:                                                    │
│  {                                                          │
│    "success": True,                                         │
│    "path": "output/chart_20240115.png",                     │
│    "chart_type": "bar",                                     │
│    "insights": ["Rock dominates with 1297 tracks..."],      │
│    "suggestions": ["Break down Rock by artist?"]            │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘

"""


class VisualizationAgent:
    def __init__(self, api_key: str = None, style: dict = None):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.style = style or COMPANY_STYLE
        self.output_dir = "output"
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, data: list, metadata: dict, user_query: str = "") -> dict:
        """
        Main entry point: data → analysis → styled chart
        """
        try:
            # Step 1: AI analyzes data and decides visualization
            decisions = self._analyze_data(data, metadata, user_query)

            # Step 2: Create chart with AI-driven decisions
            chart_path = self._create_chart(
                data=data,
                metadata=metadata,
                decisions=decisions
            )

            return {
                "success": True,
                "path": chart_path,
                "chart_type": decisions.get("chart_type", "bar"),
                "insights": decisions.get("insights", []),
                "suggestions": decisions.get("suggestions", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": None,
                "insights": [],
                "suggestions": []
            }

    def _analyze_data(self, data: list, metadata: dict, user_query: str) -> dict:

        system_prompt = """You are a data visualization expert. 
    Your job is to analyze data and decide the best way to visualize it.

    RULES:
    - Return ONLY valid JSON, no explanations
    - Choose chart_type based on data shape and query intent
    - Bar: comparisons, rankings, categories
    - Line: trends over time
    - Pie: parts of a whole (use only if <7 categories)
    - Scatter: relationships between two numeric columns
    - Provide 1-2 concise insights about the data
    - Suggest 1 relevant follow-up analysis
    """

        user_prompt = f"""Analyze this data for visualization.

    USER QUERY: {user_query}

    DATA (first 10 rows): {json.dumps(data[:10], indent=2)}

    METADATA: {json.dumps(metadata, indent=2)}

    Respond with JSON:
    {{
        "chart_type": "bar" | "line" | "pie" | "scatter",
        "title": "descriptive chart title",
        "x_column": "column name for x-axis",
        "y_column": "column name for y-axis",
        "highlights": [indices to emphasize],
        "insights": ["1-2 key insights"],
        "suggestions": ["1 follow-up analysis"]
    }}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )

    def _create_chart(self, data: list, metadata: dict, decisions: dict) -> str:
        """
        Create the actual chart using matplotlib
        """
        chart_type = decisions.get("chart_type", "bar")
        title = decisions.get("title", "Chart")
        x_col = decisions.get("x_column", metadata["columns"][0])
        y_col = decisions.get("y_column", metadata["columns"][-1])
        highlights = decisions.get("highlights", [])

        # Extract data
        x_values = [row.get(x_col, "") for row in data]
        y_values = [row.get(y_col, 0) for row in data]

        # Apply style
        plt.style.use("seaborn-v0_8-whitegrid" if self.style["grid"] else "seaborn-v0_8-white")
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(self.style["background_color"])

        # Create colors (highlight specific bars if needed)
        colors = []
        for i in range(len(data)):
            if i in highlights:
                colors.append(self.style["colors"][1])  # Highlight color
            else:
                colors.append(self.style["colors"][0])  # Default color

        # Draw chart based on type
        if chart_type == "bar":
            ax.bar(x_values, y_values, color=colors)
            plt.xticks(rotation=45, ha="right")
        
        elif chart_type == "line":
            ax.plot(x_values, y_values, color=self.style["colors"][0], marker="o")
            plt.xticks(rotation=45, ha="right")
        
        elif chart_type == "pie":
            ax.pie(y_values, labels=x_values, colors=self.style["colors"], autopct="%1.1f%%")
        
        elif chart_type == "scatter":
            ax.scatter(x_values, y_values, color=self.style["colors"][0])

        # Styling
        ax.set_title(title, fontsize=self.style["title_size"], fontweight="bold")
        if chart_type != "pie":
            ax.set_xlabel(x_col, fontsize=self.style["label_size"])
            ax.set_ylabel(y_col, fontsize=self.style["label_size"])

        plt.tight_layout()

        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close()

        return filepath