#!/usr/bin/env python3
import glob
import micasense.imageset as imageset
from micasense.panel import Panel
import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt
from tqdm import tqdm
import plotly.express as px
import argparse

# Process for M300
# 1. User enters directory with flight data
# 2. Load all images into an imageset
# 3. Build and display map with all flight paths
# 4. Allow grouping of sets into flights
# 5. Display and confirm new groups
# 6. Filter out pictures taken on ground and find all calibration images with
#    calibration panel visible
# 7. Copy files into proper directory structure

PATH = "/media/davis/UBUNTU 20_0/Easten 050122 M300/"

reflect = []


def check_capture(p, capture):
    if capture.panels_in_all_expected_images():
        print(capture.images[0].path)

    capture.clear_image_data()


def load_multiple_imagesets(sets):
    image_set = imageset.ImageSet([])

    for ims in sets:
        for capture in imageset.ImageSet.from_directory(ims).captures:
            capture.set_id = ims.split("/")[-1]
            capture.flight = "Default"
            image_set.captures.append(capture)

    return image_set


def imageset_to_df(image_set):
    columns = [
        "timestamp",
        "latitude",
        "longitude",
        "altitude",
        "capture_id",
        "dls-yaw",
        "dls-pitch",
        "dls-roll",
    ]
    irr = ["irr-{}".format(wve) for wve in image_set.captures[0].center_wavelengths()]
    columns += irr
    columns.append("set_id")
    columns.append("flight")
    data = []
    for cap in image_set.captures:
        dat = cap.utc_time()
        loc = list(cap.location())
        uuid = cap.uuid
        dls_pose = list(cap.dls_pose())
        irr = cap.dls_irradiance()
        set_id = cap.set_id
        flight = cap.flight or ""
        row = [dat] + loc + [uuid] + dls_pose + irr + [set_id] + [flight]
        data.append(row)

    return pd.DataFrame.from_records(data, index="timestamp", columns=columns)


def graph_df(df, flight=False):
    # cutoff_altitude = df.altitude.mean()-3.0*df.altitude.std()

    # df = df[df.altitude > cutoff_altitude]
    fig = px.line_mapbox(
        df, lat=df.latitude, lon=df.longitude, color=df.flight if flight else df.set_id, zoom=14
    )
    fig.update_layout(
        mapbox_style="white-bg",
        mapbox_layers=[
            {
                "below": "traces",
                "sourcetype": "raster",
                "sourceattribution": "United States Geological Survey",
                "source": [
                    "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                ],
            }
        ],
    )

    return fig


def download_m300(args):
    files = load_multiple_imagesets(c for f in args.files for c in glob.glob(f))
    df = imageset_to_df(files)
    sets = df.set_id.unique()
    flights = {}


    import dash
    from dash import dcc, html, Input, Output, State, dash_table, callback_context
    from dash_daq import ToggleSwitch
    from dash.exceptions import PreventUpdate
    import plotly.express as px

    app = dash.Dash()
    app.layout = html.Div([
        html.Div([
            dcc.Graph(id="graph", figure=graph_df(df)),
            ToggleSwitch(id="graph-toggle", value=False)
        ]),
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
        html.Button("Output", id="output-button"),
        html.Div(id="output-div")
    ])
    @app.callback(
        Output("flights-table", "data"),
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
        if "new-flight-button.n_clicks" == triggered_id:
            if new_flight not in flights:
                flights[new_flight] = set()

        return [{"flight": k, "sets": ','.join(v)} for k, v in flights.items()]

    def update_df(r):
        for key, value in flights.items():
            if r.set_id in value:
                return key
        return "Default"

    @app.callback(
        Output("graph", "figure"),
        Input("add-set", "n_clicks"),
        Input("new-flight-button", "n_clicks"),
        Input("graph-toggle", "value"),
    )
    def update_graphs(_, __, value):
        df.flight = df.apply(update_df, axis=1)

        return graph_df(df, value)


    @app.callback(
        Output("flight-dropdown", "options"),
        Input("flight-dropdown", "search_value"),
        Input("new-flight-button", "n_clicks")
    )
    def flight_options(search_value, _):
        return list(flights.keys())

    @app.callback(
        Output("set-dropdown", "options"),
        Input("set-dropdown", "search_value"),
        Input("new-flight-button", "n_clicks"),
        Input("add-set", "n_clicks")
    )
    def set_options(search_value, _, __):
        return sorted(list(sets))

    @app.callback(
        Output("output-div", "children"),
        Input("output-button", "n_clicks"),
    )
    def output(clicks):
        if (clicks == 0):
            return "Calculate"

        df.flight = df.apply(update_df, axis=1)
        df.calibration = False

        if sum(len(v) for v in flights.values()) != len(df.set_id.unique()):
            return "Not all sets assigned to flights"

        # os.mkdir("Output")
        for flight_name in flights.keys():
            # os.mkdir(f"Output/{flight_name}")
            # os.mkdir(f"Output/{flight_name}/Data")
            # os.mkdir(f"Output/{flight_name}/CS")
            # os.mkdir(f"Output/{flight_name}/CE")

            captures = {i.images[0].capture_id: i for i in files.captures}
            for row in df[df.flight == flight_name]:
                capture = captures[row.capture_id]
                if capture.panels_in_all_expected_images():
                    row.calibration = True
                    print("This is a calibration", file=sys.stderr)
                capture.clear_image_data()



    app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter




if __name__ == "__main__":
    # files = load_multiple_imagesets(glob.glob(PATH + "000*SET"))
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    download_parser = subparsers.add_parser(
        "download", help="Download some data from a drone"
    )
    download_drone_parser = download_parser.add_subparsers(dest="drone", required=True)

    # Parser for downloading from m300
    m300_download_parser = download_drone_parser.add_parser("m300")
    m300_download_parser.add_argument(
        "files", metavar="FILES", nargs="+", help="Location of sets to process"
    )
    m300_download_parser.set_defaults(func=download_m300)

    args = parser.parse_args()
    args.func(args)

    # imageset.parallel_process(check_capture, files.captures, None, use_tqdm=True)

    # print(reflect)


    # cutoff_altitude = df.altitude.mean()-3.0*df.altitude.std()

    # df = df[df.altitude > cutoff_altitude]
    # print(df.altitude)
