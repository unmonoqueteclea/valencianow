# streamlit-cloud won't install the package, so we can't do:
# from valencianow import config
import config  # type: ignore
import data  # type: ignore
import plotly.express as px
import streamlit as st

logger = config.LOGGER


def header():
    """Render the application header and the main tab-based menu"""
    st.set_page_config(page_title=config.APP_NAME, page_icon="🦇", layout="wide")
    st.header(f"🦇 {config.APP_NAME}")
    st.markdown(
        """⌚ Real-time traffic information about the city of **Valencia**
        (Spain). Powered by: [Tinybird](https://www.tinybird.co/) and
  [Streamlit](https://streamlit.io/)."""
    )
    st.markdown(
        """Built with ❤️ (and **public data sources**) by Pablo González Carrizo
  ([@unmonoqueteclea](https://twitter.com/unmonoqueteclea)).  More information in
  [my blog](https://unmonoqueteclea.github.io).

   """
    )
    return st.tabs(["🚙 Car Traffic", "🚴 Bike Traffic", "🍃 Air Quality"])


def date_selector(num: int) -> str | None:
    selected_date: str | None = None
    with st.form(f"date_selector_{num}", clear_on_submit=True):
        col_1, col_2 = st.columns(2)
        with col_1:
            partial_date = st.date_input(
                "Select max date", format="YYYY-MM-DD", value=None
            )  # type: ignore
        with col_2:
            partial_time = st.time_input("Select max time", value=None)
        submitted = st.form_submit_button(
            "📅 Change visualization date", use_container_width=True
        )
        if submitted:
            if not partial_time or not partial_date:
                st.error("Select a date and a time")
            else:
                selected_date = f"{partial_date} {partial_time}"
            logger.info(f"Selected date is {selected_date}")
    return selected_date


def reset_date_filter(date: str | None, reset) -> str | None:
    if date:
        msg = f"📅 Showing data from _{date}_. **Click to reset date**"
        if reset.button(msg, use_container_width=True, type="primary"):
            date = None
    return date


def historical_graph(
    pipe: str, timespan: str, sensor: str, measurement: str, y_axis: str
) -> None:
    data_sensor = data.load_data(pipe, None, sensor, filter_timespan=timespan)
    if data_sensor is not None:
        st.markdown(f"#### Historical data: {measurement} ({timespan})")
        data_sensor = data_sensor.sort_values(by="datetime")
        fig = px.line(
            data_sensor, x="datetime", y=y_axis, markers=True, line_shape="spline"
        )
        st.plotly_chart(fig, theme="streamlit", use_container_width=True)


def per_day_graph(pipe: str, sensor: str, timespan: str, y_axis):
    st.markdown("**📅 Data by day**")
    data_agg_sensor = data.load_data(pipe, None, sensor, filter_timespan=timespan)
    fig = px.bar(
        data_agg_sensor,
        x="day",
        y=y_axis,
        hover_data={"day": "|%A - %B %d, %Y"},
    )
    fig.update_xaxes(tickformat="%a - %b %d")
    st.plotly_chart(fig, theme="streamlit", use_container_width=True)


def per_day_of_week_graph(pipe: str, sensor: str, timespan: str, y_axis):
    st.markdown("**📅 Data by day of week**")
    data_agg_week_sensor = data.load_data(pipe, None, sensor)
    day_name_map = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }
    data_agg_week_sensor["day_of_week"] = data_agg_week_sensor["day_of_week"].map(
        day_name_map
    )
    fig = px.bar(data_agg_week_sensor, x="day_of_week", y=y_axis)
    st.plotly_chart(fig, theme="streamlit", use_container_width=True)
