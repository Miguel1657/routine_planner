import type { MessageKey } from "./i18n";

export type Option<T extends string | number> = {
  value: T;
  /** i18n key for the visible label. */
  label: MessageKey;
  hint?: MessageKey;
  /** Interpolation variables for `label` (e.g. { n: 45 } for "{n} min"). */
  vars?: Record<string, string | number>;
};

export const GOALS: Option<string>[] = [
  { value: "strength", label: "goal.strength", hint: "goal.strength.hint" },
  { value: "hypertrophy", label: "goal.hypertrophy", hint: "goal.hypertrophy.hint" },
  { value: "power", label: "goal.power", hint: "goal.power.hint" },
  { value: "endurance", label: "goal.endurance", hint: "goal.endurance.hint" },
  {
    value: "general_fitness",
    label: "goal.general_fitness",
    hint: "goal.general_fitness.hint",
  },
];

export const LEVELS: Option<string>[] = [
  { value: "beginner", label: "level.beginner", hint: "level.beginner.hint" },
  { value: "intermediate", label: "level.intermediate", hint: "level.intermediate.hint" },
  { value: "advanced", label: "level.advanced", hint: "level.advanced.hint" },
];

export const DAYS: Option<number>[] = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
  value: n,
  label: "number",
  vars: { n },
}));

export const DURATIONS: Option<number>[] = [30, 45, 60, 75, 90].map((n) => ({
  value: n,
  label: "duration.min",
  vars: { n },
}));

export const EQUIPMENT: Option<string>[] = [
  { value: "full_gym", label: "equip.full_gym", hint: "equip.full_gym.hint" },
  { value: "home", label: "equip.home", hint: "equip.home.hint" },
  { value: "dumbbells", label: "equip.dumbbells", hint: "equip.dumbbells.hint" },
  { value: "bodyweight", label: "equip.bodyweight", hint: "equip.bodyweight.hint" },
];
