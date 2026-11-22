import { useEffect, useState } from "react";
import { Observation } from "./components/DetectionEvidence";
import { type DetectionDetail } from "./api/client";
import {
  api,
  base,
  navigate,
  remember,
  type Exercise,
  type Lesson,
} from "./training";
import { AskAI } from "./AskAI";
import { Quiz, Completion } from "./Quiz";

const stages: Record<string, string> = {
  preparing: "Preparing isolated lab",
  starting: "Starting approved target",
  activity: "Running controlled activity",
  capturing: "Collecting fresh logs",
  normalizing: "Parsing and preparing features",
  rules: "Running rule detector",
  ml: "Running frozen ML detector",
  saving: "Saving results",
  ready: "Analysis ready",
};

export function StartExercise({ lesson }: { lesson: Lesson }) {
  const [ready, setReady] = useState<{
    ready: boolean;
    message: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ ready: boolean; message: string }>("/training/readiness")
      .then(setReady)
      .catch((e) => setReady({ ready: false, message: e.message }));
  }, [lesson.id]);
  async function start(mode: "live" | "sample") {
    setBusy(true);
    setError("");
    try {
      const e = await api<Exercise>("/training/exercises", {
        method: "POST",
        body: JSON.stringify({ scenario: lesson.id, mode }),
      });
      remember(lesson.id, e.id);
      navigate("/exercises/" + e.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="start-exercise">
      <p className="muted" role="status">
        {ready?.message || "Checking the local learning environment…"}
      </p>
      <div className="actions">
        <button
          className="button"
          onClick={() => void start("live")}
          disabled={busy || !ready?.ready}
        >
          Start Controlled Exercise
        </button>
        <button onClick={() => void start("sample")} disabled={busy}>
          Sample / Demonstration Mode
        </button>
      </div>
      <p className="muted">
        Live creates fresh evidence. Demonstration mode uses clearly labeled
        synthetic benign activity and never substitutes for a failed live run.
      </p>
      {error && (
        <p role="alert" className="notice">
          {error}
        </p>
      )}
    </div>
  );
}

export function ExercisePage({
  id,
  view,
  lessons,
}: {
  id: string;
  view: string;
  lessons: Lesson[];
}) {
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [error, setError] = useState("");
  const [details, setDetails] = useState<DetectionDetail[]>([]);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const e = await api<Exercise>("/training/exercises/" + id);
        if (!active) return;
        setExercise(e);
        if (e.status === "running") timer = setTimeout(load, 500);
        else if (e.status === "ready" && view === "exercise")
          navigate("/exercises/" + id + "/analysis");
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id, view]);
  useEffect(() => {
    if (exercise?.status === "ready")
      Promise.all(
        exercise.result.detection_ids
          .filter((_, i) => i % 2 === 0)
          .map((key) => api<DetectionDetail>("/detections/" + key)),
      )
        .then(setDetails)
        .catch((e) => setError(e.message));
  }, [exercise?.status, id]);
  useEffect(() => {
    if (
      view === "analysis" &&
      exercise?.status === "ready" &&
      location.hash.endsWith("?focus=ai")
    )
      requestAnimationFrame(() =>
        document.getElementById("ask-ai")?.scrollIntoView(),
      );
  }, [view, exercise?.status]);
  if (error)
    return (
      <div role="alert" className="notice">
        {error} <a href="#/">Return home</a>
      </div>
    );
  if (!exercise) return <p role="status">Loading your exercise…</p>;
  const l = lessons.find((l) => l.id === exercise.scenario);
  if (!l) return <p>Loading the lesson…</p>;
  return (
    <>
      <a className="text-link" href={"#/scenarios/" + l.id}>
        ← {l.title} guide
      </a>
      <div className="exercise-heading">
        <p className="eyebrow">
          {exercise.mode === "live"
            ? "Live Controlled Exercise"
            : "Sample / Demonstration Mode"}
        </p>
        <h1>{l.title}</h1>
        <p className="lead">
          {exercise.mode === "live"
            ? "Fresh evidence from the approved isolated activity."
            : "Synthetic benign evidence for learning—not a newly executed attack."}
        </p>
      </div>
      {exercise.status !== "ready" ? (
        <section aria-live="polite">
          <h2>
            {exercise.status === "running"
              ? "Follow the activity."
              : "The exercise stopped."}
          </h2>
          <ol className="execution-stages">
            {Object.entries(stages).filter(([key]) => exercise.mode === "live" || !["starting", "activity"].includes(key)).map(([key, label]) => (
              <li key={key} className={exercise.stage === key ? "current" : ""}>
                <span>
                  {exercise.history.some((s) => s.stage === key) ? "●" : "○"}
                </span>
                {exercise.mode === "sample" && key === "capturing" ? "Reading synthetic demonstration" : label}
                {exercise.stage === key && exercise.status === "failed"
                  ? " — failed"
                  : ""}
              </li>
            ))}
          </ol>
          {exercise.error && (
            <p className="notice" role="alert">
              {exercise.error}
            </p>
          )}
          {exercise.status === "running" && (
            <button
              onClick={() =>
                api("/training/exercises/" + id + "/cancel", {
                  method: "POST",
                  body: "{}",
                }).catch((e) => setError(e.message))
              }
            >
              Cancel exercise
            </button>
          )}
          {exercise.status !== "running" && (
            <a href={"#/scenarios/" + l.id}>
              Return to guide and review readiness
            </a>
          )}
        </section>
      ) : (
        <>
          <nav className="journey-nav" aria-label="Exercise steps">
            <a
              href={"#/exercises/" + id + "/analysis"}
              aria-current={view === "analysis" ? "step" : undefined}
            >
              01 / Evidence analysis
            </a>
            <a
              href={"#/exercises/" + id + "/quiz"}
              aria-current={view === "quiz" ? "step" : undefined}
            >
              02 / Knowledge check
            </a>
            <a
              href={"#/exercises/" + id + "/complete"}
              aria-current={view === "complete" ? "step" : undefined}
            >
              03 / Completion
            </a>
          </nav>
          {view === "analysis" && (
            <>
              <section className="analysis-section">
                <p className="eyebrow">01 / What actually happened</p>
                <h2>Read the evidence.</h2>
                <p>{exercise.result.redaction_notice}</p>
                {exercise.result.records.map((r) => (
                  <article key={r.event_id} id={"record-" + r.number} className="record">
                    <h3>Observed record {r.number}</h3>
                    <pre aria-label={"Sanitized log " + r.number}>
                      {r.sanitized_log}
                    </pre>
                    <h4>Normalized event</h4>
                    <p className="muted">
                      The parser assigns a typed timestamp and event fields to
                      this same source record.
                    </p>
                    <dl className="normalized-grid">
                      {Object.entries(r.normalized).map(([key, value]) => (
                        <div key={key}>
                          <dt>{key.replaceAll("_", " ")}</dt>
                          <dd>{String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </article>
                ))}
                <details>
                  <summary>Provenance and original-file hashes</summary>
                  <p>
                    Run {exercise.result.run_id}. Originals remain private;
                    these hashes identify the captured bytes before
                    sanitization.
                  </p>
                  <dl>
                    {Object.entries(exercise.result.hashes).map(
                      ([name, hash]) => (
                        <div key={name}>
                          <dt>{name}</dt>
                          <dd className="hash">{hash}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                </details>
              </section>
              <section className="analysis-section">
                <p className="eyebrow">02 / From events to measurements</p>
                <h2>Understand the features.</h2>
                {exercise.result.observations.map((o, i) => (
                  <div key={i}>
                    <h3>
                      Observation {i + 1} · {o.event_ids.length} linked records
                    </h3>
                    <p>Derived from displayed records: {exercise.result.records.filter(r => o.event_ids.includes(r.event_id)).map(r => r.number).join(", ")}.</p>
                    <dl className="feature-dictionary">
                      {Object.entries(o.features).map(([key, value]) => (
                        <div key={key}>
                          <dt>
                            {key} = {String(value)}
                          </dt>
                          <dd>
                            {l.features[key] ||
                              "Observable feature derived by the frozen pipeline."}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                ))}
              </section>
              <section className="analysis-section">
                <p className="eyebrow">03 / Independent judgments</p>
                <h2>Compare truth with prediction.</h2>
                <div className="notice">
                  <strong>
                    Trusted expected label: {exercise.result.expected_label}.
                  </strong>
                  <p>
                    {exercise.result.ground_truth_reason}. This label was
                    assigned before detector processing.
                  </p>
                </div>
                {exercise.result.observations.map((o, i) => (
                  <p key={i} className="comparison">
                    Rule: <strong>{o.rule.label}</strong> · ML:{" "}
                    <strong>{o.ml.label}</strong>.{" "}
                    {o.rule.label !== o.ml.label
                      ? "The detectors disagree. "
                      : ""}
                    {o.rule.label !== exercise.result.expected_label ||
                    o.ml.label !== exercise.result.expected_label
                      ? "At least one detector differs from ground truth. Inspect the features and limitations; this result has not been hidden or relabeled."
                      : "Both predictions match the controlled label for this observation. This does not establish general accuracy."}
                  </p>
                ))}
                <p>{l.limitations}</p>
                <div className="legacy">
                  {details.map((d) => (
                    <Observation
                      key={d.detection_id}
                      detail={d}
                      baseUrl={base}
                      showRag={false}
                    />
                  ))}
                </div>
                <a
                  className="text-link"
                  href="#ask-ai"
                  onClick={(e) => {
                    e.preventDefault();
                    document.getElementById("ask-ai")?.scrollIntoView();
                  }}
                >
                  ML result → Why? → Ask AI ↓
                </a>
              </section>
              <section className="analysis-section" id="ask-ai">
                <p className="eyebrow">04 / Learn from the result</p>
                <h2>Ask AI about this evidence.</h2>
                <AskAI id={id} />
                <h3>Defensive lesson</h3>
                <p>{l.mitigation}</p>
                <a className="button" href={"#/exercises/" + id + "/quiz"}>
                  Continue to knowledge check →
                </a>
              </section>
            </>
          )}
          {view === "quiz" && <Quiz exercise={exercise} lesson={l} />}
          {view === "complete" && (
            <Completion exercise={exercise} lessons={lessons} />
          )}
        </>
      )}
    </>
  );
}
