# Cars Traffic Datasource Migration

**Date:** 2026-04-02
**Status:** Approved for implementation

---

## Problem Statement

The Valencia cars traffic dataset previously available as CSV from `valencia.opendatasoft.com` is no longer accessible in that format. The new portal (`opendata.vlci.valencia.es`) provides the same data via a live GeoJSON endpoint at:

```
https://geoportal.valencia.es/apps/OpenData/Trafico/tra_espiras_p.json
```

Available formats are GeoJSON, WFS, KML, GML, SHZ, DWG — no CSV. The current GitHub Action (`append-cars.yml`) POSTs the old CSV URL directly to Tinybird, which now fails.

---

## Chosen Approach

**Transform in GitHub Action, keep Tinybird schema backward-compatible.**

A shell script (`.github/scripts/fetch_cars_traffic.sh`) fetches the GeoJSON, transforms it to NDJSON using `jq`, and POSTs it to the Tinybird Events API. The Tinybird `cars.datasource` schema is updated to reflect the new source fields, with a `FORWARD_QUERY` to preserve existing historical data. All 4 endpoint pipes remain unchanged.

---

## Key Decisions

### 1. Transformation location: shell script in `.github/scripts/`
Not inline in the workflow YAML. Keeps logic readable and locally testable (see Local Testing section).

### 2. Null/invalid timestamp rows are skipped
The new GeoJSON has some features where `hora_actualizacion` is `null` (inactive sensors with `ih = 0`). These rows are **dropped entirely** at transform time and never sent to Tinybird. Rationale: `last_edited_date` is the sorting key — null timestamps would corrupt ordering and produce meaningless historical records for sensors that aren't measuring anything.

Additionally, rows where `hora_actualizacion` is not a string, or is a string of length other than 14, are also skipped. The `jq` filter must do an explicit type and length guard before slicing — a numeric value or short/truncated string must not be coerced to a garbage datetime and silently inserted.

Features with a `null` or missing `geometry` are also skipped — no geometry means no usable `geo_point_2d`.

### 3. Tinybird ingestion: Events API
`POST /v0/events?name=cars` with NDJSON body. The old approach (POSTing a URL to the datasource append API) only works with directly downloadable flat formats. The Events API is the correct mechanism for streaming NDJSON.

**Auth:** Token must be passed as `Authorization: Bearer ${TINYBIRD_TOKEN}`. The existing `TINYBIRD_TOKEN` repo secret is used by the bikes/air workflows for datasource append — confirm it has `DATASOURCE:APPEND` scope (or is an admin token) before deploying. Run `tb --cloud token ls` to check.

**Content-Type:** The Tinybird Events API does not require a Content-Type header and works without it. Do not include it — the API infers the format from the body.

### 4. `geo_point_2d` format: `"lat,lon"` string
The new GeoJSON returns coordinates as `[longitude, latitude]` (GeoJSON standard). The script reverses them to `"lat,lon"` to match the format existing consumers expect.

### 5. Schema: only the 4 fields used by endpoints
The new source also provides `angulo` and `fecha_actualizacion`, but no endpoint consumes them. The new schema stores only: `last_edited_date`, `idpm`, `ih`, `geo_point_2d`. This keeps the datasource lean.

### 6. Field name mapping
| New source field | Tinybird field | Transformation |
|---|---|---|
| `hora_actualizacion` (String `"20221007121600"`, 14 chars) | `last_edited_date` (DateTime) | Slice: `[0:4]-[4:6]-[6:8] [8:10]:[10:12]:[12:14]` |
| `geometry.coordinates[1]` + `[0]` | `geo_point_2d` (String) | Reverse GeoJSON lon/lat → `"lat,lon"` string |
| `idpm` | `idpm` | Direct |
| `ih` | `ih` | Direct |

The `hora_actualizacion` slicing positions (0-indexed): year `[0:4]`, month `[4:6]`, day `[6:8]`, hour `[8:10]`, minute `[10:12]`, second `[12:14]`.

### 7. Timezone assumption
The old CSV URL specified `timezone=Europe/Madrid`. The new GeoJSON source provides no explicit timezone in `hora_actualizacion`. **Assumption: the new source timestamps are also Europe/Madrid local time**, consistent with the old source and with the city operating in that timezone. This is undocumented by the provider. If it turns out the new source is UTC, time-based queries will be off by 1–2 hours depending on DST.

### 8. Data model: snapshot ingestion (pre-existing design)
Each hourly run appends a full snapshot of all active sensors (~1,277 rows). This is identical to the old CSV behaviour. The `cars_now.pipe` finds "current" data via `WHERE last_edited_date = (SELECT max(last_edited_date) FROM cars)` — this is a pre-existing design issue, not introduced by this migration, and is out of scope here.

---

## Files to Change

| File | Change |
|---|---|
| `.github/scripts/fetch_cars_traffic.sh` | **New** — fetch GeoJSON, transform to NDJSON, POST to Events API |
| `.github/workflows/append-cars.yml` | Update to call the script; remove `on: push` trigger |
| `tinybird/datasources/cars.datasource` | Strip dead fields, update schema to 4 fields with json paths, add `FORWARD_QUERY` |

**Unchanged:** `cars_now.pipe`, `cars_history.pipe`, `cars_per_day.pipe`, `cars_per_day_of_week.pipe`

---

## Implementation Notes

### `cars.datasource` schema

The existing schema has **no `json:$.` path annotations** on any column. The new schema adds them. This means the migration is not purely a column-drop — it also adds path annotations to the 4 retained columns. This combination (column drops + annotation additions) may or may not follow the automatic ALTER path in Tinybird. **Run `tb deploy --check` before creating the deployment** to confirm acceptability.

