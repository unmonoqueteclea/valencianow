#!/bin/bash
set -euo pipefail

# Live ArcGIS MapServer endpoint — updated hourly with real air quality data.
# Layer 156 = Estaciones contaminación atmosféricas.
# outSR=4326 requests WGS84 coordinates directly (avoids UTM conversion).
MAPSERVER_URL="https://geoportal.valencia.es/server/rest/services/OPENDATA/MedioAmbiente/MapServer/156/query?where=1%3D1&outFields=*&f=json&outSR=4326&resultRecordCount=5000"

# Fetch MapServer JSON snapshot
curl --fail --max-time 30 "$MAPSERVER_URL" > /tmp/air_quality.json

# Validate the response contains a features array (guards against server error responses
# that curl --fail would not catch)
jq -e '.features | length > 0' /tmp/air_quality.json > /dev/null

# Transform to NDJSON and POST to Tinybird Events API.
# Rows are skipped when:
#   - fecha_carg is null (no valid measurement timestamp)
#   - geometry is null (no usable coordinates)
# Field names are mapped from ArcGIS short names to the schema column names.
# fecha_carg arrives as a Unix timestamp in milliseconds.
jq -c '
  .features[]
  | select(
      .attributes.fecha_carg != null
      and .geometry != null
    )
  | {
      _objectid: .attributes.objectid,
      nom___nombre: .attributes.nombre,
      adre_a___direccion: .attributes.direccion,
      tipus_zona___tipo_zona: .attributes.tipozona,
      par_metres___par_metros: .attributes.parametros,
      mesuraments___mediciones: .attributes.mediciones,
      so2: .attributes.so2,
      no2: (.attributes.no2 // 0),
      o3: .attributes.o3,
      co: .attributes.co,
      pm10: .attributes.pm10,
      pm25: .attributes.pm25,
      tipoemision: .attributes.tipoemisio,
      fecha_carga: (.attributes.fecha_carg / 1000 | strftime("%Y-%m-%d %H:%M:%S")),
      calidad_ambiental: .attributes.calidad_am,
      fiwareid: .attributes.fiwareid,
      geo_shape: ({"coordinates": [.geometry.x, .geometry.y], "type": "Point"} | tojson),
      geo_point_2d: ((.geometry.y | tostring) + "," + (.geometry.x | tostring))
    }
' /tmp/air_quality.json \
| curl --fail --max-time 60 \
    -X POST "${TINYBIRD_HOST}/v0/events?name=air" \
    -H "Authorization: Bearer ${TINYBIRD_TOKEN}" \
    --data-binary @-
