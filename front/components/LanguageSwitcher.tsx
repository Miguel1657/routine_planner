"use client";

import { LANGS, useI18n } from "@/lib/i18n";

export default function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();
  return (
    <div
      role="group"
      aria-label={t("lang.label")}
      className="fixed right-4 top-4 z-10 flex overflow-hidden rounded-full border border-line bg-white text-xs font-semibold uppercase tracking-widest"
    >
      {LANGS.map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code)}
          aria-pressed={lang === code}
          className={`px-3 py-1.5 transition focus-visible:outline-2 focus-visible:outline-coral ${
            lang === code ? "bg-ink text-white" : "text-muted hover:text-ink"
          }`}
        >
          {code}
        </button>
      ))}
    </div>
  );
}
