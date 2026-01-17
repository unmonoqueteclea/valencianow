"""functions to build all the maps shown in the application"""

import pandas as pd
import pydeck as pdk

from valencianow import config, data

LABEL_BIKE, LABEL_CAR, LABEL_AIR = "bike", "car", "air"
# approximated expected maximum values, to generate correct ranges
MAX_IH_BIKE, MAX_IH_CAR = 1000, 8000
RADIUS_BIKE, RADIUS_CAR = 35, 15
SCALE_BIKE, SCALE_CAR = 5, 0.5
AGGREGATION = "MEAN"


def balizas_icon_layer(balizas_df: pd.DataFrame) -> pdk.Layer:
    """IconLayer for displaying active balizas on the map."""
    return pdk.Layer(
        "IconLayer",
        data=balizas_df,
        get_position=[data.COL_LON, data.COL_LAT],
        get_icon="icon_data",
        get_size=47,
        pickable=True,
        tooltip=False,
    )


def traffic_now_heatmap(
    rows: pd.DataFrame, balizas_df: pd.DataFrame | None = None, is_bike=False
):
    """Heatmap with current traffic values"""

    max_ih = MAX_IH_BIKE if is_bike else MAX_IH_CAR
    radius = RADIUS_BIKE if is_bike else RADIUS_CAR

    layers = [
        pdk.Layer(
            "HeatmapLayer",
            data=rows,
            color_domain=[100, max_ih],
            intensity=1,
            radius_pixels=radius,
            get_position=f"[{data.COL_LON}, {data.COL_LAT}]",
            aggregation=AGGREGATION,
            opacity=0.5,
            get_weight="ih",
            pickable=True,
            extruded=True,
        )
    ]

    if balizas_df is not None and not balizas_df.empty:
        layers.append(balizas_icon_layer(balizas_df))

    return pdk.Deck(
        map_style="dark",
        map_provider="carto",
        initial_view_state=pdk.ViewState(
            latitude=config.VALENCIA_LAT, longitude=config.VALENCIA_LON, zoom=12
        ),
        layers=layers,
    )


def traffic_now_elevation(rows: pd.DataFrame, is_bike=False) -> pdk.Deck:
    """Map with columns representing traffic values"""

    max_ih = MAX_IH_BIKE if is_bike else MAX_IH_CAR
    label = LABEL_BIKE if is_bike else LABEL_CAR
    scale = SCALE_BIKE if is_bike else SCALE_CAR
    radius = RADIUS_BIKE if is_bike else RADIUS_CAR

    tooltip = (
        f"🔢 Sensor id: {{{data.COL_SENSOR}}} \n"
        f"⏱️ {label.capitalize()}s/hour: {{ih}} \n"
        f"📅 Updated: {{{data.COL_DATE}}}"
    )
    return pdk.Deck(
        map_style="dark",
        map_provider="carto",
        tooltip={"text": tooltip},  # type: ignore
        initial_view_state=pdk.ViewState(
            latitude=config.VALENCIA_LAT,
            longitude=config.VALENCIA_LON,
            zoom=12,
            pitch=40,
        ),
        layers=[
            pdk.Layer(
                "ColumnLayer",
                rows,
                get_elevation="ih",
                get_fill_color=[
                    # gradient from yellow to red
                    f"255*(1-ih/{max_ih})+150*ih/{max_ih}",
                    f"255*(1-ih/{max_ih})",
                    f"150*(1-ih/{max_ih})",
                    "160",
                ],
                get_position=[data.COL_LON, data.COL_LAT],
                elevation_aggregation=AGGREGATION,
                auto_highlight=True,
                elevation_scale=scale,
                radius=radius,
                pickable=True,
                coverage=1,
            )
        ],
    )


def air_now_scatterplot(rows: pd.DataFrame):
    # color recommendations taken from
    # https://www.miteco.gob.es/es/calidad-y-evaluacion-ambiental/temas/atmosfera-y-calidad-del-aire/calidad-del-aire/ica.html
    rows["color"] = rows["ica"].map(
        {
            6: [56, 162, 206],
            5: [50, 161, 94],
            4: [241, 229, 73],
            3: [200, 52, 65],
            2: [110, 22, 29],
            1: [162, 91, 164],
        }  # type: ignore
    )
    tooltip = f"🔢 Sensor: {{{data.COL_SENSOR}}} \n 🍃 ICA: {{ica}} \n 📅 Updated: {{{data.COL_DATE}}}"
    return pdk.Deck(
        map_style="dark",
        map_provider="carto",
        initial_view_state=pdk.ViewState(
            latitude=config.VALENCIA_LAT, longitude=config.VALENCIA_LON, zoom=12
        ),
        tooltip={"text": tooltip},  # type: ignore
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=rows,
                pickable=True,
                opacity=0.5,
                stroked=True,
                filled=True,
                get_position=f"[{data.COL_LON}, {data.COL_LAT}]",
                get_radius=440,
                get_fill_color="color",
            )
        ],
    )
