import { useState } from "react";
import { api } from "./training";

type Answer = {
  status: string;
  mode: string;
  text: string;
  model?: string;
  scope_notice?: string;
  sources: {
    chunk_id: string;
    title: string;
    text: string;
    references: { title: string; url: string }[];
  }[];
};
export function AskAI({ id }: { id: string }) {
  const [question, setQuestion] = useState(
    "Why did the rule and ML model reach these results?",
  );
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function ask() {
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      const result = await api<Answer>(
        "/training/exercises/" + id + "/question",
        {
          method: "POST",
          body: JSON.stringify({ question }),
          signal: AbortSignal.timeout(65_000),
        },
      );
      if (typeof result.text !== "string" || !Array.isArray(result.sources))
        throw Error("Unexpected explanation response");
      setAnswer(result);
    } catch (e) {
      setError(
        "The local explanation could not be completed. Your detector results are unchanged. Read the evidence preview and defensive lesson, or retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="ask-panel">
      <p>
        Ask a short question about these logs, features, predictions or
        defensive lessons. The frozen detectors decide; local AI helps explain
        the stored result.
      </p>
      <div className="suggestions">
        {[
          "What happened?",
          "Why was this suspicious?",
          "What evidence matters?",
          "How can defenders reduce this risk?",
        ].map((q) => (
          <button
            key={q}
            type="button"
            disabled={busy}
            onClick={() => {
              setQuestion(q);
              setAnswer(null);
            }}
          >
            {q}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask();
        }}
      >
        <label htmlFor="student-question">Ask AI about this evidence…</label>
        <textarea
          id="student-question"
          maxLength={300}
          minLength={3}
          required
          value={question}
          disabled={busy}
          onChange={(e) => {
            setQuestion(e.target.value);
            setAnswer(null);
          }}
        />
        <div className="actions">
          <button
            className="button"
            disabled={busy || question.trim().length < 3}
          >
            {busy ? "Preparing grounded explanation…" : "Ask AI"}
          </button>
          <span className="muted">
            {question.length}/300 · Current exercise only
          </span>
        </div>
      </form>
      {busy && (
        <p role="status">
          Reading current evidence and trusted local knowledge…
        </p>
      )}
      {error && (
        <p role="alert" className="notice">
          {error}
        </p>
      )}
      {answer && (
        <div className="ai-answer" aria-live="polite">
          <p className="eyebrow">
            {answer.status === "grounded"
              ? "Local AI + trusted retrieval"
              : answer.status === "unsupported"
                ? "Outside this lesson"
                : "Safe deterministic fallback — not a live AI answer"}
          </p>
          <p>{answer.text}</p>
          {answer.scope_notice && (
            <p className="muted">{answer.scope_notice}</p>
          )}
          {answer.sources.length > 0 && (
            <>
              <h3>Trusted sources</h3>
              {answer.sources.map((s) => (
                <div key={s.chunk_id} className="citation">
                  <h4>{s.title}</h4>
                  <p>{s.text}</p>
                  {s.references.map((r) => (
                    <a
                      key={r.url}
                      href={r.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {r.title} ↗
                    </a>
                  ))}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
