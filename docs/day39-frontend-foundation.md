# Day 39 frontend foundation

The Vite app uses the existing Tailwind plugin. `AppShell` owns navigation and
layout. `ApiConnection` owns connection status and retry behavior. The typed API
client is separate from React components, and its health check calls FastAPI
`GET /health`. API health indicates reachability. Database readiness has a
separate backend endpoint.

Start FastAPI from the repository root using the pinned dependencies and
`python -m uvicorn app.main:app --app-dir backend`. From `frontend`, run
`npm ci` and `npm run dev`, then open `http://localhost:5173`. If the API is
elsewhere, copy `.env.example` to `.env.local` and set
`VITE_API_BASE_URL`. Set the backend's `FRONTEND_ORIGIN` to the exact browser
origin and restart both servers after changing configuration.

`npm run api:generate` regenerates TypeScript types from FastAPI OpenAPI.
The pinned generator and drift check follow the
[OpenAPI TypeScript CLI](https://openapi-ts.dev/cli). Hosted CI checks for schema
drift, builds the Tailwind app, and runs the frontend health client against a
live FastAPI process with the browser origin.

The solo project owner's field list is scenario, time, source and target where
available, separate rule and ML predictions, supporting evidence, and trusted
ground truth where appropriate. The generated contract reflects what the
backend actually exposes. The current summaries do not include source/target
addresses for every event. Rule evidence can include source and target for windowed
observations. Explanation sources belong to the later explanation features.
