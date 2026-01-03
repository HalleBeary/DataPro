import os
import json
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
from openai import OpenAI
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
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, data: list, metadata: dict, user_query: str = "") -> dict:
        """
        Refactored: Data + Query -> Plotly JSON Spec -> Interactive Figure
        """
        try:
            if not data:
                return {"success": True, "path": None, "insights": ["No data found."]}

            # STEP 1: AI generates the Plotly Specification
            spec = self._generate_chart_spec(data, metadata, user_query)

            # STEP 2: Build the Plotly Figure from the Spec
            fig = self._build_figure(data, spec)

            # STEP 3: Save as Interactive HTML and Static Image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(self.output_dir, f"chart_{timestamp}.html")
            png_path = os.path.join(self.output_dir, f"chart_{timestamp}.png")
            
            fig.write_html(html_path)
            # Note: png requires 'kaleido' package
            try:
                fig.write_image(png_path, engine="kaleido")
            except:
                png_path = None # Fallback if kaleido isn't installed

            return {
                "success": True,
                "html_path": html_path,
                "png_path": png_path,
                "insights": spec.get("insights", []),
                "suggestions": spec.get("suggestions", [])
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_chart_spec(self, data: list, metadata: dict, user_query: str) -> dict:
        """AI decides exactly how the chart should look via Tool Calling."""
        tools = [{
            "type": "function",
            "function": {
                "name": "render_chart",
                "description": "Render a Plotly chart",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "pie", "heatmap"]},
                        "title": {"type": "string"},
                        "x_axis": {"type": "string", "description": "Column name for X"},
                        "y_axis": {"type": "string", "description": "Column name for Y"},
                        "color_by": {"type": "string", "description": "Column name to differentiate colors/series"},
                        "insights": {"type": "array", "items": {"type": "string"}},
                        "suggestions": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["chart_type", "title", "x_axis", "y_axis"]
                }
            }
        }]

        prompt = f"""Analyze this data and design a Plotly visualization.
QUERY: {user_query}
COLUMNS: {metadata['columns']}
SAMPLE DATA: {json.dumps(data[:5])}

Design a chart that best answers the query. If 'color_by' is provided, create multiple series.
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "render_chart"}}
        )
        
        return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    def _build_figure(self, data: list, spec: dict) -> go.Figure:
        """Translates the AI Spec and Company Style into a real Plotly Object."""
        fig = go.Figure()
        chart_type = spec['chart_type']
        x_col, y_col = spec['x_axis'], spec['y_axis']
        color_col = spec.get('color_by')

        # Extract values
        if color_col:
            # Multi-series logic
            groups = {}
            for row in data:
                g = row.get(color_col, "Total")
                if g not in groups: groups[g] = {'x': [], 'y': []}
                groups[g]['x'].append(row.get(x_col))
                groups[g]['y'].append(row.get(y_col))
            
            for i, (name, val) in enumerate(groups.items()):
                color = self.style['colors'][i % len(self.style['colors'])]
                if chart_type == "bar":
                    fig.add_trace(go.Bar(x=val['x'], y=val['y'], name=str(name), marker_color=color))
                else:
                    fig.add_trace(go.Scatter(x=val['x'], y=val['y'], name=str(name), mode='lines+markers', line=dict(color=color)))
        else:
            # Single series logic
            x_vals = [r.get(x_col) for r in data]
            y_vals = [r.get(y_col) for r in data]
            fig.add_trace(go.Bar(x=x_vals, y=y_vals, marker_color=self.style['colors'][0]) if chart_type == "bar" 
                          else go.Scatter(x=x_vals, y=y_vals, mode='lines+markers', line=dict(color=self.style['colors'][0])))

        # Apply Global Company Styling
        fig.update_layout(
            title=spec['title'],
            template="plotly_white",
            paper_bgcolor=self.style.get('background_color', '#FFFFFF'),
            plot_bgcolor=self.style.get('background_color', '#FFFFFF'),
            font=dict(family=self.style.get('font_family', 'Arial'), color=self.style.get('text_color', '#000000')),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig