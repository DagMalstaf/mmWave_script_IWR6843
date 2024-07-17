import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
import numpy as np
import time
import webbrowser
import threading

class RadarDashboard:
    def __init__(self, port=8050):
        self.app = dash.Dash(__name__)
        self.port = port
        self.plots = {"plot-0": None}  
        self.status = "Initializing..."
        self.setup_layout()
        self.setup_callbacks()
        self.status_update_time = time.time()
        self.plot_updates = {}

    def setup_layout(self):
        self.app.layout = html.Div([
            html.H1("Radar Dashboard"),
            html.Div(id="status", children=f"Status: {self.status}"),
            html.Button("Add Plot", id="add-plot-button"),
            html.Div(id="plots-container", children=[self.create_plot("plot-0", "Raw ADC Data")]),
            dcc.Interval(id='interval-component', interval=100, n_intervals=0),
            dcc.Store(id='plot-data-store'),
            dcc.Store(id='status-store')
        ])

    def setup_callbacks(self):
        @self.app.callback(
            Output("plots-container", "children"),
            Input("add-plot-button", "n_clicks"),
            State("plots-container", "children")
        )
        def add_plot_callback(n_clicks, existing_plots):
            if n_clicks is None:
                raise PreventUpdate
            return self.add_plot(existing_plots)

        @self.app.callback(
            Output("plots-container", "children", allow_duplicate=True),
            Input({"type": "remove", "index": ALL}, "n_clicks"),
            State("plots-container", "children"),
            prevent_initial_call=True
        )
        def remove_plot(n_clicks, existing_plots):
            ctx = dash.callback_context
            if not ctx.triggered:
                raise PreventUpdate
            removed_id = ctx.triggered[0]["prop_id"].split(".")[0]
            plot_id = removed_id.replace("remove-", "")
            self.plots.pop(plot_id, None)
            return [plot for plot in existing_plots if plot["props"]["id"] != plot_id]

        @self.app.callback(
            Output("status", "children"),
            Input('interval-component', 'n_intervals'),
            State('status-store', 'data')
        )
        def update_status_display(n, stored_status):
            if stored_status:
                return f"Status: {stored_status}"
            return f"Status: {self.status}"

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
                    current_plot_data[plot_id] = [go.Scatter(x=list(range(len(data))), y=data)]
                elif plot_type == "heatmap":
                    current_plot_data[plot_id] = [go.Heatmap(z=data)]
            
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
            return [go.Figure(data=plot_data) for plot_id, plot_data in stored_data.items()]

        def update_plot(self, plot_id, data, plot_type="scatter"):
            if plot_id not in self.plots and plot_id != "plot-0":
                print(f"Plot {plot_id} not found")
                return
            self.plot_updates[plot_id] = (data, plot_type)

    def add_plot(self, existing_plots=None):
        if existing_plots is None:
            existing_plots = []
        plot_id = f"plot-{len(existing_plots)}"
        new_plot = html.Div([
            dcc.Graph(id={"type": "plot", "index": plot_id}, figure=self.create_placeholder_figure()),
            html.Button("Remove", id=f"remove-{plot_id}")
        ])
        self.plots[plot_id] = new_plot
        return existing_plots + [new_plot]

    def create_plot(self, plot_id, title):
        return html.Div([
            dcc.Graph(id={"type": "plot", "index": plot_id}, figure=self.create_placeholder_figure(title)),
            html.Button("Remove", id=f"remove-{plot_id}")
        ])\
    
    def create_placeholder_figure(self, title):
        return go.Figure(data=[go.Scatter(x=[], y=[])],
                         layout=go.Layout(
                             title=title,
                             xaxis=dict(title="X-axis"),
                             yaxis=dict(title="Y-axis")
                         ))

    def update_plot(self, plot_id, data, plot_type="scatter"):
        if plot_id not in self.plots:
            print(f"Plot {plot_id} not found")
            return
        self.plot_updates[plot_id] = (data, plot_type)

    def update_status(self, new_status):
        self.status = new_status
        self.status_update_time = time.time()
    
    def run(self):
        threading.Timer(1.25, lambda: webbrowser.open_new_tab(f'http://127.0.0.1:{self.port}')).start()
        
        self.app.run_server(debug=False, use_reloader=False, port=self.port)