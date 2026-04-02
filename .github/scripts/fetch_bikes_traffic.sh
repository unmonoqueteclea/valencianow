#!/bin/bash
set -euo pipefail

# Live ArcGIS MapServer endpoint — updated regularly with real bike traffic data.
# outSR=4326 requests WGS84 coordinates directly (avoids UTM conversion).
# resultRecordCount=5000 ensures all ~150 sensors are returned in one request.
MAPSERVER_URL="https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/225/query?where=1%3D1&outFields=idpm,ih,last_edited_date&f=json&outSR=4326&resultRecordCount=5000"

# Fetch MapServer JSON snapshot
curl --fail --max-time 30 "$MAPSERVER_URL" > /tmp/bikes_traffic.json

# Validate the response contains a features array (guards against server error responses
# that curl --fail would not catch)
jq -e '.features | length > 0' /tmp/bikes_traffic.json > /dev/null

# Transform to NDJSON and POST to Tinybird Events API.
# Rows are skipped when:
#   - last_edited_date is null (no valid timestamp — required as sorting key)
#   - geometry is null (no usable coordinates)
# ih can be null (sensor exists but has no current reading) — stored as-is.
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
' /tmp/bikes_traffic.json \
| curl --fail --max-time 60 \
    -X POST "${TINYBIRD_HOST}/v0/events?name=bikes" \
    -H "Authorization: Bearer ${TINYBIRD_TOKEN}" \
    --data-binary @-
