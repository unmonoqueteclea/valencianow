#!/bin/bash
set -euo pipefail

GEOJSON_URL="https://geoportal.valencia.es/apps/OpenData/Trafico/tra_espiras_bici_p.json"

# Fetch GeoJSON snapshot
curl --fail --max-time 30 "$GEOJSON_URL" > /tmp/bikes_traffic.json

# Validate the response contains a features array (guards against CDN error pages
# or empty responses that curl --fail would not catch)
jq -e '.features | length > 0' /tmp/bikes_traffic.json > /dev/null

# Transform to NDJSON and POST to Tinybird Events API.
# Rows are skipped when:
#   - hora_actualizacion is null, not a string, or not 14 chars (inactive sensors
#     or malformed data — storing them would corrupt the sorting key)
#   - geometry is null (no usable coordinates)
jq -c '
  .features[]
  | select(
      .properties.hora_actualizacion != null
      and (.properties.hora_actualizacion | type) == "string"
      and (.properties.hora_actualizacion | length) == 14
      and .geometry != null
    )
  | {
      last_edited_date: (.properties.hora_actualizacion |
        .[0:4] + "-" + .[4:6] + "-" + .[6:8] + " " +
        .[8:10] + ":" + .[10:12] + ":" + .[12:14]),
      idpm: .properties.idpm,
      ih: .properties.ih,
      geo_point_2d: (
        (.geometry.coordinates[1] | tostring) + "," +
        (.geometry.coordinates[0] | tostring)
      )
    }
' /tmp/bikes_traffic.json \
| curl --fail --max-time 60 \
    -X POST "${TINYBIRD_HOST}/v0/events?name=bikes" \
    -H "Authorization: Bearer ${TINYBIRD_TOKEN}" \
    --data-binary @-
