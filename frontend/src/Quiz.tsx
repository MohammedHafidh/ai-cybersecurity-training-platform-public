import { useState } from "react";
import { api, navigate, type Exercise, type Lesson } from "./training";

type Grade = {
  score: number;
  total: number;
  passed: boolean;
  feedback: { correct: boolean; answer: number; explanation: string }[];
};
export function Quiz({
  exercise,
  lesson,
}: {
  exercise: Exercise;
  lesson: Lesson;
}) {
  const [answers, setAnswers] = useState<number[]>([-1, -1, -1, -1]);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    setBusy(true);
    setError("");
    try {
      setGrade(
        await api<Grade>(
          "/training/exercises/" + exercise.id + "/quiz-attempts",
          { method: "POST", body: JSON.stringify({ answers }) },
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function complete() {
    setBusy(true);
    setError("");
    try {
      await api("/training/exercises/" + exercise.id + "/complete", {
        method: "POST",
        body: "{}",
      });
      navigate("/exercises/" + exercise.id + "/complete");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="quiz">
      <p className="eyebrow">Test understanding, not memorization</p>
      <h2>Knowledge check</h2>
      <p>
        Four curated questions. Three correct answers pass. Grading is
        deterministic; the LLM does not grade your work.
      </p>
      {exercise.quiz_attempts?.length ? (
        <p className="muted">
          Previous attempts: {exercise.quiz_attempts.length}. Your answers,
          score and attempt time are saved locally in the platform database.
        </p>
      ) : null}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {lesson.questions.map((q, i) => (
          <fieldset key={q.id} disabled={busy || !!grade}>
            <legend>
              <span className="eyebrow">Question {i + 1} / 4</span>
              {q.prompt}
            </legend>
            {q.options.map((option, j) => (
              <label className="quiz-option" key={j}>
                <input
                  type="radio"
                  name={q.id}
                  checked={answers[i] === j}
                  onChange={() =>
                    setAnswers((a) => a.map((x, k) => (k === i ? j : x)))
                  }
                  required
                />
                {option}
              </label>
            ))}
            {grade && (
              <div className="notice">
                <strong>
                  {grade.feedback[i].correct
                    ? "Correct"
                    : "Review this concept"}
                  .
                </strong>{" "}
                Correct answer: {q.options[grade.feedback[i].answer]}.{" "}
                {grade.feedback[i].explanation}
              </div>
            )}
          </fieldset>
        ))}
        {!grade && (
          <button className="button" disabled={busy || answers.includes(-1)}>
            Submit knowledge check
          </button>
        )}
      </form>
      {error && (
        <p role="alert" className="notice">
          {error}
        </p>
      )}
      {grade && (
        <section className="quiz-result" aria-live="polite">
          <h3>Your score: {grade.score}/4</h3>
          <p>
            {grade.passed
              ? "Passed. You can mark this scenario complete."
              : "Not passed yet. Review the explanations and try again. Your evidence and detector results are unchanged."}
          </p>
          <div className="actions">
            {grade.passed && (
              <button
                className="button"
                disabled={busy}
                onClick={() => void complete()}
              >
                Mark Scenario Complete
              </button>
            )}
            <button
              onClick={() => {
                setGrade(null);
                setAnswers([-1, -1, -1, -1]);
                window.scrollTo(0, 0);
              }}
            >
              Retry Quiz
            </button>
            <a href={"#/exercises/" + exercise.id + "/analysis"}>
              Review Evidence
            </a>
          </div>
        </section>
      )}
    </section>
  );
}

export function Completion({
  exercise,
  lessons,
}: {
  exercise: Exercise;
  lessons: Lesson[];
}) {
  const next =
    lessons[
      (lessons.findIndex((l) => l.id === exercise.scenario) + 1) %
        lessons.length
    ];
  const best = Math.max(
    0,
    ...(exercise.quiz_attempts || []).map((a) => a.score),
  );
  return (
    <section className="completion">
      <p className="eyebrow">
        {exercise.mode === "live"
          ? "Live controlled learning"
          : "Sample / Demonstration learning"}
      </p>
      <h2>
        {exercise.completed
          ? "Scenario Complete"
          : "Complete the knowledge check first."}
      </h2>
      <p>
        {exercise.completed
          ? "You traced activity into evidence, compared independent detectors and tested your understanding. Keep the limitations in mind."
          : "A score of at least 3/4 is required before marking the scenario complete."}
      </p>
      <p className="completion-score">
        Best quiz score <strong>{best}/4</strong>
      </p>
      <div className="actions">
        <a className="button" href={"#/exercises/" + exercise.id + "/analysis"}>
          Review Evidence
        </a>
        <a href={"#/exercises/" + exercise.id + "/analysis?focus=ai"}>
          Review AI Explanation
        </a>
        <a href={"#/exercises/" + exercise.id + "/quiz"}>Retry Quiz</a>
        <a href="#/">Return Home</a>
        {exercise.completed && (
          <a href={"#/scenarios/" + next.id}>Continue to {next.title} →</a>
        )}
      </div>
    </section>
  );
}
