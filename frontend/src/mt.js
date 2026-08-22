// On-demand machine translation of database content (listings, descriptions,
// reviews). Results live in memory only; nothing is persisted server-side.
const cache = new Map();

async function fetchOne(text, lang) {
  const url =
    "/mt/translate_a/single?client=gtx&sl=auto&tl=" +
    encodeURIComponent(lang) +
    "&dt=t&q=" +
    encodeURIComponent(text);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`translation failed (${res.status})`);
  const data = await res.json();
  return (Array.isArray(data) && data[0] ? data[0] : [])
    .map((part) => (Array.isArray(part) ? part[0] : ""))
    .join("");
}

export async function translateMany(texts, lang) {
  const unique = [...new Set(texts.filter((text) => text && text.trim()))];
  const result = {};
  const pending = [];
  for (const text of unique) {
    const key = `${lang}:${text}`;
    if (cache.has(key)) result[text] = cache.get(key);
    else pending.push(text);
  }
  await Promise.all(
    pending.map(async (text) => {
      try {
        const out = await fetchOne(text, lang);
        if (out) {
          cache.set(`${lang}:${text}`, out);
          result[text] = out;
        }
      } catch {
        // Caller falls back to the original string when a translation fails.
      }
    }),
  );
  return result;
}
