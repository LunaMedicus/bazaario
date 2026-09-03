import React from "react";
import { LANGS, useLang, useSetLang } from "../i18n";

function LangSwitcher() {
  const lang = useLang();
  const setLang = useSetLang();

  return (
    <select
      className="lang-switcher"
      value={lang}
      onChange={(event) => setLang(event.target.value)}
      aria-label="Language"
    >
      {LANGS.map((entry) => (
        <option key={entry.code} value={entry.code}>
          {entry.label}
        </option>
      ))}
    </select>
  );
}

export default LangSwitcher;
