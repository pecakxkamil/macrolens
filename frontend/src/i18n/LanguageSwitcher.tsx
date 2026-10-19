import { useSyncExternalStore } from "react";
import { getLanguage, setLanguage, subscribeLanguage } from "./language";
export function LanguageSwitcher() {
  const language = useSyncExternalStore(subscribeLanguage, getLanguage);
  return <div className="language-switcher" role="group" aria-label={language === "pl" ? "J\u0119zyk interfejsu".normalize("NFC") : "Interface language"}>
    <button type="button" lang="en" aria-label="English" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>EN</button>
    <button type="button" lang="pl" aria-label="Polski" aria-pressed={language === "pl"} onClick={() => setLanguage("pl")}>PL</button>
  </div>;
}
