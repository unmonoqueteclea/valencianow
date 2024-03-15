import streamlit as st

from valencianow import config, maps


def ui_header():
    st.set_page_config(page_title=config.APP_NAME, page_icon="🦇", layout="wide")
    st.header(f"🦇 {config.APP_NAME}")
    st.markdown(
        """⌚ Real-time information about the city of **Valencia**
        (Spain).

  Built with ❤️ (and **public data sources**) by Pablo González Carrizo
  ([unmonoqueteclea](https://unmonoqueteclea.github.io/)).

  Powered by """
    )

    col1, col2, _ = st.columns([0.1, 0.1, 0.8])
    with col1:
        st.image(config.TINYBIRD_LOGO, width=130)
    with col2:
        st.image(config.STREAMLIT_LOGO, width=150)
    st.divider()
    tab_car, tab_bike = st.tabs(["🚙 car traffic", "🚴 bike traffic"])
    return tab_car, tab_bike


def ui_tab_car(tab):
    _date = None
    with tab:
        st.markdown(
            """ℹ️ Electromagnetic coils, in different parts of the city,
            that are able to measure the number of **cars** passing over
            them. Both maps represent **number of cars per hour**"""
        )
        _date_info = st.empty()
        _reset = st.empty()
        with st.form("date_selector", clear_on_submit=True):
            date_col_1, date_col_2 = st.columns(2)
            with date_col_1:
                selected_date = st.date_input(
                    "Select max date", format="YYYY-MM-DD", value=None
                )
            with date_col_2:
                selected_time = st.time_input("Select time", value=None)
            submitted = st.form_submit_button(
                "Change visualization date",
                use_container_width=True,
            )
            if submitted:
                _date = f"{selected_date} {selected_time}"
        cars_now = config.load_data(
            "cars_now", _date, use_cached_data=config.USE_CACHED_DATA
        )
        _date_info_text = f"""💾 Original data from [Valencia Open Data]({config.SOURCE_CARS_NOW}).
                \n ⌚ **Showing data from**: `{cars_now.at[0, 'date']}` (**updated every hour**)"""
        _date_info.markdown(_date_info_text)
        if _date:
            if _reset.button(
                "📅 Max date applied. **Press to reset to current date and time**",
                use_container_width=True,
                type="primary",
            ):
                _date = None
        col1, col2 = st.columns(2)
        with col1:
            maps.traffic_now_heatmap(cars_now)
        with col2:
            maps.traffic_now_elevation(cars_now)


def ui_tab_bike(tab):
    _date = None
    with tab:
        st.markdown(
            """ℹ️ Electromagnetic coils, in different parts of the city,
            that are able to measure the number of **bikes** passing over
            them. Both maps represent **number of bikes per hour**"""
        )
        _date_info = st.empty()
        _reset = st.empty()
        with st.form("date_selector_2", clear_on_submit=True):
            date_col_1, date_col_2 = st.columns(2)
            with date_col_1:
                selected_date = st.date_input(
                    "Select max date", format="YYYY-MM-DD", value=None
                )
            with date_col_2:
                selected_time = st.time_input("Select time", value=None)
            submitted = st.form_submit_button(
                "Change visualization date",
                use_container_width=True,
            )
            if submitted:
                _date = f"{selected_date} {selected_time}"
        cars_now = config.load_data(
            "bikes_now", _date, use_cached_data=config.USE_CACHED_DATA
        )
        _date_info_text = f"""💾 Original data from [Valencia Open Data]({config.SOURCE_BIKES_NOW}).
                \n ⌚ **Showing data from**: `{cars_now.at[0, 'date']}` (**updated every hour**)"""
        _date_info.markdown(_date_info_text)
        if _date:
            if _reset.button(
                "📅 Max date applied. **Press to reset to current date and time**",
                use_container_width=True,
                type="primary",
            ):
                _date = None
        col1, col2 = st.columns(2)
        with col1:
            maps.traffic_now_heatmap(cars_now, is_bike=True)
        with col2:
            maps.traffic_now_elevation(cars_now, is_bike=True)


def main():
    tab_car, tab_bike = ui_header()
    ui_tab_car(tab_car)
    ui_tab_bike(tab_bike)


if __name__ == "__main__":
    main()
