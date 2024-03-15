import pandas as pd
import pydeck as pdk
import streamlit as st

VALENCIA_LAT = 39.46975
VALENCIA_LON = -0.37739

MAX_IH_BIKE = 1000
MAX_IH_CAR = 7000


@st.cache_resource
def traffic_now_heatmap(data: pd.DataFrame, is_bike=False):
    max_ih = MAX_IH_BIKE if is_bike else MAX_IH_CAR
    st.pydeck_chart(
        pdk.Deck(
            map_style=pdk.map_styles.SATELLITE,
            map_provider="mapbox",
            initial_view_state=pdk.ViewState(
                latitude=VALENCIA_LAT,
                longitude=VALENCIA_LON,
                zoom=12,
            ),
            layers=[
                pdk.Layer(
                    "HeatmapLayer",
                    data=data,
                    color_domain=[50, max_ih / 2],
                    intensity=0.5,
                    radius_pixels=15,
                    get_position="[lon, lat]",
                    aggregation="MEAN",
                    opacity=0.5,
                    get_weight="ih",
                    pickable=True,
                    extruded=True,
                )
            ],
        )
    )


def traffic_now_elevation(data: pd.DataFrame, is_bike=False):
    max_ih = MAX_IH_BIKE if is_bike else MAX_IH_CAR
    scale = 5 if is_bike else 0.5

    st.pydeck_chart(
        pdk.Deck(
            # map_style=None,  # type: ignore
            map_style=pdk.map_styles.SATELLITE,
            map_provider="mapbox",
            tooltip={"text": "vehicles/hour: {ih}"},  # type: ignore
            initial_view_state=pdk.ViewState(
                latitude=VALENCIA_LAT,
                longitude=VALENCIA_LON,
                zoom=12,
                pitch=40,
            ),
            layers=[
                pdk.Layer(
                    "ColumnLayer",
                    data,
                    get_elevation="ih",
                    get_fill_color=[
                        f"255*(1-ih/{max_ih})+150*ih/{max_ih}",
                        f"255*(1-ih/{max_ih})",
                        f"150*(1-ih/{max_ih})",
                        "160",
                    ],
                    get_position=["lon", "lat"],
                    elevation_aggregation="MEAN",
                    auto_highlight=True,
                    elevation_scale=scale,
                    radius=40,
                    pickable=True,
                    coverage=1,
                )
            ],
        )
    )