#!/bin/bash
set -euo pipefail

# Live ArcGIS MapServer endpoint — updated every ~3 minutes with real traffic data.
# outSR=4326 requests WGS84 coordinates directly (avoids UTM conversion).
# resultRecordCount=5000 ensures all ~1210 sensors are returned in one request.
MAPSERVER_URL="https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/208/query?where=1%3D1&outFields=idpm,ih,last_edited_date&f=json&outSR=4326&resultRecordCount=5000"

# Fetch MapServer JSON snapshot
curl --fail --max-time 30 "$MAPSERVER_URL" > /tmp/traffic.json

# Validate the response contains a features array (guards against server error responses
# that curl --fail would not catch)
jq -e '.features | length > 0' /tmp/traffic.json > /dev/null

# Transform to NDJSON and POST to Tinybird Events API.
# Rows are skipped when:
#   - last_edited_date is null (no valid timestamp — required as sorting key)
#   - geometry is null (no usable coordinates)
jq -c '
  .features[]
  | select(
      .attributes.last_edited_date != null
      and .geometry != null
    )
  | {
      last_edited_date: (.attributes.last_edited_date / 1000 | strftime("%Y-%m-%d %H:%M:%S")),
      idpm: .attributes.idpm,
      ih: .attributes.ih,
      geo_point_2d: ((.geometry.y | tostring) + "," + (.geometry.x | tostring))
    }
' /tmp/traffic.json \
| curl --fail --max-time 60 \
    -X POST "${TINYBIRD_HOST}/v0/events?name=cars" \
    -H "Authorization: Bearer ${TINYBIRD_TOKEN}" \
    --data-binary @-
