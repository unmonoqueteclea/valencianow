"""valencia-now Streamlit-based application

Dashboard with real-time information about the city of Valencia
(Spain).

"""

import components  # type: ignore

# streamlit-cloud won't install the package, so we can't do:
# from valencianow import config
import config  # type: ignore
import data  # type: ignore
import maps  # type: ignore
import pandas as pd
import streamlit as st


def aggregated_sensor_data(data_now: pd.DataFrame, label: str) -> None:
    info = data.PIPES[label]
    st.markdown("## ➕ individual sensor data")
    with st.form(f"aggregated-sensor-{label}"):
        sensor = st.selectbox(
            "🔢 Select a sensor to show its data (sensor numbers in map tooltips)",
            sorted(data_now.sensor.values),
        )
        if st.form_submit_button("🔎 Find sensor data", use_container_width=True):
            components.historical_graph(
                info["hist_pipe"], sensor, info["hist_meas"], info["hist_y"]
            )
            st.markdown("#### aggregated data")
            sensor_col_1, sensor_col_2 = st.columns(2)
            with sensor_col_1:
                components.per_day_graph(
                    info["per_day_pipe"], sensor, info["per_day_y"]
                )
            with sensor_col_2:
                components.per_day_of_week_graph(
                    info["per_dow_pipe"], sensor, info["per_dow_y"]
                )


def render_tab_car(tab) -> None:
    with tab:
        st.markdown(
            """ℹ️ Induction loops in different parts of the city that
            are able to measure the number of **cars** passing through
            them. Both maps represent **number of cars per hour**"""
        )
        car_date_info, car_date_reset = st.empty(), st.empty()
        car_selected_date = components.date_selector(1)
        traffic_data = data.load_data("traffic_cars_now", car_selected_date)
        car_selected_date = components.reset_date_filter(
            car_selected_date, car_date_reset
        )
        if traffic_data is None:
            st.error("No data found for selected date and time")
        else:
            max_date = traffic_data.date.max()
            car_date_info.markdown(
                f"""💾 Original data from [Valencia Open
            Data]({config.CARS_DATA_URL}).  \n 📅 **Currently showing
            data from**: `{max_date}` (**updated every hour**)"""
            )
            car_maps_col_1, car_maps_col_2 = st.columns(2)
            with car_maps_col_1:
                st.pydeck_chart(maps.traffic_now_heatmap(traffic_data))
            with car_maps_col_2:
                st.pydeck_chart(maps.traffic_now_elevation(traffic_data))
            aggregated_sensor_data(traffic_data, maps.LABEL_CAR)


def render_tab_bike(tab) -> None:
    with tab:
        st.markdown(
            """ℹ️ Induction loops in different parts of the city that
            are able to measure the number of **bikes** passing
            through them. Both maps represent **number of bikes per
            hour**"""
        )
        bike_date_info, bike_reset = st.empty(), st.empty()
        bike_date = components.date_selector(2)
        traffic_bike_data = data.load_data("traffic_bikes_now", bike_date)
        bike_date = components.reset_date_filter(bike_date, bike_reset)
        if traffic_bike_data is None:
            st.error("No data found for selected date and time")
        else:
            max_date = traffic_bike_data.date.max()
            bike_date_info.markdown(f"""💾 Original data from
            [Valencia Open Data]({config.BIKES_DATA_URL}).  \n 📅
            **Currently showing data from**: `{max_date}` (**updated
            every 30 min**)""")
            bike_maps_col_1, bikes_maps_col_2 = st.columns(2)
            with bike_maps_col_1:
                st.pydeck_chart(
                    maps.traffic_now_heatmap(traffic_bike_data, is_bike=True)
                )
            with bikes_maps_col_2:
                st.pydeck_chart(
                    maps.traffic_now_elevation(traffic_bike_data, is_bike=True)
                )
            aggregated_sensor_data(traffic_bike_data, maps.LABEL_BIKE)


def render_tab_air(tab) -> None:
    with tab:
        st.markdown(
            """ℹ️ Air quality measurements
        ([ICA](https://www.miteco.gob.es/es/calidad-y-evaluacion-ambiental/temas/atmosfera-y-calidad-del-aire/calidad-del-aire/ica.html))
        in different parts of the city. Possible values are:"""
        )
        st.markdown(
            """ **1**: `hazardous`, **2**: `very unhealthy`, **3**: `unhealthy`,
        **4**: `moderate`, **5**: `fair`,  **6**: `good`."""
        )
        air_date_info, air_date_reset = st.empty(), st.empty()
        air_date = components.date_selector(3)
        air_quality_data = data.load_data("air_quality_now", air_date)
        air_date = components.reset_date_filter(air_date, air_date_reset)
        if air_quality_data is None:
            st.error("No data found for selected date and time")
        else:
            max_date = air_quality_data.date.max()
            air_date_info.markdown(f"""💾 Original data from [Valencia
            Open Data]({config.AIR_DATA_URL}).  \n 📅 **Currently
            showing data from**: `{max_date}` (**updated every
            hour**)""")
            st.pydeck_chart(maps.air_now_scatterplot(air_quality_data))
        aggregated_sensor_data(air_quality_data, maps.LABEL_AIR)


def main() -> None:
    tab_car, tab_bike, tab_air = components.header()
    render_tab_car(tab_car)
    render_tab_bike(tab_bike)
    render_tab_air(tab_air)


if __name__ == "__main__":
    main()
