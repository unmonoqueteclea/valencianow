import logging
import os

APP_NAME = "Valencia-Now"
TAB_CAR, TAB_BIKE, TAB_AIR = "car", "bike", "air"

VALENCIA_LAT, VALENCIA_LON = 39.46975, -0.37739

TINYBIRD_API = os.environ["TINYBIRD_HOST"]
TINYBIRD_TOKEN = os.environ["TINYBIRD_TOKEN"]

# urls of the original data sources
OPENDATA_VAL = "https://valencia.opendatasoft.com/explore/dataset"
CARS_DATA_URL = f"{OPENDATA_VAL}/punts-mesura-trafic-espires-electromagnetiques-puntos-medida-trafico-espiras-ele/"
BIKES_DATA_URL = f"{OPENDATA_VAL}/punts-mesura-bicis-espires-electromagnetiques-puntos-medida-bicis-espiras-electr/"
AIR_DATA_URL = f"{OPENDATA_VAL}/estacions-contaminacio-atmosferiques-estaciones-contaminacion-atmosfericas/"

logger = logging.getLogger("valencianow")
logger.setLevel(logging.DEBUG)
logger_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s [%(module)s] %(message)s")
logger_handler.setFormatter(formatter)
logger.addHandler(logger_handler)
