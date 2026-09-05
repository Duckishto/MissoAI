"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";

import { BeliefStrip } from "@/components/BeliefStrip";
import { type NextQuestion, api } from "@/lib/api";

export default function SessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);
  const [current, setCurrent] = useState<NextQuestion | null>(null);
  const [choice, setChoice] = useState<string>("");
  const [written, setWritten] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const servedAt = useRef<number>(Date.now());

  const load = useCallback(async () => {
    const next = await api.nextQuestion(sessionId);
    setCurrent(next);
    setChoice("");
    setWritten("");
    servedAt.current = Date.now();
  }, [sessionId]);

  useEffect(() => {
    load().catch(() => setNotice("The session could not be loaded."));
  }, [load]);

  async function submit() {
    if (!current?.question) return;
    const result = await api.submit(sessionId, {
      question_id: current.question.id,
      response_text: current.question.options ? choice : written,
      latency_ms: Date.now() - servedAt.current,
    });
    // Phase 0 records without judging, and the interface says exactly that
    // rather than implying a verdict the backend did not give.
    setNotice(
      result.is_correct === null
        ? "Recorded. This build stores your answer and reasoning; it does not mark them yet."
        : result.feedback,
    );
    await load();
  }

  if (!current) {
    return <main className="mx-auto max-w-2xl px-6 py-16 text-sm text-ink-2">Loading.</main>;
  }

  if (current.exhausted || !current.question) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="reading text-2xl">Nothing left to ask</h1>
        <p className="mt-4 max-w-[52ch] text-ink-2">{current.rationale}</p>
      </main>
    );
  }

  const q = current.question;

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <article
        className="border-l-2 pl-6"
        style={{ borderColor: "var(--observed)" }}
      >
        <p className="reading">{q.stem}</p>

        {q.options ? (
          <fieldset className="mt-6 space-y-1">
            <legend className="sr-only">Answer choices</legend>
            {q.options.map((option) => (
              <label
                key={option.id}
                className="flex cursor-pointer items-start gap-3 rounded-sm px-2 py-2 hover:bg-paper-raised"
              >
                <input
                  type="radio"
                  name="answer"
                  value={option.id}
                  checked={choice === option.id}
                  onChange={() => setChoice(option.id)}
                  className="mt-1"
                />
                <span className="text-[0.9375rem]">{option.text}</span>
              </label>
            ))}
          </fieldset>
        ) : (
          <textarea
            value={written}
            onChange={(e) => setWritten(e.target.value)}
            rows={6}
            placeholder="Explain your reasoning, not just the answer."
            className="mt-6 w-full rounded-sm border bg-paper-raised p-3 text-[0.9375rem]"
            style={{ borderColor: "var(--rule)" }}
          />
        )}

        <button
          onClick={submit}
          disabled={!choice && !written.trim()}
          className="mt-6 rounded-sm px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          style={{ background: "var(--observed)" }}
        >
          Submit answer
        </button>
      </article>

      {notice && (
        <p role="status" className="mt-6 max-w-[52ch] text-sm text-ink-2">
          {notice}
        </p>
      )}

      <section className="mt-14 border-t pt-6" style={{ borderColor: "var(--rule)" }}>
        <h2 className="text-sm font-medium">What the system currently believes</h2>
        <p className="mt-1 max-w-[52ch] text-sm text-ink-3">
          An estimate of your understanding, with its uncertainty shown. It describes the
          evidence so far, not your ability.
        </p>
        <div className="mt-3 divide-y" style={{ borderColor: "var(--rule)" }}>
          <BeliefStrip
            concept="Evidence and mastery"
            mean={0.5}
            variance={0.08}
            observations={0}
          />
        </div>
      </section>
    </main>
  );
}
