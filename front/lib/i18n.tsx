"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";

export type Lang = "es" | "en";
export const LANGS: Lang[] = ["es", "en"];
const STORAGE_KEY = "lang";

const es = {
  "meta.title": "Rutinas personalizadas",
  "intro.kicker": "Tu rutina, a tu medida",
  "intro.title": "Transforma tu cuerpo, transforma tu vida",
  "intro.subtitle":
    "Responde cinco preguntas y recibe una rutina de entrenamiento personalizada.",
  "intro.start": "Iniciar",
  "q.progress": "Pregunta {n} de {total}",
  "q.back": "← Atrás",
  "q.goal": "¿Qué quieres entrenar?",
  "q.level": "¿Cuál es tu nivel?",
  "q.days": "¿Cuántos días por semana?",
  "q.duration": "¿Cuánto dura cada sesión?",
  "q.equipment": "¿Con qué equipo cuentas?",
  "goal.strength": "Fuerza",
  "goal.strength.hint": "Levantar más pesado",
  "goal.hypertrophy": "Hipertrofia",
  "goal.hypertrophy.hint": "Ganar masa muscular",
  "goal.power": "Potencia",
  "goal.power.hint": "Explosividad y velocidad",
  "goal.endurance": "Resistencia",
  "goal.endurance.hint": "Aguantar más tiempo",
  "goal.general_fitness": "Fitness general",
  "goal.general_fitness.hint": "Estar en forma",
  "level.beginner": "Básico",
  "level.beginner.hint": "Estoy empezando",
  "level.intermediate": "Intermedio",
  "level.intermediate.hint": "Entreno con regularidad",
  "level.advanced": "Avanzado",
  "level.advanced.hint": "Años de experiencia",
  "equip.full_gym": "Gimnasio completo",
  "equip.full_gym.hint": "Barras, poleas y máquinas",
  "equip.home": "Casa",
  "equip.home.hint": "Mancuernas, bandas y kettlebell",
  "equip.dumbbells": "Mancuernas",
  "equip.dumbbells.hint": "Solo mancuernas",
  "equip.bodyweight": "Peso corporal",
  "equip.bodyweight.hint": "Sin equipo",
  "number": "{n}",
  "duration.min": "{n} min",
  "loading.aria": "Generando rutina",
  "loading.title": "Armando tu rutina…",
  "loading.hint": "Esto puede tardar hasta un minuto.",
  "error.title": "No pudimos generar tu rutina",
  "error.connect": "No pude conectar con el servidor. ¿Está corriendo la API?",
  "error.unexpected": "Ocurrió un error inesperado.",
  "error.server": "El servidor respondió {status}",
  "error.retry": "Reintentar",
  "error.restart": "Empezar de nuevo",
  "result.kicker": "Tu rutina",
  "result.days.one": "{n} día por semana",
  "result.days.other": "{n} días por semana",
  "result.day": "Día {n}",
  "result.sets": "Series",
  "result.reps": "Reps",
  "result.rest": "Descanso",
  "result.demo": "Demostración de {name}",
  "result.again": "Crear otra rutina",
  "lang.label": "Idioma",
} as const;

export type MessageKey = keyof typeof es;

const en: Record<MessageKey, string> = {
  "meta.title": "Personalized workouts",
  "intro.kicker": "Your workout, tailored to you",
  "intro.title": "Transform your body, transform your life",
  "intro.subtitle":
    "Answer five questions and get a personalized training routine.",
  "intro.start": "Start",
  "q.progress": "Question {n} of {total}",
  "q.back": "← Back",
  "q.goal": "What do you want to train for?",
  "q.level": "What is your level?",
  "q.days": "How many days per week?",
  "q.duration": "How long is each session?",
  "q.equipment": "What equipment do you have?",
  "goal.strength": "Strength",
  "goal.strength.hint": "Lift heavier",
  "goal.hypertrophy": "Hypertrophy",
  "goal.hypertrophy.hint": "Build muscle mass",
  "goal.power": "Power",
  "goal.power.hint": "Explosiveness and speed",
  "goal.endurance": "Endurance",
  "goal.endurance.hint": "Go longer",
  "goal.general_fitness": "General fitness",
  "goal.general_fitness.hint": "Stay in shape",
  "level.beginner": "Beginner",
  "level.beginner.hint": "I am just starting out",
  "level.intermediate": "Intermediate",
  "level.intermediate.hint": "I train regularly",
  "level.advanced": "Advanced",
  "level.advanced.hint": "Years of experience",
  "equip.full_gym": "Full gym",
  "equip.full_gym.hint": "Barbells, cables and machines",
  "equip.home": "Home",
  "equip.home.hint": "Dumbbells, bands and kettlebell",
  "equip.dumbbells": "Dumbbells",
  "equip.dumbbells.hint": "Dumbbells only",
  "equip.bodyweight": "Bodyweight",
  "equip.bodyweight.hint": "No equipment",
  "number": "{n}",
  "duration.min": "{n} min",
  "loading.aria": "Generating workout",
  "loading.title": "Building your workout…",
  "loading.hint": "This can take up to a minute.",
  "error.title": "We could not generate your workout",
  "error.connect": "Could not reach the server. Is the API running?",
  "error.unexpected": "An unexpected error occurred.",
  "error.server": "The server responded {status}",
  "error.retry": "Retry",
  "error.restart": "Start over",
  "result.kicker": "Your workout",
  "result.days.one": "{n} day per week",
  "result.days.other": "{n} days per week",
  "result.day": "Day {n}",
  "result.sets": "Sets",
  "result.reps": "Reps",
  "result.rest": "Rest",
  "result.demo": "Demonstration of {name}",
  "result.again": "Create another workout",
  "lang.label": "Language",
};

const MESSAGES: Record<Lang, Record<MessageKey, string>> = { es, en };

type Vars = Record<string, string | number>;
export type Translate = (key: MessageKey, vars?: Vars) => string;

type Ctx = { lang: Lang; setLang: (lang: Lang) => void; t: Translate };

const LangContext = createContext<Ctx | null>(null);

const listeners = new Set<() => void>();

// In-memory fallback so the switcher still works when localStorage is blocked.
let memoryLang: Lang | null = null;

function readLang(): Lang {
  if (memoryLang) return memoryLang;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "es" || saved === "en") return saved;
  } catch {
    // localStorage unavailable (private mode, blocked storage): fall through.
  }
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "es";
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

// The server and the hydration pass render "es"; React then re-renders with the
// saved/browser language without a hydration mismatch.
const getServerSnapshot = (): Lang => "es";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const lang = useSyncExternalStore(subscribe, readLang, getServerSnapshot);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = MESSAGES[lang]["meta.title"];
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    memoryLang = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
    listeners.forEach((l) => l());
  }, []);

  const value = useMemo<Ctx>(() => {
    const t: Translate = (key, vars) => {
      let text = MESSAGES[lang][key];
      if (vars) {
        for (const [name, v] of Object.entries(vars)) {
          text = text.replaceAll(`{${name}}`, String(v));
        }
      }
      return text;
    };
    return { lang, setLang, t };
  }, [lang, setLang]);

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useI18n must be used inside <LanguageProvider>");
  return ctx;
}
