#!/usr/bin/env python3

import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import plotly.express as px

data_canada = px.data.gapminder().query("country == 'Canada'")
fig = px.bar(data_canada, x='year', y='pop')

flights = {}
sets = {"m0", "m1", "m2", "m3"}

app = dash.Dash()
app.layout = html.Div([
    dcc.Graph(id="graph", figure=fig),
    html.Div([
        "Flights",
        dash_table.DataTable(
            id="flights-table",
            data=[
                {"flight": k, "sets": ','.join(v)} for k, v in flights.items()
            ]
        )
    ]),
    html.Br(),
    html.Div([
        "Create new flight: ",
        dcc.Input(id="new-flight"),
        html.Button("Submit", id="new-flight-button")
    ]),

    html.Br(),
    html.Div([
        html.Div(id="t"),
        dcc.Dropdown(id="flight-dropdown"),
        dcc.Dropdown(id="set-dropdown"),
        html.Button("Add set", id="add-set")
    ]),
])

@app.callback(
    [
        Output("flights-table", "data"),
        Output("graph", "figure"),
    ],
    [
        Input("add-set", "n_clicks"),
        Input("new-flight-button", "n_clicks"),
        State("new-flight", "value"),
        State("flight-dropdown", "value"),
        State("set-dropdown", "value")
    ]

)
def update_flights(add_set_clicks, new_flight_clicks, new_flight, flight_value, set_value):
    triggered_id = callback_context.triggered[0]['prop_id']

    if "add-set.n_clicks" == triggered_id:
        if not any(set_value in s for s in flights.values()):
            flights[flight_value].add(set_value)
        else:
            for se in flights.values():
                se.discard(set_value)
                flights[flight_value].add(set_value)
                break
    if "new-flight-button.n_clicks" == triggered_id:
        if new_flight not in flights:
            flights[new_flight] = set()

    return [{"flight": k, "sets": ','.join(v)} for k, v in flights.items()], fig


@app.callback(
    Output("flight-dropdown", "options"),
    Input("flight-dropdown", "search_value"),
    Input("new-flight-button", "n_clicks")
)
def flight_options(search_value, _):
    triggered_id = callback_context.triggered[0]['prop_id']
    print(triggered_id)
    return list(flights.keys())

@app.callback(
    Output("set-dropdown", "options"),
    Input("set-dropdown", "search_value"),
    Input("new-flight-button", "n_clicks"),
    Input("add-set", "n_clicks")
)
def set_options(search_value, _, __):
    triggered_id = callback_context.triggered[0]['prop_id']
    print(triggered_id)
    return sorted(list(sets))

app.run_server(debug=True, use_reloader=True)  # Turn off reloader if inside Jupyter
