# Day 41 detection evidence

Open **Detection evidence** on the dashboard and choose a stored prediction. The selector loads the latest 20 records via `GET /detections`. Detail loads via `GET /detections/{detection_id}`. The API groups the opposite detector's stored predictions by run ID and observation row ID, including observations made up of several events. The view is read-only.

The rule output shows the measured value, threshold and aggregation unit. The ML output shows the stored prediction with its model version and, when available and valid, the frozen model's probability of the malicious class. This probability describes the model output for this observation. Observed features, event IDs and log references support inspection. The expected label in run metadata records the collection context separately from both predictions.

The project owner uses three synthetic normalized fixtures for the scenario review. CI ingests, processes, and reads them over HTTP using the production FastAPI routes and the frozen detector. The fixture database is disposable.

| Scenario ID | Display name | Wording checked |
| --- | --- | --- |
| `brute_force` | Brute force | Three failed SSH password events meet the rule threshold in one 60-second window. |
| `sql_injection` | SQL injection | The rule counts SQL-like token matches over the web run. A token match alone cannot establish that an injection succeeded. |
| `reconnaissance` | Network reconnaissance | The rule counts distinct destination ports observed by the logging services within one 60-second window. |

The dashboard shows evidence references and observed features. Raw log bodies remain in their evidence archive.
