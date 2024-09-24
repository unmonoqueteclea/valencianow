import logging
import os

LOGGER = logging.getLogger("valencia-now")
LOGGER.setLevel(logging.DEBUG)
logger_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s [%(module)s] %(message)s")
logger_handler.setFormatter(formatter)
LOGGER.addHandler(logger_handler)


APP_NAME = "valencia-now"

TINYBIRD_API = "https://api.tinybird.co/v0/pipes/"
TINYBIRD_TOKEN = os.environ["TINYBIRD_TOKEN_VLC"]

# urls of the original data sources
OPENDATA_VAL = "https://valencia.opendatasoft.com/explore/dataset"
CARS_DATA_URL = f"{OPENDATA_VAL}/punts-mesura-trafic-espires-electromagnetiques-puntos-medida-trafico-espiras-ele/"
BIKES_DATA_URL = f"{OPENDATA_VAL}/punts-mesura-bicis-espires-electromagnetiques-puntos-medida-bicis-espiras-electr/"
AIR_DATA_URL = f"{OPENDATA_VAL}/estacions-contaminacio-atmosferiques-estaciones-contaminacion-atmosfericas/"

DATA_CACHE_SECONDS = 600  # 10 minutes

# you are not expected to change any of the followng, they are just constants
TAB_CAR = "car"
TAB_BIKE = "bike"
TAB_AIR = "air"
