# 🦇 valencia now

⌚ Real-time traffic information about the city of Valencia
(Spain). 🔗 [Check it now!](https://valencianow.unmonoqueteclea.freemyip.com/)

Data from **public sources** about **car traffic**, **bikes traffic**
and **air quality** is periodically collected and stored with
[Tinybird](https://www.tinybird.co/). Real time and aggregated data is
shown in an [Streamlit](https://streamlit.io/) application.

![maps](https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/maps.png?raw=true)

## How it works

The system consists of two main components: data ingestion pipelines
in `Tinybird` that collect and process sensor data from [Valencia's
open data portal](https://valencia.opendatasoft.com/), and a
`Streamlit` web application that visualizes real-time and historical
data through interactive maps and charts. Additionally, the application
displays live emergency vehicle locations from V16 beacons in the
Valencia region.

## Installation and Usage

First, set up the data infrastructure in Tinybird using the
configuration files in the `tinybird/` folder to create all required
data sources, pipes, and endpoints. A **GitHub Actions** pipeline
automatically collects data from Valencia's open data portal and sends
it to `Tinybird` on a periodic schedule.

Set the required environment variables for Tinybird access:

```bash
export TINYBIRD_HOST=https://api.tinybird.co
export TINYBIRD_TOKEN=your_token_here
```

Install [uv](https://docs.astral.sh/uv/) and run the `Streamlit` application:

```bash
cd ui
uv run streamlit run src/valencianow/app.py
```
