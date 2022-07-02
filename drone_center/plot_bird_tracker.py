#!/usr/bin/env python3

import plotly.express as px
import pandas as pd
import json

if __name__ == "__main__":
    df = pd.read_json("decoded.json")
    print(df)

    df["TagId"] = df["TagId"].fillna("Healthy")

    fig = px.scatter_mapbox(
        df, lat="Latitude", lon="Longitude", color="TagId"
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

    fig.show()
    fig.write_html("bird_tracking.html")
