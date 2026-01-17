import pandas as pd
import streamlit as st

from valencianow import components, config, data, maps


def aggregated_sensor_data(data_now: pd.DataFrame, label: str) -> None:
    info = data.TB_PIPES[label]
    sensor_param = info[data.TB_SENSOR_PARAM]
    st.markdown("## ➕ Individual sensor data")
    with st.form(f"aggregated-sensor-{label}"):
        sensor = st.selectbox(
            "🔢 Select a sensor to show its data (sensor ids in map tooltips)",
            sorted(data_now[data.COL_SENSOR].values),
        )
        timespan = st.radio(
            "Select a time span: ",
            ["Today", "Last Week", "Last Month", "Last Year"],
            index=2,
            horizontal=True,
        )

        if st.form_submit_button("🔎 Find sensor data", use_container_width=True):
            components.historical_graph(
                info[data.TB_HIST_PIPE],
                timespan,
                int(sensor),
                info[data.TB_HIST_MEAS],
                info[data.TB_HIST_Y],
                sensor_param=sensor_param,
            )
            if timespan != "Today":
                st.markdown(f"#### Aggregated data ({timespan})")
                sensor_col_1, sensor_col_2 = st.columns(2)
                with sensor_col_1:
                    components.per_day_graph(
                        info[data.TB_PER_DAY_PIPE],
                        int(sensor),
                        timespan,
                        info[data.TB_PER_DAY_Y],
                        sensor_param=sensor_param,
                    )
                if timespan != "Last Week":
                    with sensor_col_2:
                        components.per_day_of_week_graph(
                            info[data.TB_PER_DOW_PIPE],
                            int(sensor),
                            timespan,
                            info[data.TB_PER_DOW_Y],
                            sensor_param=sensor_param,
                        )


def render_tab_car(tab) -> None:
    with tab:
        st.markdown(
            f"""ℹ️⠀Induction loops in different parts of the city that are able to measure the number
            of **cars** passing through them. Both maps represent *number of cars per hour*
            \n💾⠀Original data from [Valencia Open Data: Puntos medida tráfico espiras
            electromagnéticas]({config.CARS_DATA_URL}). Balizas V16 data obtained from
            [DGT - Dirección General de Tráfico](https://www.dgt.es)."""
        )
        car_date_info, car_date_reset = st.empty(), st.empty()
        car_selected_date = components.date_selector(1)
        traffic_data = data.load_data("cars_now", car_selected_date)
        car_selected_date = components.reset_date_filter(
            car_selected_date, car_date_reset
        )
        if traffic_data is None:
            st.error("No data found for selected date and time")
        else:
            max_date = traffic_data[data.COL_DATE].max()
            car_date_info.markdown(
                f"""\n 📅⠀Max date currently visualized: `{max_date}` (updated every hour)"""
            )
            # Load balizas data only when viewing current data (no date filter)
            balizas_data = None
            if car_selected_date is None:
                balizas_data = data.load_balizas_data()
            car_maps_col_1, car_maps_col_2 = st.columns(2)
            with car_maps_col_1:
                st.pydeck_chart(maps.traffic_now_heatmap(traffic_data, balizas_data))
            with car_maps_col_2:
                st.pydeck_chart(maps.traffic_now_elevation(traffic_data))
            aggregated_sensor_data(traffic_data, maps.LABEL_CAR)


def render_tab_bike(tab) -> None:
    with tab:
        st.markdown(
            f"""ℹ️⠀Induction loops in different parts of the city that are able to measure the number
            of **bikes** passing through them. Both maps represent *number of bikes per hour*
            \n💾⠀Original data from [Valencia Open Data: Puntos de medida espiras
            electromagneticas]({config.BIKES_DATA_URL}). """
        )
        bike_date_info, bike_reset = st.empty(), st.empty()
        bike_date = components.date_selector(2)
        traffic_bike_data = data.load_data("bikes_now", bike_date)
        bike_date = components.reset_date_filter(bike_date, bike_reset)
        if traffic_bike_data is None:
            st.error("No data found for selected date and time")
        else:
            max_date = traffic_bike_data[data.COL_DATE].max()
            bike_date_info.markdown(f""" \n 📅⠀Max date currently visualized: `{max_date}`
            (updated every 30 min)""")
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
            f""" **1**: `hazardous`, **2**: `very unhealthy`, **3**: `unhealthy`, **4**: `moderate`,
        **5**: `fair`, **6**: `good`\n\n💾⠀Original data from [Valencia Open
        Data: Estacions contaminació atmosfèriques]({config.AIR_DATA_URL}).  """
        )
        air_date_info, air_date_reset = st.empty(), st.empty()
        air_date = components.date_selector(3)
        air_quality_data = data.load_data("air_now", air_date, local_time=True)
        air_date = components.reset_date_filter(air_date, air_date_reset)
        if air_quality_data is None:
            st.error("No data found for selected date and time")
        else:
            max_date = air_quality_data[data.COL_DATE].max()
            air_date_info.markdown(f"""\n 📅⠀Max date currently visualized: `{max_date}`
            (updated every hour)""")
            st.pydeck_chart(maps.air_now_scatterplot(air_quality_data))
        aggregated_sensor_data(air_quality_data, maps.LABEL_AIR)


def main() -> None:
    tab_car, tab_bike, tab_air = components.header()
    render_tab_car(tab_car)
    render_tab_bike(tab_bike)
    render_tab_air(tab_air)


if __name__ == "__main__":
    main()
