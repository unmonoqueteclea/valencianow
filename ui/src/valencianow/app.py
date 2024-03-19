"""valencianow streamlit-based application

Dashboard with real-time information about the city of Valencia
(Spain).

"""

import typing

import pandas as pd
import plotly.express as px
import streamlit as st

# streamlit-cloud won't install the package, so we can't
# do: from valencianow import config
import config  # type: ignore
import maps  # type: ignore


def ui_header():
    st.set_page_config(page_title=config.APP_NAME, page_icon="🦇", layout="wide")
    st.header(f"🦇 {config.APP_NAME}")
    st.markdown(
        """⌚ Real-time traffic information about the city of **Valencia**
        (Spain)."""
    )
    st.markdown(
        """Built with ❤️ (and **public data sources**) by Pablo González Carrizo
  ([@unmonoqueteclea](https://twitter.com/unmonoqueteclea)). More in
  [my blog](https://unmonoqueteclea.github.io).

  Powered by: """
    )
    col1, col2, _ = st.columns([0.2, 0.2, 0.6])
    with col1:
        st.image(config.TINYBIRD_LOGO, width=100)
    with col2:
        st.image(config.STREAMLIT_LOGO, width=120)
    st.divider()
    return st.tabs(["🚙 car traffic", "🚴 bike traffic", "🍃 air quality"])


def ui_date_selector(num) -> typing.Optional[str]:
    _date = None
    with st.form(f"date_selector_{num}", clear_on_submit=True):
        date_selector_col_1, date_selector_col_2 = st.columns(2)
        with date_selector_col_1:
            selected_date = st.date_input(
                "Select max date", format="YYYY-MM-DD", value=None
            )
        with date_selector_col_2:
            selected_time = st.time_input("Select max time", value=None)
        submitted = st.form_submit_button(
            "📅 Change visualization date", use_container_width=True
        )
        if submitted:
            if not selected_time or not selected_date:
                st.error("Missing date or time")
            else:
                _date = f"{selected_date} {selected_time}"
    return _date


def ui_reset_date_filter(date, reset) -> typing.Optional[str]:
    if date:
        msg = "📅 Date filter applied. **Click to reset max date and time**"
        if reset.button(msg, use_container_width=True, type="primary"):
            date = None
    return date


def ui_aggregated_sensor_data(data_now: pd.DataFrame, label: str) -> None:
    _info = {
        maps.LABEL_AIR: {
            "history_pipe": "air_history",
            "history_measurement": "air quality",
            "history_y": "ica",
            "per_day_pipe": "air_per_day",
            "per_day_y": "avg_ica",
            "per_dow_pipe": "air_per_day_of_week",
            "per_dow_y": "avg_ica",
        },
        maps.LABEL_CAR: {
            "history_pipe": "cars_history",
            "history_measurement": "cars per hour",
            "history_y": "cars_per_hour",
            "per_day_pipe": "cars_per_day",
            "per_day_y": "avg_cars_per_hour",
            "per_dow_pipe": "cars_per_day_of_week",
            "per_dow_y": "avg_cars_per_hour",
        },
        maps.LABEL_BIKE: {
            "history_pipe": "bikes_history",
            "history_measurement": "bikes per hour",
            "history_y": "bikes_per_hour",
            "per_day_pipe": "bikes_per_day",
            "per_day_y": "avg_bikes_per_hour",
            "per_dow_pipe": "bikes_per_day_of_week",
            "per_dow_y": "avg_bikes_per_hour",
        },
    }
    info = _info[label]
    st.markdown("## ➕ individual sensor data")
    with st.form(f"aggregated-sensor-{label}"):
        sensor = st.selectbox(
            "🔢 Select a sensor to show its data (sensor numbers in map tooltips)",
            sorted(data_now.sensor.values),
        )
        if st.form_submit_button("🔎 Find sensor data", use_container_width=True):

            # historical sensor data
            data_sensor = config.load_data(info["history_pipe"], None, sensor)
            if data_sensor is not None:
                st.markdown(f"#### historical data: {info['history_measurement']}")
                data_sensor = data_sensor.sort_values(by="datetime")
                fig = px.line(
                    data_sensor, x="datetime", y=info["history_y"], markers=True
                )
                st.plotly_chart(fig, theme="streamlit", use_container_width=True)

            # aggregated data
            st.markdown("#### aggregated data")
            sensor_col_1, sensor_col_2 = st.columns(2)
            with sensor_col_1:
                st.markdown("**📅 data by day**")
                data_agg_sensor = config.load_data(info["per_day_pipe"], None, sensor)
                fig = px.bar(data_agg_sensor, x="day", y=info["per_day_y"])
                st.plotly_chart(fig, theme="streamlit", use_container_width=True)
            with sensor_col_2:
                st.markdown("**📅 data by day of week (1 is Monday)**")
                data_agg_week_sensor = config.load_data(
                    info["per_dow_pipe"], None, sensor
                )
                fig = px.bar(data_agg_week_sensor, x="day_of_week", y=info["per_dow_y"])
                st.plotly_chart(fig, theme="streamlit", use_container_width=True)