A `FORWARD_QUERY` is included defensively. Per Tinybird docs, dropping columns alone is an automatic operation that doesn't require a FORWARD_QUERY. However, because the annotation additions make this a non-trivial schema change, keeping the FORWARD_QUERY ensures correct handling of existing data regardless.

```
SCHEMA >
    `last_edited_date` DateTime `json:$.last_edited_date`,
    `idpm` Int32 `json:$.idpm`,
    `ih` Nullable(Int32) `json:$.ih`,
    `geo_point_2d` String `json:$.geo_point_2d`

ENGINE "MergeTree"
ENGINE_SORTING_KEY "last_edited_date, idpm"

FORWARD_QUERY >
    SELECT last_edited_date, idpm, ih, geo_point_2d FROM cars
```

### Script logic (`fetch_cars_traffic.sh`)
The script opens with `set -euo pipefail` so any failure exits non-zero and fails the GitHub Action visibly.

```bash
#!/bin/bash
set -euo pipefail

GEOJSON_URL="https://geoportal.valencia.es/apps/OpenData/Trafico/tra_espiras_p.json"

# Fetch GeoJSON snapshot
curl --fail --max-time 30 "$GEOJSON_URL" > /tmp/traffic.json

# Validate the response contains a features array (guards against CDN error pages
# or empty responses that curl --fail would not catch)
jq -e '.features | length > 0' /tmp/traffic.json > /dev/null

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
' /tmp/traffic.json \
| curl --fail --max-time 60 \
    -X POST "${TINYBIRD_HOST}/v0/events?name=cars" \
    -H "Authorization: Bearer ${TINYBIRD_TOKEN}" \
    --data-binary @-
```

- `TINYBIRD_HOST` is the base URL without trailing slash (e.g. `https://api.tinybird.co`). Already in repo secrets.
- `TINYBIRD_TOKEN` already in repo secrets.

### GitHub Action (`append-cars.yml`)
- Remove `on: push` trigger — it causes full snapshot appends to production on every push to any branch.
- Keep only `workflow_dispatch` and `schedule: '0 * * * *'`.
- Invoke the script as `bash .github/scripts/fetch_cars_traffic.sh` (do not rely on execute bit).
- Pass secrets as environment variables to the script step.

### Deployment sequence
**Order matters — do not swap steps 1 and 3:**

1. Update `cars.datasource`, run `tb deploy --check` locally to validate
2. Deploy schema to cloud: `tb --cloud deployment create --wait --auto`
3. Merge the workflow change (new script + updated `append-cars.yml`)
4. Trigger a manual run via `workflow_dispatch`
5. **Immediately check for quarantine rows:** `tb --cloud datasource data cars_quarantine`
   — The Events API returns HTTP 202 (accepted) even when rows are quarantined. A silent quarantine would mean the ingestion looks successful but no data lands in the table. Zero quarantine rows = success.

---

## Local Testing

The spec is locally testable before touching cloud. Two approaches:

**Option A — Full end-to-end with live GeoJSON (requires local Tinybird server):**
1. Update `tinybird/datasources/cars.datasource` with the new schema
2. From the `tinybird/` directory: `tb build` (applies schema locally)
3. Get local token: `tb token ls`
4. Run the script against the local server:
   ```bash
   TINYBIRD_HOST=http://localhost:7181 \
   TINYBIRD_TOKEN=<token from tb token ls> \
   bash .github/scripts/fetch_cars_traffic.sh
   ```
5. Verify: `tb endpoint data cars_now`
6. Check quarantine: `tb datasource data cars_quarantine`

**Option B — Offline schema + pipe testing (no live GeoJSON needed):**
1. Create `tinybird/fixtures/cars.ndjson` with a few rows in the new 4-field format:
   ```json
   {"last_edited_date": "2026-04-02 10:00:00", "idpm": 2323, "ih": 251, "geo_point_2d": "39.4508,−0.3791"}
   {"last_edited_date": "2026-04-02 10:00:00", "idpm": 1001, "ih": 88, "geo_point_2d": "39.4712,−0.3864"}
   ```
2. `tb build` — ingests fixtures locally
3. Test all endpoint pipes: `tb endpoint data cars_now`, `tb endpoint data cars_history --idpm 2323`, etc.

Option B is faster for iterating on the schema and pipe queries. Option A confirms the full pipeline including the script logic and GeoJSON parsing.

---

## Known Limitations (Out of Scope)

- **Data gap**: The old action has been broken for some time. The GeoJSON endpoint only provides the current snapshot — historical backfill from this source is not possible. Gap is accepted.
- **`cars_now.pipe` correctness**: Uses global `max(last_edited_date)`; sensors with older timestamps are excluded from "current" results. Pre-existing issue.
- **No deduplication**: Every hourly run appends ~1,277 rows regardless of changes. Pre-existing issue.
- **No partition key**: MergeTree without `ENGINE_PARTITION_KEY` accumulates small parts over time. Pre-existing issue.
- **`on: push` in bikes/air workflows**: Same problem exists there, out of scope for this migration.

---

## Open Questions Resolved

- **Will historical data break?** No — `FORWARD_QUERY` maps old rows to the new 4-field schema; all 4 fields existed in the old schema with identical types.
- **Do endpoints need updating?** No — they query `last_edited_date`, `idpm`, `ih`, `geo_point_2d` which are preserved.
- **What about the `bikes` datasource?** Out of scope — still working, different source.
- **Is `jq` available on `ubuntu-latest`?** Yes — pre-installed on GitHub-hosted runners.
- **Are secrets already configured?** Yes — `TINYBIRD_TOKEN` and `TINYBIRD_HOST` already in repo secrets, confirmed by bikes/air workflows.
- **Token scope for Events API?** Requires `DATASOURCE:APPEND` scope. Verify with `tb --cloud token ls` before deploying.
