# Day 40 recent-events dashboard

Start the frontend and API using the [Day 39 instructions](day39-frontend-foundation.md).
Configure the database with the [Day 33 guide](day33-postgresql.md). The
dashboard calls `GET /events?limit=20` and preserves the API's newest-first
ordering. Use the [Day 34 ingestion API](day34-ingestion.md) to add normalized
events.

Each row shows the observed timestamp in UTC, source family, event type, run
ID, and log reference. The count describes only the events returned for this
view. These rows do not establish attack intent or report evaluation metrics.
The API response does not include raw log content.

The dashboard distinguishes loading, an empty database, and an unavailable
or invalid API response. Use **Refresh** to fetch another snapshot or
**Try again** after a request failure.

Hosted CI tests the client through FastAPI using a temporary database. The
test begins with an empty list, ingests two synthetic normalized records, and
checks the returned fields, newest-first order, and limit. The existing
PostgreSQL integration job remains in place.
