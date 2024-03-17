import typing

import plotly.express as px
import streamlit as st

import config
import maps


def ui_header():
    st.set_page_config(page_title=config.APP_NAME, page_icon="🦇", layout="wide")
    st.header(f"🦇 {config.APP_NAME}")
    st.markdown(
        """⌚ Real-time traffic information about the city of **Valencia**
        (Spain).

  Built with ❤️ (and **public data sources**) by Pablo González Carrizo
  ([unmonoqueteclea](https://unmonoqueteclea.github.io/)).

  Powered by: """
    )

    col1, col2, _ = st.columns([0.2, 0.2, 0.6])
    with col1:
        st.image(config.TINYBIRD_LOGO, width=130)
    with col2:
        st.image(config.STREAMLIT_LOGO, width=150)
    st.divider()
    return st.tabs(["🚙 car traffic", "🚴 bike traffic"])


def ui_date_selector(num) -> typing.Optional[str]:
    _date = None
    with st.form(f"date_selector_{num}", clear_on_submit=True):
        date_col_1, date_col_2 = st.columns(2)
        with date_col_1:
            selected_date = st.date_input(
                "Select max date", format="YYYY-MM-DD", value=None
            )
        with date_col_2:
            selected_time = st.time_input("Select time", value=None)
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
        msg = "📅 Max date applied. **Click to reset to date and time**"
        if reset.button(msg, use_container_width=True, type="primary"):
            date = None
    return date


def ui_aggregated_sensor_data(data_now, is_bike=False) -> None:
    label = "bike" if is_bike else "car"
    st.markdown("## ➕ individual sensor data")
    data_now.sensor.values.sort()
    with st.form(f"aggregated-sensor-{is_bike}"):
        sensor = st.selectbox(
            "🔢 Select a sensor to show its data (sensor number is shown in map tooltips)",
            data_now.sensor.values,
        )
        submit = st.form_submit_button("Find sensor data", use_container_width=True)
        if submit:
            data_sensor = config.load_data(f"{label}s_history", None, sensor)
            if data_sensor is not None:
                data_sensor = data_sensor.sort_values(by="datetime")
                fig = px.line(
                    data_sensor, x="datetime", y=f"{label}s_per_hour", markers=True
                )
                st.plotly_chart(fig, theme="streamlit", use_container_width=True)


def ui_tab_car(tab):
    with tab:
        st.markdown(
            """🚙 Electromagnetic coils in different parts of the city
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
            \n ⌚ **Showing data from**: `{max_date}` (**updated every hour**)"""
            _date_info.markdown(_date_info_text)
            col1, col2 = st.columns(2)
            with col1:
                maps.traffic_now_heatmap(data_now)
            with col2:
                maps.traffic_now_elevation(data_now)
            ui_aggregated_sensor_data(data_now)


def ui_tab_bike(tab):
    _date = None
    with tab:
        st.markdown(
            """🚴 Electromagnetic coils in different parts of the city
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
            \n ⌚ **Showing data from**: `{max_date}` (**updated every 15 min**)"""
            _date_info.markdown(_date_info_text)
            col1, col2 = st.columns(2)
            with col1:
                maps.traffic_now_heatmap(data_now, is_bike=True)
            with col2:
                maps.traffic_now_elevation(data_now, is_bike=True)
            ui_aggregated_sensor_data(data_now, is_bike=True)


def main() -> None:
    tab_car, tab_bike = ui_header()
    ui_tab_car(tab_car)
    ui_tab_bike(tab_bike)


if __name__ == "__main__":
    main()
