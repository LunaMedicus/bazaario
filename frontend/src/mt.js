// On-demand machine translation of database content (listings, descriptions,
// reviews). Results live in memory only; nothing is persisted server-side.
//
// Two free, keyless providers are tried in order for every lookup:
//   1. Google gtx (best quality) - rate limits aggressively per IP (HTTP 429).
//   2. MyMemory   - lower quality but generous limits, CORS-enabled.
// Failures fall through automatically; the caller shows an honest error only
// when both providers fail.
const cache = new Map();

async function fromGoogle(text, targetLang, sourceLang = "auto") {
  const query =
    "client=gtx&sl=" +
    encodeURIComponent(sourceLang) +
    "&tl=" +
    encodeURIComponent(targetLang) +
    "&dt=t&q=" +
    encodeURIComponent(text);
  const bases = ["https://translate.googleapis.com", "/mt"];
  let lastError;
  for (const base of bases) {
    try {
      const response = await fetch(`${base}/translate_a/single?${query}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("json")) throw new Error("non-json response");
      const data = await response.json();
      const out = (Array.isArray(data) && data[0] ? data[0] : [])
        .map((part) => (Array.isArray(part) ? part[0] : ""))
        .join("")
        .trim();
      if (!out) throw new Error("empty translation");
      return out;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

async function fromMyMemory(text, targetLang, sourceLang = "en") {
  const query =
    "q=" +
    encodeURIComponent(text) +
    "&langpair=" +
    encodeURIComponent(sourceLang) +
    "|" +
    encodeURIComponent(targetLang);
  const response = await fetch(
    `https://api.mymemory.translated.net/get?${query}`,
  );
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  const out = String(data?.responseData?.translatedText || "").trim();
  // MyMemory signals problems by returning advice text instead of a payload.
  if (
    !out ||
    /MYMEMORY WARNING|QUERY LENGTH LIMIT|INVALID/i.test(out)
  ) {
    throw new Error("mymemory unavailable");
  }
  return out;
}

async function fetchOne(text, lang) {
  if (lang === "en") return text;
  try {
    return await fromGoogle(text, lang, "en");
  } catch {
    return fromMyMemory(text, lang, "en");
  }
}

export async function translateSearchQuery(text, sourceLang) {
  const clean = String(text || "").trim();
  if (!clean || sourceLang === "en") return clean;

  const cacheKey = `search:${sourceLang}:en:${clean.toLocaleLowerCase()}`;
  const cached = cache.get(cacheKey);
  if (cached) return cached;

  let translated;
  try {
    translated = await fromGoogle(clean, "en", sourceLang);
  } catch {
    translated = await fromMyMemory(clean, "en", sourceLang);
  }
  cache.set(cacheKey, translated);
  return translated;
}

export async function translateMany(texts, lang) {
  if (lang === "en") {
    return Object.fromEntries(texts.filter(Boolean).map((text) => [text, text]));
  }
  const unique = [...new Set(texts.filter((text) => text && text.trim()))];
  const result = {};
  const pending = [];
  for (const text of unique) {
    const cached = cache.get(`${lang}:${text}`);
    if (cached) result[text] = cached;
    else pending.push(text);
  }
  if (pending.length === 0) return result;

  // Light concurrency cap keeps the free endpoints happy.
  const queue = [...pending];
  const workers = Array.from({ length: Math.min(2, queue.length) }, async () => {
    while (queue.length) {
      const text = queue.shift();
      try {
        const out = await fetchOne(text, lang);
        cache.set(`${lang}:${text}`, out);
        result[text] = out;
      } catch {
        // Leave this text out; the caller handles total failure.
      }
    }
  });
  await Promise.all(workers);

  if (pending.length > 0 && Object.keys(result).length === 0) {
    throw new Error("translation service unreachable");
  }
  return result;
}
