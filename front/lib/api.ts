export type Preferences = {
  goal: string;
  level: string;
  days_per_week: number;
  session_duration_minutes: number;
  equipment: string[];
  language: "es" | "en";
};

export type ExerciseCard = {
  exercise_id: number;
  name: string;
  body_part: string;
  target_muscle: string;
  equipment: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  image_url: string;
  gif_url: string;
};

export type DayCard = { day: number; name: string; exercises: ExerciseCard[] };

export type GenerateResponse = {
  ok: boolean;
  name: string | null;
  days: DayCard[];
  model: string;
  attempts: number;
  candidates: number;
  errors: string[];
};

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`HTTP ${status}`);
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function generateWorkout(
  preferences: Preferences,
  signal?: AbortSignal,
): Promise<GenerateResponse> {
  const response = await fetch(`${API_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences),
    signal,
  });
  if (!response.ok) {
    throw new ApiError(response.status);
  }
  return response.json();
}
