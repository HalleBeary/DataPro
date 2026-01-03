import os
import json
import time
from datetime import datetime
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    BadRequestError,
    APIError
)
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import textwrap
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
        self.max_retries = 3
        self.style = style or COMPANY_STYLE
        self.output_dir = "output"

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Define the tool for chart creation
        self.tools = [{
            "type": "function",
            "function": {
                "name": "create_chart",
                "description": "Create a chart visualization based on the data analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "enum": ["bar", "line", "pie", "scatter"],
                            "description": "Type of chart to create"
                        },
                        "title": {
                            "type": "string",
                            "description": "Descriptive title for the chart"
                        },
                        "x_column": {
                            "type": "string",
                            "description": "Column name to use for x-axis"
                        },
                        "y_column": {
                            "type": "string",
                            "description": "Column name to use for y-axis"
                        },
                        "highlights": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Indices of data points to highlight (0-based)"
                        },
                        "insights": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "1-2 key insights about the data"
                        },
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "1 follow-up analysis suggestion"
                        }
                    },
                    "required": ["chart_type", "title", "x_column", "y_column"]
                }
            }
        }]

    def run(self, data: list, metadata: dict, user_query: str = "") -> dict:
        """
        Main entry point: data → analysis → styled chart
        """
        try:
            # Handle empty data
            if not data or len(data) == 0:
                return {
                    "success": True,
                    "path": None,
                    "chart_type": None,
                    "insights": ["No data found matching your query."],
                    "suggestions": ["Try broadening your search criteria or check for typos."]
                }

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
        """
        AI decides how to visualize the data using function calling
        """
        system_prompt = """You are a data visualization expert.
Your job is to analyze data and decide the best way to visualize it.

RULES:
- Use the create_chart function to specify your visualization
- Choose chart_type based on data shape and query intent:
  - bar: comparisons, rankings, categories
  - line: trends over time
  - pie: parts of a whole (only if <7 categories)
  - scatter: relationships between two numeric columns
- Provide 1-2 concise, insightful observations about the data
- Suggest 1 relevant follow-up analysis
- Make suggestions specific and actionable (include filters, time period, metrics)
- Highlight the most important data point (usually index 0 for rankings)
"""

        user_prompt = f"""Analyze this data and create a visualization.

USER QUERY: {user_query}

DATA (first 10 rows): {json.dumps(data[:10], indent=2)}

COLUMNS: {metadata.get('columns', [])}
ROW COUNT: {metadata.get('row_count', len(data))}
"""

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    tools=self.tools,
                    tool_choice="auto", #{"type": "function", "function": {"name": "create_chart"}},
                    temperature=0
                )

                # Extract function call
                tool_call = response.choices[0].message.tool_calls[0]
                decisions = json.loads(tool_call.function.arguments)

                return decisions

            except AuthenticationError:
                raise Exception("Invalid API key. Please check your OPENAI_API_KEY.")

            except RateLimitError:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise Exception("Rate limit exceeded. Please try again later.")

            except APIConnectionError:
                if attempt < self.max_retries - 1:
                    print("🔄 Connection error. Retrying...")
                    time.sleep(1)
                else:
                    raise Exception("Could not connect to OpenAI. Check your internet.")

            except BadRequestError as e:
                raise Exception(f"Invalid request: {str(e)}")

            except APIError as e:
                if attempt < self.max_retries - 1:
                    print("🔄 OpenAI server error. Retrying...")
                    time.sleep(1)
                else:
                    raise Exception(f"OpenAI error: {str(e)}")


    def _create_chart(self, data: list, metadata: dict, decisions: dict) -> str:
            """
            Create the actual chart using matplotlib with Prosus styling
            """
            # === EXTRACT PARAMETERS ===
            chart_type = decisions.get("chart_type", "bar")
            title = decisions.get("title", "Chart")
            x_col = decisions.get("x_column", metadata["columns"][0])
            y_col = decisions.get("y_column", metadata["columns"][-1])
            highlights = decisions.get("highlights", [0])

            x_values = [textwrap.fill(str(row.get(x_col, "")), width=12) for row in data]
            y_values = [row.get(y_col, 0) for row in data]
            style = self.style

            # === SETUP FIGURE ===
            fig, ax = plt.subplots(figsize=style["figure_size"])
            fig.patch.set_facecolor(style["background_color"])
            ax.set_facecolor(style["background_color"])

            # === HEADER GRADIENT BAR ===
            header_ax = fig.add_axes([0, 0.93, 1, 0.07])
            header_ax.set_xlim(0, 1)
            header_ax.set_ylim(0, 1)
            gradient = plt.cm.colors.LinearSegmentedColormap.from_list(
                "prosus_gradient",
                [style["colors"][1], style["colors"][2]]
            )
            header_ax.imshow([[i/100 for i in range(100)]], aspect="auto", cmap=gradient, extent=[0, 1, 0, 1])
            header_ax.axis("off")

            # === LOGO ===
            logo_path = style.get("logo_path", "assets/prosus_logo.png")
            if os.path.exists(logo_path):
                try:
                    logo_ax = fig.add_axes([0.82, 0.93, 0.12, 0.06])
                    logo_ax.imshow(mpimg.imread(logo_path))
                    logo_ax.axis("off")
                except Exception:
                    self._add_text_logo(fig)
            else:
                self._add_text_logo(fig)

            # === DRAW CHART ===
            if chart_type == "bar":
                self._draw_bar(ax, x_values, y_values, highlights, style)
            elif chart_type == "line":
                self._draw_line(ax, data, x_values, y_values, x_col, y_col, metadata, style)
            elif chart_type == "pie":
                self._draw_pie(ax, x_values, y_values, style)
            elif chart_type == "scatter":
                self._draw_scatter(ax, x_values, y_values, style)

            # === TITLE ===
            ax.set_title(
                title,
                fontsize=style["title_size"],
                fontweight="bold",
                color=style["text_color"],
                pad=20,
                loc="left"
            )

            # === AXIS STYLING (skip for pie) ===
            if chart_type != "pie":
                ax.set_xlabel(x_col, fontsize=style["label_size"], color=style.get("axis_color", style["text_color"]))
                ax.set_ylabel(y_col, fontsize=style["label_size"], color=style.get("axis_color", style["text_color"]))
                ax.tick_params(colors=style.get("axis_color", style["text_color"]), labelsize=style["tick_size"])

                if style.get("grid", True):
                    ax.yaxis.grid(True, color=style.get("grid_color", "#E0E0E0"), alpha=style.get("grid_alpha", 0.5), linestyle="--")
                    ax.set_axisbelow(True)

                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["bottom"].set_color(style.get("grid_color", "#E0E0E0"))
                ax.spines["left"].set_color(style.get("grid_color", "#E0E0E0"))

            # === FOOTER ===
            fig.text(0.01, 0.02, f"Source: {metadata.get('source', 'Database')}", fontsize=8, color=style.get("axis_color", "#333333"), ha="left", alpha=0.6)
            fig.text(0.99, 0.02, "Generated by Prosus AI Data Agent", fontsize=8, color=style.get("axis_color", "#333333"), ha="right", alpha=0.6)

            # === SAVE ===
            plt.subplots_adjust(top=0.85, bottom=0.15)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.output_dir, f"chart_{timestamp}.png")
            fig.savefig(filepath, dpi=style["dpi"], bbox_inches="tight", facecolor=style["background_color"])
            plt.close()

            return filepath
    

    # ----------------
    # Helper methods
    
    def _add_text_logo(self, fig):
        """Fallback text logo"""
        fig.text(0.95, 0.96, "prosus", fontsize=18, fontweight="bold", color="white", ha="right", va="center", style="italic")

    def _draw_bar(self, ax, x_values, y_values, highlights, style):
        """Draw bar chart"""
        colors = []
        for i in range(len(y_values)):
            if i in highlights:
                colors.append(style["colors"][0])
            elif i % 2 == 0:
                colors.append(style["colors"][1])
            else:
                colors.append(style["colors"][2])

        bars = ax.bar(x_values, y_values, color=colors, edgecolor="white", linewidth=1.5)

        for bar, val in zip(bars, y_values):
            label = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (max(y_values) * 0.02),
                label,
                ha="center", va="bottom",
                color=style["text_color"],
                fontsize=11, fontweight="bold"
            )

        ax.tick_params(axis='x', rotation=45)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment('right')

    def _draw_line(self, ax, data, x_values, y_values, x_col, y_col, metadata, style):
        """Draw line chart"""
        unique_x = len(set(x_values))
        has_multiple_series = unique_x < len(x_values)

        if has_multiple_series:
            other_cols = [c for c in metadata.get("columns", []) if c != x_col and c != y_col]
            if other_cols:
                group_col = other_cols[0]
                groups = {}
                for row in data:
                    group = row.get(group_col, "Unknown")
                    if group not in groups:
                        groups[group] = []
                    groups[group].append({"x": row.get(x_col, ""), "y": row.get(y_col, 0)})

                all_x_raw = [row.get(x_col, "") for row in data]
                all_x = sorted(set(all_x_raw), key=lambda d: (str(d)[:4], str(d)[5:7] if len(str(d)) >= 7 else "00"))
                x_to_idx = {x: i for i, x in enumerate(all_x)}

                for i, (group_name, points) in enumerate(groups.items()):
                    sorted_points = sorted(points, key=lambda p: (str(p["x"])[:4], str(p["x"])[5:7] if len(str(p["x"])) >= 7 else "00"))
                    plot_x = [x_to_idx[p["x"]] for p in sorted_points]
                    plot_y = [p["y"] for p in sorted_points]
                    ax.plot(plot_x, plot_y, color=style["colors"][i % len(style["colors"])], marker="o", linewidth=2.5, label=str(group_name), markersize=6, alpha=0.85)

                num_ticks = len(all_x)
                if num_ticks > 10:
                    step = max(1, num_ticks // 8)
                    tick_positions = list(range(0, num_ticks, step))
                    ax.set_xticks(tick_positions)
                    ax.set_xticklabels([all_x[i] for i in tick_positions])
                else:
                    ax.set_xticks(range(num_ticks))
                    ax.set_xticklabels(all_x)

                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=style["tick_size"], frameon=True, fancybox=True, borderpad=1)
                plt.subplots_adjust(right=0.75)
            else:
                self._draw_single_line(ax, x_values, y_values, style)
        else:
            self._draw_single_line(ax, x_values, y_values, style)

        ax.tick_params(axis='x', rotation=45)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment('right')

    def _draw_single_line(self, ax, x_values, y_values, style):
        """Draw single line chart"""
        sorted_pairs = sorted(zip(x_values, y_values), key=lambda p: (str(p[0])[:4], str(p[0])[5:7] if len(str(p[0])) >= 7 else "00"))
        sorted_x = [p[0] for p in sorted_pairs]
        sorted_y = [p[1] for p in sorted_pairs]
        ax.plot(sorted_x, sorted_y, color=style["colors"][0], marker="o", linewidth=2.5, markersize=6)

    def _draw_pie(self, ax, x_values, y_values, style):
        """Draw pie chart"""
        ax.pie(y_values, labels=x_values, colors=style["colors"][:len(y_values)], autopct="%1.1f%%", startangle=90)

    def _draw_scatter(self, ax, x_values, y_values, style):
        """Draw scatter chart"""
        ax.scatter(x_values, y_values, color=style["colors"][0], s=100)
        ax.tick_params(axis='x', rotation=45)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment('right')