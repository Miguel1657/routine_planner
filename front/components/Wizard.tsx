"use client";

import { useRef, useState } from "react";
import {
  DAYS,
  DURATIONS,
  EQUIPMENT,
  GOALS,
  LEVELS,
  type Option,
} from "@/lib/options";
import { useI18n, type MessageKey } from "@/lib/i18n";
import {
  ApiError,
  generateWorkout,
  type GenerateResponse,
  type Preferences,
} from "@/lib/api";
import WorkoutView from "./WorkoutView";

type Answers = {
  goal?: string;
  level?: string;
  days?: number;
  duration?: number;
  equipment?: string;
};

type Step = {
  key: keyof Answers;
  title: MessageKey;
  options: Option<string | number>[];
  compact?: boolean;
};

const STEPS: Step[] = [
  { key: "goal", title: "q.goal", options: GOALS },
  { key: "level", title: "q.level", options: LEVELS },
  { key: "days", title: "q.days", options: DAYS, compact: true },
  { key: "duration", title: "q.duration", options: DURATIONS, compact: true },
  { key: "equipment", title: "q.equipment", options: EQUIPMENT },
];

type Phase = "intro" | "questions" | "loading" | "result" | "error";

export default function Wizard() {
  const { t, lang } = useI18n();
  const [phase, setPhase] = useState<Phase>("intro");
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string>("");
  const controller = useRef<AbortController | null>(null);

  function reset() {
    controller.current?.abort();
    setAnswers({});
    setStepIndex(0);
    setResult(null);
    setError("");
    setPhase("intro");
  }

  async function submit(final: Answers) {
    const preferences: Preferences = {
      goal: final.goal!,
      level: final.level!,
      days_per_week: final.days!,
      session_duration_minutes: final.duration!,
      equipment: [final.equipment!],
      language: lang,
    };
    controller.current?.abort();
    controller.current = new AbortController();
    setPhase("loading");
    try {
      const response = await generateWorkout(preferences, controller.current.signal);
      setResult(response);
      setPhase("result");
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(
        e instanceof TypeError
          ? t("error.connect")
          : e instanceof ApiError
            ? t("error.server", { status: e.status })
            : t("error.unexpected"),
      );
      setPhase("error");
    }
  }

  function choose(step: Step, value: string | number) {
    const next = { ...answers, [step.key]: value };
    setAnswers(next);
    if (stepIndex < STEPS.length - 1) setStepIndex(stepIndex + 1);
    else void submit(next);
  }

  if (phase === "intro") {
    return (
      <Centered>
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-coral">
          {t("intro.kicker")}
        </p>
        <h1 className="max-w-2xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
          {t("intro.title")}
        </h1>
        <p className="mt-5 max-w-md text-balance text-lg text-muted">
          {t("intro.subtitle")}
        </p>
        <button
          type="button"
          onClick={() => setPhase("questions")}
          className="mt-10 rounded-full bg-ink px-12 py-4 text-sm font-semibold uppercase tracking-widest text-white transition hover:-translate-y-0.5 hover:bg-coral focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-coral"
        >
          {t("intro.start")}
        </button>
      </Centered>
    );
  }

  if (phase === "questions") {
    const step = STEPS[stepIndex];
    const selected = answers[step.key];
    return (
      <Centered>
        <div
          className="mb-10 h-1 w-full max-w-xs overflow-hidden rounded-full bg-soft"
          aria-hidden
        >
          <div
            className="h-full bg-coral transition-all duration-500"
            style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
          />
        </div>
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-coral">
          {t("q.progress", { n: stepIndex + 1, total: STEPS.length })}
        </p>
        <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
          {t(step.title)}
        </h2>
        <div
          role="radiogroup"
          aria-label={t(step.title)}
          className={
            step.compact
              ? "mt-10 flex max-w-xl flex-wrap justify-center gap-3"
              : "mt-10 grid w-full max-w-xl gap-3"
          }
        >
          {step.options.map((option) => {
            const active = selected === option.value;
            return (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => choose(step, option.value)}
                className={`rounded-2xl border px-6 py-4 text-left transition hover:-translate-y-0.5 hover:border-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral ${
                  step.compact ? "min-w-20 text-center" : ""
                } ${active ? "border-ink bg-ink text-white" : "border-line bg-white"}`}
              >
                <span className="block text-lg font-semibold">{t(option.label, option.vars)}</span>
                {option.hint && (
                  <span
                    className={`block text-sm ${active ? "text-white/70" : "text-muted"}`}
                  >
                    {t(option.hint)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => (stepIndex === 0 ? reset() : setStepIndex(stepIndex - 1))}
          className="mt-10 text-sm font-medium text-muted underline-offset-4 hover:text-ink hover:underline"
        >
          {t("q.back")}
        </button>
      </Centered>
    );
  }

  if (phase === "loading") {
    return (
      <Centered>
        <div
          className="size-12 animate-spin rounded-full border-4 border-soft border-t-coral"
          role="status"
          aria-label={t("loading.aria")}
        />
        <h2 className="mt-8 text-2xl font-semibold">{t("loading.title")}</h2>
        <p className="mt-2 max-w-sm text-muted" aria-live="polite">
          {t("loading.hint")}
        </p>
      </Centered>
    );
  }

  if (phase === "error" || (phase === "result" && result && !result.ok)) {
    const messages = phase === "error" ? [error] : (result?.errors ?? []);
    return (
      <Centered>
        <h2 className="text-3xl font-semibold">{t("error.title")}</h2>
        <ul className="mt-4 max-w-md space-y-1 text-muted">
          {messages.slice(0, 3).map((m, i) => (
            <li key={i}>{m}</li>
          ))}
        </ul>
        <div className="mt-8 flex gap-3">
          <button
            type="button"
            onClick={() => void submit(answers)}
            className="rounded-full bg-ink px-8 py-3 text-sm font-semibold uppercase tracking-widest text-white transition hover:bg-coral"
          >
            {t("error.retry")}
          </button>
          <button
            type="button"
            onClick={reset}
            className="rounded-full border border-line px-8 py-3 text-sm font-semibold uppercase tracking-widest transition hover:border-ink"
          >
            {t("error.restart")}
          </button>
        </div>
      </Centered>
    );
  }

  return result ? <WorkoutView result={result} onRestart={reset} /> : null;
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-4xl flex-col items-center justify-center px-4 py-16 text-center">
      {children}
    </main>
  );
}
