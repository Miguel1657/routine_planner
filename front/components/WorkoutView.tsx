/* eslint-disable @next/next/no-img-element -- exercise GIFs are animated and remote */
import type { ExerciseCard, GenerateResponse } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-soft px-1 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-muted">{label}</dt>
      <dd className="text-base font-semibold">{value}</dd>
    </div>
  );
}

function ExerciseTile({ exercise, index }: { exercise: ExerciseCard; index: number }) {
  const { t } = useI18n();
  return (
    <li className="flex flex-col overflow-hidden rounded-2xl border border-line bg-white transition hover:-translate-y-1 hover:shadow-lg">
      <div className="aspect-square bg-soft">
        {exercise.gif_url && (
          <img
            src={exercise.gif_url}
            alt={t("result.demo", { name: exercise.name })}
            loading="lazy"
            className="size-full object-cover"
          />
        )}
      </div>
      <div className="flex flex-1 flex-col p-5">
        <span className="text-xs font-semibold uppercase tracking-[0.15em] text-coral">
          {exercise.target_muscle}
        </span>
        <h3 className="mt-1 text-lg font-semibold capitalize leading-snug">
          {index + 1}. {exercise.name}
        </h3>
        <p className="mt-1 text-sm capitalize text-muted">{exercise.equipment}</p>
        <dl className="mt-auto grid grid-cols-3 gap-2 pt-5 text-center">
          <Stat label={t("result.sets")} value={String(exercise.sets)} />
          <Stat label={t("result.reps")} value={exercise.reps} />
          <Stat label={t("result.rest")} value={`${exercise.rest_seconds}s`} />
        </dl>
      </div>
    </li>
  );
}

export default function WorkoutView({
  result,
  onRestart,
}: {
  result: GenerateResponse;
  onRestart: () => void;
}) {
  const { t } = useI18n();
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-16">
      <header className="mb-12 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-coral">
          {t("result.kicker")}
        </p>
        <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          {result.name}
        </h1>
        <p className="mt-3 text-muted">
          {t(result.days.length === 1 ? "result.days.one" : "result.days.other", {
            n: result.days.length,
          })}
        </p>
      </header>

      <div className="space-y-14">
        {result.days.map((day) => (
          <section key={day.day} aria-labelledby={`day-${day.day}`}>
            <h2
              id={`day-${day.day}`}
              className="mb-6 flex flex-wrap items-baseline gap-x-3 text-2xl font-semibold"
            >
              <span className="text-coral">{t("result.day", { n: day.day })}</span>
              <span>{day.name}</span>
            </h2>
            <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {day.exercises.map((exercise, i) => (
                <ExerciseTile
                  key={`${exercise.exercise_id}-${i}`}
                  exercise={exercise}
                  index={i}
                />
              ))}
            </ul>
          </section>
        ))}
      </div>

      <div className="mt-16 text-center">
        <button
          type="button"
          onClick={onRestart}
          className="rounded-full bg-ink px-10 py-4 text-sm font-semibold uppercase tracking-widest text-white transition hover:-translate-y-0.5 hover:bg-coral"
        >
          {t("result.again")}
        </button>
      </div>
    </main>
  );
}