def ui_tab_car(tab) -> None:
    with tab:
        st.markdown(
            """ℹ️ Electromagnetic coils in different parts of the city
            that are able to measure the number of **cars** passing
            through them. Both maps represent **number of cars per
            hour**"""
        )
        _date_info, _reset = st.empty(), st.empty()
        _date = ui_date_selector(1)
        data_now = config.load_data("cars_now", _date)
        _date = ui_reset_date_filter(_date, _reset)
        if data_now is None:
            st.error("No data found for selected date and time")
        else:
            max_date = data_now.date.max()
            _date_info_text = f"""💾 Original data from [Valencia Open Data]({config.SOURCE_CARS_NOW}).
            \n 📅 **Currently showing data from**: `{max_date}` (**updated every hour**)"""
            _date_info.markdown(_date_info_text)
            car_maps_col_1, car_maps_col_2 = st.columns(2)
            with car_maps_col_1:
                maps.traffic_now_heatmap(data_now)
            with car_maps_col_2:
                maps.traffic_now_elevation(data_now)
            ui_aggregated_sensor_data(data_now, maps.LABEL_CAR)


def ui_tab_bike(tab) -> None:
    with tab:
        st.markdown(
            """ℹ️ Electromagnetic coils in different parts of the city
            that are able to measure the number of **bikes** passing
            through them. Both maps represent **number of bikes per
            hour**"""
        )
        _date_info, _reset = st.empty(), st.empty()
        _date = ui_date_selector(2)
        data_now = config.load_data("bikes_now", _date)
        _date = ui_reset_date_filter(_date, _reset)
        if data_now is None:
            st.error("No data found for selected date and time")
        else:
            max_date = data_now.date.max()
            _date_info_text = f"""💾 Original data from [Valencia Open Data]({config.SOURCE_BIKES_NOW}).
            \n 📅 **Currently showing data from**: `{max_date}` (**updated every 15 min**)"""
            _date_info.markdown(_date_info_text)
            bike_maps_col_1, bikes_maps_col_2 = st.columns(2)
            with bike_maps_col_1:
                maps.traffic_now_heatmap(data_now, is_bike=True)
            with bikes_maps_col_2:
                maps.traffic_now_elevation(data_now, is_bike=True)
            ui_aggregated_sensor_data(data_now, maps.LABEL_BIKE)


def ui_tab_air(tab) -> None:
    with tab:
        st.markdown(
            """ℹ️ Air quality measurements
        ([ICA](https://www.miteco.gob.es/es/calidad-y-evaluacion-ambiental/temas/atmosfera-y-calidad-del-aire/calidad-del-aire/ica.html))
        in different parts of the city. Possible values are:"""
        )
        st.markdown(
            """ **1**: `extremely bad`, **2**: `very bad`, **3**: `bad`,
        **4**: `average`, **5**: `mostly good`,  **6**: `good`."""
        )
        _date_info, _reset = st.empty(), st.empty()
        _date = ui_date_selector(3)
        data_now = config.load_data("air_now", _date)
        _date = ui_reset_date_filter(_date, _reset)
        if data_now is None:
            st.error("No data found for selected date and time")
        else:
            max_date = data_now.date.max()
            _date_info_text = f"""💾 Original data from [Valencia Open Data]({config.SOURCE_BIKES_NOW}).
            \n 📅 **Currently showing data from**: `{max_date}` (**updated every hour**)"""
            _date_info.markdown(_date_info_text)
            maps.air_now_scatterplot(data_now)
        ui_aggregated_sensor_data(data_now, maps.LABEL_AIR)


def main() -> None:
    tab_car, tab_bike, tab_air = ui_header()
    ui_tab_car(tab_car)
    ui_tab_bike(tab_bike)
    ui_tab_air(tab_air)


if __name__ == "__main__":
    main()
