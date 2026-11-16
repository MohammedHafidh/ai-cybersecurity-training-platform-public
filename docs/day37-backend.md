# Day 37 history and frozen evaluation

The existing detection history endpoints read PostgreSQL. Process a stored run
once and retrieve the same detection IDs after the application restarts.
The integration test verifies this behavior on PostgreSQL 16 in hosted CI.
Trusted labels remain in the combined response's ground truth object.
Stored predictions and their observed evidence stay separate.

`GET /evaluation/summary` reads the checked-in Day 32 evaluation JSON.
The response includes rule and model versions, aggregation, and overall and
per-source metrics with confusion matrices. The frontend should use this
endpoint for official metrics. It does not compute metrics from live history
or access private test evidence. Missing or invalid artifacts return `503`.

FastAPI initializes the configured database engine at startup and disposes it
on shutdown. Schema setup remains the explicit Day 33 command. Without a
database, liveness and evaluation remain available while storage routes return
`503`. Invalid requests return field locations and validation messages with
submitted values omitted.

Set `FRONTEND_ORIGIN` to one exact browser origin before starting the API.
The default is `http://localhost:5173`. CORS allows GET and POST with JSON
content and no credential sharing. Deploy the API only in a trusted environment.
Independent teammate review was unavailable. Automated negative tests cover
missing fields, invalid scenarios, and label separation.
