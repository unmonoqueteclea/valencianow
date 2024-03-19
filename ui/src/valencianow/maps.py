"""functions to build the maps shown in the application

"""
import pandas as pd
import pydeck as pdk
import streamlit as st

VALENCIA_LAT, VALENCIA_LON = 39.46975, -0.37739
# approximated expected maximum values, to generate correct ranges
MAX_IH_BIKE, MAX_IH_CAR = 1000, 8000
LABEL_BIKE, LABEL_CAR = "bike", "car"


@st.cache_data
def traffic_now_heatmap(data: pd.DataFrame, is_bike=False) -> None:
    """Heatmap with current traffic values"""
    max_ih = MAX_IH_BIKE if is_bike else MAX_IH_CAR
    radius = 35 if is_bike else 20
    st.pydeck_chart(
        pdk.Deck(
            map_style=pdk.map_styles.SATELLITE,
            map_provider="mapbox",
            initial_view_state=pdk.ViewState(
                latitude=VALENCIA_LAT, longitude=VALENCIA_LON, zoom=12
            ),
            layers=[
                pdk.Layer(
                    "HeatmapLayer",
                    data=data,
                    color_domain=[50, max_ih / 2],
                    intensity=0.5,
                    radius_pixels=radius,
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


@st.cache_data
def traffic_now_elevation(data: pd.DataFrame, is_bike=False) -> None:
    """Map with columns representing traffic values"""
    max_ih = MAX_IH_BIKE if is_bike else MAX_IH_CAR
    label = LABEL_BIKE if is_bike else LABEL_CAR
    scale = 5 if is_bike else 0.5

    st.pydeck_chart(
        pdk.Deck(
            # map_style=None,  # type: ignore
            map_style=pdk.map_styles.SATELLITE,
            map_provider="mapbox",
            tooltip={"text": "🔢 sensor id: {sensor} \n ⏱" + label + "s/hour: {ih}"},  # type: ignore
            initial_view_state=pdk.ViewState(
                latitude=VALENCIA_LAT, longitude=VALENCIA_LON, zoom=12, pitch=40
            ),
            layers=[
                pdk.Layer(
                    "ColumnLayer",
                    data,
                    get_elevation="ih",
                    get_fill_color=[
                        # gradient from yellow to red
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


@st.cache_data
def air_now_scatterplot(data: pd.DataFrame):
    # color recommendations taken from
    # https://www.miteco.gob.es/es/calidad-y-evaluacion-ambiental/temas/atmosfera-y-calidad-del-aire/calidad-del-aire/ica.html
    data["color"] = data["ica"].map(
        {
            6: [56, 162, 206],
            5: [50, 161, 94],
            4: [241, 229, 73],
            3: [200, 52, 65],
            2: [110, 22, 29],
            1: [162, 91, 164],
        }  # type: ignore
    )
    st.pydeck_chart(
        pdk.Deck(
            map_style=pdk.map_styles.SATELLITE,
            map_provider="mapbox",
            initial_view_state=pdk.ViewState(
                latitude=VALENCIA_LAT, longitude=VALENCIA_LON, zoom=12
            ),
            tooltip={"text": "🔢 sensor {sensor} \n 🍃" + "ICA: {ica}"},  # type: ignore
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=data,
                    pickable=True,
                    opacity=0.5,
                    stroked=True,
                    filled=True,
                    get_position="[lon, lat]",
                    get_radius=400,
                    get_fill_color="color",
                )
            ],
        )
    )
