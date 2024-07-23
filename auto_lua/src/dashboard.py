import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
import numpy as np
import time
import webbrowser
import threading
import subprocess

class RadarDashboard:
    def __init__(self, port=8050):
        self.app = dash.Dash(__name__)
        self.port = port
        self.plots = {
            "plot-0": {"title": "Raw ADC Data", "xaxis": {}, "yaxis": {}},
            "plot-1": {"title": "Processed ADC Data", "xaxis": {}, "yaxis": {}},
            "plot-2": {"title": "Range Profile Plot", "xaxis": {}, "yaxis": {}}
        }
        self.status = "Initializing..."
        self.hand_status = "No"
        self.hand_distance = None
        self.hand_detection_count = 0
        self.setup_layout()
        self.setup_callbacks()
        self.status_update_time = time.time()
        self.plot_updates = {}
        

    def setup_layout(self):
        self.app.layout = html.Div([
            html.Div([
                html.H1("Radar Dashboard", style={'display': 'inline-block', 'margin-right': '20px'}),
                html.Button("Collect Data", id="collect-data-button", n_clicks=0,
                            style={'float': 'right', 'margin-top': '20px'})
            ]),
            html.Div(id="status", children=f"Status: {self.status}"),
            html.Div(id="plots-container-0", children=[self.create_plot("plot-0", "Raw ADC Data", "ADC Samples", "ADC I/Q Data")]),
            html.Div(id="plots-container-1", children=[self.create_plot("plot-1", "Processed ADC Data", "ADC Samples", "Magnitude (Db)")]),
            html.Div(id="hand-status", children=f"Hand above sensor: {self.hand_status}"),
            html.Div(id="hand-distance", children=""),
            html.Div(id="hand-detection-count", children=f"Hand detection count: {self.hand_detection_count}"),
            html.Div(id="plots-container-2", children=[self.create_plot("plot-2", "Range Profile Plot", "Range (m)", "Range FFT Output (Db)")]),

            dcc.Interval(id='interval-component', interval=100, n_intervals=0),
            dcc.Store(id='plot-data-store'),
            dcc.Store(id='status-store')
        ])

    def setup_callbacks(self):
        @self.app.callback(
            [Output("status", "children"),
            Output("hand-status", "children"),
            Output("hand-distance", "children"),
            Output("hand-detection-count", "children")],
            Input('interval-component', 'n_intervals')
        )
        def update_status_display(n):
            hand_status_text = f"Hand above sensor: {self.hand_status}"
            hand_distance_text = f"Distance: {self.hand_distance:.2f}m" if self.hand_distance is not None else ""
            hand_count_text = f"Hand detection count: {self.hand_detection_count}"
            return f"Status: {self.status}", hand_status_text, hand_distance_text, hand_count_text

        @self.app.callback(
            Output("status", "children", allow_duplicate=True),
            Input("collect-data-button", "n_clicks"),
            prevent_initial_call=True
        )
        def collect_data(n_clicks):
            if n_clicks > 0:
                return self.execute_data_collection()
            return dash.no_update
                
        @self.app.callback(
            Output('plot-data-store', 'data'),
            Output('status-store', 'data'),
            Input('interval-component', 'n_intervals'),
            State('plot-data-store', 'data'),
            State('status-store', 'data')
        )
        def update_plots_and_status(n, current_plot_data, current_status):
            if current_plot_data is None:
                current_plot_data = {}
            
            for plot_id, (data, plot_type) in self.plot_updates.items():
                if plot_type == "scatter":
                    current_plot_data[plot_id] = {
                        "data": [go.Scatter(x=data[0], y=data[1])],
                        "layout": go.Layout(
                            title=self.plots[plot_id]["title"],
                            xaxis=self.plots[plot_id]["xaxis"],
                            yaxis=self.plots[plot_id]["yaxis"]
                        )
                    }
                elif plot_type == "iq_scatter":
                    current_plot_data[plot_id] = {
                        "data": [
                            go.Scatter(x=data[0], y=data[1], name="Real (I)", line=dict(color="blue")),
                            go.Scatter(x=data[0], y=data[2], name="Imaginary (Q)", line=dict(color="red"))
                        ],
                        "layout": go.Layout(
                            title=self.plots[plot_id]["title"],
                            xaxis=self.plots[plot_id]["xaxis"],
                            yaxis=self.plots[plot_id]["yaxis"],
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    }
                elif plot_type == "heatmap":
                    current_plot_data[plot_id] = {
                        "data": [go.Heatmap(z=data[1], x=data[0])],
                        "layout": go.Layout(
                            title=self.plots[plot_id]["title"],
                            xaxis=self.plots[plot_id]["xaxis"],
                            yaxis=self.plots[plot_id]["yaxis"]
                        )
                    }
            
            self.plot_updates.clear()
            
            if time.time() - self.status_update_time < 0.5:
                return current_plot_data, self.status
            return current_plot_data, current_status

        @self.app.callback(
        Output({"type": "plot", "index": ALL}, "figure"),
        Input('interval-component', 'n_intervals'),
        State('plot-data-store', 'data')
        )
        def update_plots(n, stored_data):
            if not stored_data:
                raise PreventUpdate
            
            figures = []
            for plot_id in ['plot-0', 'plot-1', 'plot-2']:
                if plot_id in stored_data:
                    figures.append(go.Figure(data=stored_data[plot_id]["data"], 
                                             layout=stored_data[plot_id]["layout"]))
                else:
                    figures.append(go.Figure(data=[go.Scatter(x=[], y=[])],
                                             layout=go.Layout(title=f"No data for {plot_id}")))
            return figures
        
        def update_plot(self, plot_id, data, plot_type="scatter"):
            if plot_id not in self.plots and plot_id != "plot-0":
                print(f"Plot {plot_id} not found")
                return
            self.plot_updates[plot_id] = (data, plot_type)


    def create_plot(self, plot_id, title, x_label, y_label):
        self.plots[plot_id]["xaxis"] = dict(title=x_label)
        self.plots[plot_id]["yaxis"] = dict(title=y_label)
        
        return html.Div([
            dcc.Graph(id={"type": "plot", "index": plot_id}, 
                      figure=self.create_placeholder_figure(plot_id, title))
        ])
    
    def create_placeholder_figure(self, plot_id, title):
        return go.Figure(
            data=[go.Scatter(x=[], y=[])],
            layout=go.Layout(
                title=title,
                xaxis=self.plots[plot_id]["xaxis"],
                yaxis=self.plots[plot_id]["yaxis"]
            )
        )

    def update_plot(self, plot_id, data, plot_type="scatter", title=None, xaxis=None, yaxis=None):
        if plot_id not in self.plots:
            print(f"Plot {plot_id} not found")
            return
        if title:
            self.plots[plot_id]["title"] = title
        if xaxis:
            self.plots[plot_id]["xaxis"].update(xaxis)
        if yaxis:
            self.plots[plot_id]["yaxis"].update(yaxis)
        
        if isinstance(data, tuple) and len(data) == 2:
            if plot_id == "plot-0":
                x_data = list(range(len(data[0])))
                y_data_real = data[0]
                y_data_imag = data[1]
                self.plot_updates[plot_id] = ((x_data, y_data_real, y_data_imag), "iq_scatter")
            else:
                x_data, y_data = data
                self.plot_updates[plot_id] = ((x_data, y_data), plot_type)
        else:
            x_data = list(range(len(data)))
            y_data = data
            self.plot_updates[plot_id] = ((x_data, y_data), plot_type)

    def update_status(self, new_status):
        if new_status is None:
            return
        if new_status.startswith("Hand above sensor:"):
            parts = new_status.split(": ", 1)
            if len(parts) > 1:
                new_hand_status = parts[1].strip()
                if new_hand_status.startswith("Yes") and self.hand_status != "Yes":
                    self.hand_detection_count += 1
                self.hand_status = new_hand_status
                if self.hand_status.startswith("Yes"):
                    distance_part = self.hand_status.split("(")[1].split(")")[0]
                    self.hand_distance = float(distance_part.split(":")[1].split("m")[0])
                else:
                    self.hand_distance = None
        else:
            self.status = new_status

    def execute_data_collection(self):
        try:
            cmd_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime\triggerFrame.cmd'
            studio_runtime_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime'

            subprocess.Popen(cmd_path, cwd=studio_runtime_path)
            
            return "Status: Data collection completed successfully."
        except Exception as e:
            print(f"Status: Error during data collection: {str(e)}")
            return f"Status: Error during data collection: {str(e)}"
    
    def run(self):
        threading.Timer(1.25, lambda: webbrowser.open_new_tab(f'http://127.0.0.1:{self.port}')).start()
        self.app.run_server(debug=False, use_reloader=False, port=self.port)