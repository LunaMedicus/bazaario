import React, { useEffect, useState } from "react";
import clickSound from "./sounds/star-click.mp3";
import { api, clearSession, getSession, saveSession } from "./api";
import { LANGS, LangProvider, getInitialLang, storeLang, useT, useLang, useSetLang, translate } from "./i18n";
import { translateMany, translateSearchQuery } from "./mt";
import { cdnImage } from "./images";
import StarRating from "./components/StarRating";

const CATEGORIES = [
  "Fruit",
  "Vegetables",
  "Grains",
  "Dairy",
  "Honey & bee products",
  "Herbs",
  "Nuts",
  "Tea",
];

const SEASONS = ["Spring", "Summer", "Autumn", "Winter", "All year"];

function useRoute() {
  const [route, setRoute] = useState(window.location.pathname);
  useEffect(() => {
    const handlePopState = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);
  return route;
}

function money(value) {
  return `${Number(value || 0).toFixed(2)} AZN`;
}

function App() {
  const route = useRoute();
  const [lang, setLangState] = useState(getInitialLang);
  const setLang = (next) => {
    setLangState(next);
    storeLang(next);
  };
  const t = (key, params) => translate(lang, key, params);
  const [session, setSession] = useState(getSession);
  const [notice, setNotice] = useState(null);

  const navigate = (to) => {
    window.history.pushState({}, "", to);
    window.dispatchEvent(new PopStateEvent("popstate"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const flash = (message, kind = "success") => {
    setNotice({ message, kind });
    window.setTimeout(() => setNotice(null), 3600);
  };

  useEffect(() => {
    if (!session?.access_token) return undefined;
    let active = true;
    api.me()
      .then(({ user }) => {
        if (!active) return;
        const nextSession = { ...session, user };
        saveSession(nextSession);
        setSession(nextSession);
      })
      .catch(() => {
        if (!active) return;
        clearSession();
        setSession(null);
        flash(t("misc.sessionExpired"), "error");
        navigate("/login");
      });
    return () => { active = false; };
  }, [session?.access_token]);

  const onLogin = (payload) => {
    saveSession(payload);
    setSession(payload);
    flash(t("misc.signedInAs", { name: payload.user.display_name }));
    navigate("/dashboard");
  };

  const onLogout = () => {
    clearSession();
    setSession(null);
    navigate("/");
  };

  let content;
  if (route === "/login") {
    content = <LoginView onLogin={onLogin} onNavigate={navigate} />;
  } else if (route === "/register") {
    content = <RegisterView onNavigate={navigate} onFlash={flash} />;
  } else if (route === "/dashboard") {
    content = session ? (
      <DashboardRouter session={session} onNavigate={navigate} onFlash={flash} />
    ) : (
      <LoginView onLogin={onLogin} onNavigate={navigate} />
    );
  } else if (route.startsWith("/product/")) {
    content = (
      <ProductDetail
        id={route.split("/").pop()}
        onNavigate={navigate}
        onFlash={flash}
      />
    );
  } else if (route === "/favorites") {
    content = <FavoritesView onNavigate={navigate} />;
  } else {
    content = <CatalogView onNavigate={navigate} />;
  }

  return (
    <LangProvider value={{ lang, setLang }}>
      <div className="app-shell">
        <Header session={session} onNavigate={navigate} onLogout={onLogout} />
        {notice && <div className={`toast ${notice.kind}`}>{notice.message}</div>}
        <main>{content}</main>
        <Footer />
      </div>
    </LangProvider>
  );
}

function LangSwitcher() {
  const lang = useLang();
  const setLang = useSetLang();
  return (
    <div className="lang-switcher" role="group" aria-label="Language">
      {LANGS.map((entry) => (
        <button
          key={entry.code}
          className={lang === entry.code ? "active" : ""}
          onClick={() => setLang(entry.code)}
        >
          {entry.label}
        </button>
      ))}
    </div>
  );
}

function Header({ session, onNavigate, onLogout }) {
  return (
    <header className="site-header">
      <button className="wordmark" onClick={() => onNavigate("/")} aria-label="Bazaario home">
        bazaario<span>.</span>
      </button>
      <Nav session={session} onNavigate={onNavigate} />
      <div className="header-actions">
        <LangSwitcher />
        {session ? (
          <>
            <span className={`role-tag ${session.user.role}`}>{session.user.role}</span>
            <SignOutButton onLogout={onLogout} />
          </>
        ) : (
          <>
            <SignInButton onNavigate={onNavigate} />
            <JoinButton onNavigate={onNavigate} />
          </>
        )}
      </div>
    </header>
  );
}

function Nav({ session, onNavigate }) {
  const t = useT();

  return (
    <nav className="main-nav">
      <button onClick={() => onNavigate("/")}>
        {t("nav.catalog")}
      </button>

      <button onClick={() => onNavigate("/favorites")}>
        Favorites
      </button>

      {session && (
        <button onClick={() => onNavigate("/dashboard")}>
          {t("nav.dashboard")}
        </button>
      )}
    </nav>
  );
}

function SignOutButton({ onLogout }) {
  const t = useT();
  return <button className="text-button" onClick={onLogout}>{t("nav.signOut")}</button>;
}

function SignInButton({ onNavigate }) {
  const t = useT();
  return <button className="text-button" onClick={() => onNavigate("/login")}>{t("nav.signIn")}</button>;
}

function JoinButton({ onNavigate }) {
  const t = useT();
  return <button className="button button-small" onClick={() => onNavigate("/register")}>{t("nav.join")}</button>;
}

function Footer() {
  return (
    <footer className="site-footer">
      <span>Bazaario copyright 2026</span>
    </footer>
  );
}

function SectionHeading({ eyebrow, title, detail }) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
      </div>
      {detail && <p className="heading-detail">{detail}</p>}
    </div>
  );
}

function CatalogView({ onNavigate }) {
  const t = useT();
  const lang = useLang();
  const [products, setProducts] = useState([]);
  const [meta, setMeta] = useState({ categories: CATEGORIES, regions: [], seasons: SEASONS });
  const [filters, setFilters] = useState({ q: "", category: "", region: "", season: "" });
  const [resolvedSearch, setResolvedSearch] = useState({ original: "", translated: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.meta().then((data) => setMeta({ categories: data.categories || CATEGORIES, regions: data.regions || [], seasons: data.seasons || SEASONS })).catch(() => {});
  }, []);

  useEffect(() => {
    if (filters.category && !(meta.categories || []).includes(filters.category)) {
      setFilters((current) => ({ ...current, category: "" }));
    }
  }, [meta.categories, filters.category]);

  useEffect(() => {
    let active = true;
    const original = filters.q.trim();
    const timer = window.setTimeout(async () => {
      if (!original) {
        if (active) setResolvedSearch({ original: "", translated: "" });
        return;
      }
      try {
        const translated = await translateSearchQuery(original, lang);
        if (active) setResolvedSearch({ original, translated });
      } catch {
        if (active) setResolvedSearch({ original, translated: original });
      }
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [filters.q, lang]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (resolvedSearch.translated) params.set("q", resolvedSearch.translated);
    if (
      resolvedSearch.original &&
      resolvedSearch.original.toLocaleLowerCase() !==
        resolvedSearch.translated.toLocaleLowerCase()
    ) {
      params.set("q_original", resolvedSearch.original);
    }
    for (const key of ["category", "region", "season"]) {
      if (filters[key]) params.set(key, filters[key]);
    }
    api.products(params)
      .then((data) => {
        if (active) setProducts(data.products || []);
      })
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [resolvedSearch, filters.category, filters.region, filters.season]);

  return (
    <div className="page page-catalog">
      <section className="catalog-intro">
        <h1>{t("catalog.title")}</h1>
      </section>

      <section className="filter-bar" aria-label="Catalog filters">
        <label className="search-field">
          <span className="filter-heading">
            <span>{t("filter.search")}</span>
            <small>{LANGS.map((entry) => entry.label).join(" · ")}</small>
          </span>
          <input
            type="search"
            value={filters.q}
            onChange={(event) => setFilters({ ...filters, q: event.target.value })}
            placeholder={t("filter.searchPlaceholder")}
            autoComplete="off"
          />
        </label>
        <label>
          <span>{t("filter.category")}</span>
          <select value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
            <option value="">{t("filter.allCategories")}</option>
            {meta.categories.map((category) => <option key={category} value={category}>{t(`cat.${category}`, {}, category)}</option>)}
          </select>
        </label>
        <label>
          <span>{t("filter.region")}</span>
          <select value={filters.region} onChange={(event) => setFilters({ ...filters, region: event.target.value })}>
            <option value="">{t("filter.everyRegion")}</option>
            {meta.regions.map((region) => <option key={region} value={region}>{t(`region.${region}`, {}, region)}</option>)}
          </select>
        </label>
        <label>
          <span>{t("filter.season")}</span>
          <select value={filters.season} onChange={(event) => setFilters({ ...filters, season: event.target.value })}>
            <option value="">{t("filter.anySeason")}</option>
            {meta.seasons.map((season) => <option key={season} value={season}>{t(`season.${season}`, {}, season)}</option>)}
          </select>
        </label>
      </section>

      <div className="catalog-meta">
        <span>{loading ? t("catalog.loading") : t("catalog.count", { n: products.length })}</span>
        <span>{t("catalog.categoriesCount", { n: meta.categories.length })}</span>
      </div>
      {error && <InlineError message={error} />}
      {loading ? (
        <div className="empty-state">{t("catalog.loading")}</div>
      ) : products.length ? (
        <div className="product-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} onOpen={() => onNavigate(`/product/${product.id}`)} />
          ))}
        </div>
      ) : (
        <div className="empty-state">{t("catalog.empty")}</div>
      )}
    </div>
  );
}

function ProductCard({ product, onOpen }) {
  const t = useT();
  const lang = useLang();

  const [isFavorite, setIsFavorite] = useState(() => {
    try {
      const favorites = JSON.parse(
        localStorage.getItem("bazaario_favorites") || "[]"
      );
      return favorites.includes(product.id);
    } catch {
      return false;
    }
  });

  

  const toggleFavorite = (event) => {
    event.stopPropagation();

    try {
      const audio = new Audio(clickSound);
      audio.volume = 1;
      audio.play().catch((error) => {
          console.error("Favorite sound error:", error);
      });
      const favorites = JSON.parse(
        localStorage.getItem("bazaario_favorites") || "[]"
      );

      let nextFavorites;

      if (favorites.includes(product.id)) {
        nextFavorites = favorites.filter((id) => id !== product.id);
        setIsFavorite(false);
      } else {
        nextFavorites = [...favorites, product.id];
        setIsFavorite(true);
      }

      localStorage.setItem(
        "bazaario_favorites",
        JSON.stringify(nextFavorites)
      );
    } catch {
      // Ignore localStorage errors
    }
  };

  const shownName = product.name;

  return (
    <article className="product-card">
      <div className="product-image-wrap">
        <button
          className="product-image-button"
          onClick={onOpen}
          aria-label={`View ${shownName}`}
        >
          <img
            src={cdnImage(product.image_url, "card")}
            alt={shownName}
            loading="lazy"
            decoding="async"
            width="480"
            height="320"
          />

          <span className="image-label">
            {t(`cat.${product.category}`, {}, product.category)}
          </span>
        </button>

        <button
          type="button"
          className={`favorite-button ${isFavorite ? "active" : ""}`}
          onClick={toggleFavorite}
          aria-label={
            isFavorite
              ? `Remove ${shownName} from favorites`
              : `Add ${shownName} to favorites`
          }
          aria-pressed={isFavorite}
        >
          {isFavorite ? "♥" : "♡"}
        </button>
      </div>

      <div className="product-card-body">
        <div className="product-card-topline">
          <span>
            {t(`region.${product.region}`, {}, product.region)}
          </span>

          <span>
            {t(`season.${product.season}`, {}, null) ||
              localiseSeasonWindow(product.season, lang)}
          </span>
        </div>

        <button className="product-name" onClick={onOpen}>
          {shownName}
        </button>

        <div className="product-shop">
          {product.shop?.name}
        </div>

        <div className="product-card-bottom">
          <strong>{money(product.price_azn)}</strong>

          <button
            className="add-button"
            onClick={onOpen}
          >
            {t("product.view")}
          </button>
        </div>
      </div>
    </article>
  );
}

function FavoritesView({ onNavigate }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadFavorites = async () => {
    setLoading(true);
    setError("");

    try {
      const savedFavorites = JSON.parse(
        localStorage.getItem("bazaario_favorites") || "[]"
      );

      if (!savedFavorites.length) {
        setProducts([]);
        setLoading(false);
        return;
      }

      const data = await api.products(new URLSearchParams());
      const allProducts = data.products || [];

      const favoriteProducts = allProducts.filter((product) =>
        savedFavorites.includes(product.id)
      );

      setProducts(favoriteProducts);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFavorites();
  }, []);

  const removeFavorite = (productId) => {
    try {
      const favorites = JSON.parse(
        localStorage.getItem("bazaario_favorites") || "[]"
      );

      const nextFavorites = favorites.filter(
        (id) => id !== productId
      );

      localStorage.setItem(
        "bazaario_favorites",
        JSON.stringify(nextFavorites)
      );

      setProducts((current) =>
        current.filter((product) => product.id !== productId)
      );
    } catch {
      // Ignore localStorage errors
    }
  };

  return (
    <div className="page page-catalog">
      <section className="catalog-intro">
        <h1>Favorites</h1>
        <p>
          Your saved products
        </p>
      </section>

      {error && <InlineError message={error} />}

      {loading ? (
        <div className="empty-state">
          Loading favorites...
        </div>
      ) : products.length ? (
        <>
          <div className="catalog-meta">
            <span>
              {products.length}{" "}
              {products.length === 1 ? "favorite" : "favorites"}
            </span>
          </div>

          <div className="product-grid">
            {products.map((product) => (
              <div className="favorite-product-wrapper" key={product.id}>
                <ProductCard
                  product={product}
                  onOpen={() =>
                    onNavigate(`/product/${product.id}`)
                  }
                />

                <button
                  type="button"
                  className="favorite-remove-button"
                  onClick={() => removeFavorite(product.id)}
                >
                  Remove from favorites
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="empty-state favorites-empty">
          <h2>No favorites yet</h2>
          <p>
            Go to the catalog and click ♡ on products you want to save.
          </p>

          <button
            className="button"
            onClick={() => onNavigate("/")}
          >
            Browse products
          </button>
        </div>
      )}
    </div>
  );
}

function useTranslatedContent(lang) {
  const [state, setState] = useState({ lang: null, map: {}, working: false, failed: false });
  const run = async (texts) => {
    setState((current) => ({ ...current, lang, working: true, failed: false }));
    try {
      const clean = texts.filter(Boolean);
      if (clean.length === 0) {
        setState({ lang, map: {}, working: false, failed: false });
        return;
      }
      const result = await translateMany(clean, lang);
      const map = {};
      for (const text of clean) map[text] = result[text] || text;
      setState({ lang, map, working: false, failed: false });
    } catch {
      setState({ lang, map: {}, working: false, failed: true });
    }
  };
  return [state, run];
}

const MONTHS = {
  az: ["Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun", "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"],
  ru: ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"],
};

function localiseSeasonWindow(season, lang) {
  if (!season || (lang !== "az" && lang !== "ru")) return season;
  const months = MONTHS[lang];
  return String(season).replace(/[A-Z][a-z]+/g, (month) => {
    const index = new Date(Date.parse(`${month} 1, 2000`)).getMonth();
    return Number.isNaN(index) ? month : months[index];
  });
}


function TranslateToggle({ translated, working, failed, onTranslate, onShowOriginal }) {
  const t = useT();
  return (
    <span className="translate-wrap">
      <button className="text-button translate-toggle" onClick={translated ? onShowOriginal : onTranslate} disabled={working}>
        {working ? t("translate.working") : translated ? t("translate.original") : t("translate.show")}
      </button>
      {failed && <small className="translate-failed">{t("translate.failed")}</small>}
    </span>
  );
}

function ProductDetail({ id, onNavigate, onFlash }) {
  const t = useT();
  const lang = useLang();
  const [product, setProduct] = useState(null);
  const [error, setError] = useState("");
  const [content, translateContent] = useTranslatedContent(lang);

  const load = () =>
    api
      .product(id)
      .then((data) => setProduct(data.product))
      .catch((err) => setError(err.message));

  useEffect(() => {
    load();
  }, [id]);

  if (error) {
    return (
      <div className="page">
        <InlineError message={error} />
      </div>
    );
  }

  if (!product) {
    return <div className="page empty-state">{t("product.loading")}</div>;
  }

  const translated = content.lang === lang && Boolean(content.map[product.name]);
  const shownName = translated ? content.map[product.name] : product.name;
  const dictSeason = t(`season.${product.season}`, {}, null);
  const shownSeason = dictSeason || localiseSeasonWindow(product.season, lang);
  const shownDescription = translated
    ? content.map[product.description] || product.description
    : product.description;

  return (
    <div className="page product-detail-page">
      <button className="back-link" onClick={() => onNavigate("/")}>
        {t("product.back")}
      </button>

      <section className="product-detail">
        <div className="detail-image-wrap">
          <img
            src={cdnImage(product.image_url, "detail")}
            alt={shownName}
            decoding="async"
            fetchpriority="high"
            width="960"
            height="640"
          />
        </div>

        <div className="detail-copy">
          <p className="eyebrow orange">
            {t(`cat.${product.category}`, {}, product.category)} /{" "}
            {t(`region.${product.region}`, {}, product.region)}
          </p>
          <h1>{shownName}</h1>

          <div className="detail-title-row">
            <p className="detail-description">{shownDescription}</p>
            <TranslateToggle
              translated={translated}
              working={content.working}
              failed={content.lang === lang && content.failed}
              onTranslate={() =>
                translateContent([
                  product.name,
                  product.description,
                  ...(product.reviews || []).map((review) => review.body),
                ])
              }
              onShowOriginal={() => translateContent([])}
            />
          </div>

          <div className="detail-shop">
            <span>{t("product.soldBy")}</span>
            <strong>{product.shop?.name}</strong>
            <small>
              {t(`region.${product.shop?.region}`, {}, product.shop?.region)},
              Azerbaijan
            </small>
          </div>

          <div className="detail-season">
            <span>{t("product.season")}</span>
            <strong>{shownSeason}</strong>
            <span className="stock-note">
              {t("product.inStock", { n: product.stock })}
            </span>
          </div>

          <div className="detail-purchase">
            <strong>{money(product.price_azn)}</strong>
            <span className="muted">{t("product.contactToBuy")}</span>
          </div>

          <ReviewSection
            productId={product.id}
            reviews={product.reviews}
            translations={translated ? content.map : null}
            onDone={() => {
              load();
            }}
          />
        </div>
      </section>

      <section className="seller-contact-section">
        <SellerContact shop={product.shop} />
        <MessageThreadPanel
          productId={product.id}
          heading={t("messages.with", {
            shop: product.shop?.name || t("messages.withFallback"),
          })}
        />
      </section>
    </div>
  );
}

function ReviewSection({ productId, reviews, translations, onDone }) {
  const t = useT();
  const session = getSession();
  const isCustomer = session?.user?.role === "customer";
  const mine =
    isCustomer && session
      ? (reviews || []).find(
          (review) => review.customer === session.user.display_name,
        )
      : null;

  return (
    <div className="review-section">
      <h3>
        {t("reviews.title")} {reviews?.length ? `(${reviews.length})` : ""}
      </h3>
      {!reviews?.length && <p className="muted">{t("reviews.none")}</p>}
      {reviews?.length > 0 && (
        <div className="review-list">
          {reviews.map((review) => (
            <div className="review-line" key={review.id}>
              <b>{"★".repeat(review.rating)}</b>
              <span>
                {(translations && review.body && translations[review.body]) ||
                  review.body ||
                  t("reviews.noComment")}
              </span>
              <small>{review.customer}</small>
            </div>
          ))}
        </div>
      )}
      {isCustomer && (
        <ReviewForm productId={productId} existing={mine} onSaved={onDone} />
      )}
      {!session && <p className="muted">{t("reviews.signInPrompt")}</p>}
    </div>
  );
}

function ReviewForm({ productId, existing, onSaved }) {
  const t = useT();
  const [rating, setRating] = useState(existing?.rating || 5);
  const [body, setBody] = useState(existing?.body || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createReview(productId, { rating, body });
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="inline-form review-form" onSubmit={submit}>
      <div className="rating-field">
        <span>{t("reviews.rating")}</span>
        <StarRating value={rating} onChange={setRating} />
      </div>

      <input
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder={
          existing ? t("reviews.updatePlaceholder") : t("reviews.placeholder")
        }
      />
      <button className="button button-small" disabled={saving}>
        {existing ? t("reviews.update") : t("reviews.publish")}
      </button>
      {error && <InlineError message={error} />}
    </form>
  );
}

function telHref(phone) {
  return `tel:${String(phone).replace(/[^+0-9]/g, "")}`;
}

function SellerContact({ shop }) {
  const t = useT();
  if (!shop?.phone) {
    return (
      <div className="seller-contact">
        <h3>{t("seller.title")}</h3>
        <p className="muted">{t("seller.noPhone")}</p>
      </div>
    );
  }
  return (
    <div className="seller-contact">
      <h3>{t("seller.title")}</h3>
      <p>{t("seller.hubs")}</p>
      <a className="call-button" href={telHref(shop.phone)}>
        {t("seller.call", { phone: shop.phone })}
      </a>
    </div>
  );
}

function MessageThreadPanel({
  productId,
  heading,
  thread,
  viewerRole,
  onBack,
}) {
  const t = useT();
  const session = getSession();
  const [messages, setMessages] = useState(null);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    api
      .productMessages(productId)
      .then((data) => setMessages(data.messages || []))
      .catch((err) => setError(err.message));

  useEffect(() => {
    setMessages(null);
    load();
  }, [productId]);

  const send = async (event) => {
    event.preventDefault();
    if (!session) return;
    const payload =
      thread && session.user.role === "shop"
        ? { body, customer_id: thread.customer_id }
        : { body };
    setSending(true);
    setError("");
    try {
      await api.sendMessage(productId, payload);
      setBody("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="message-panel">
      <div className="section-title-row">
        <h3>{heading}</h3>
        {onBack && (
          <button className="text-button" onClick={onBack}>
            {t("messages.allConversations")}
          </button>
        )}
      </div>

      {!session && <p className="muted">{t("messages.signInPrompt")}</p>}
      {session && error && <InlineError message={error} />}

      {session &&
        (messages === null ? (
          <p className="muted">{t("messages.loading")}</p>
        ) : messages.length === 0 ? (
          <p className="muted">{t("messages.empty")}</p>
        ) : (
          <ul className="message-list">
            {messages.map((message) => (
              <li
                key={message.id}
                className={`message-line ${message.sender_role}`}
              >
                <span className="message-meta">
                  {message.sender_role === "customer"
                    ? message.sender
                    : t("messages.senderShop")}{" "}
                  · {new Date(message.created_at).toLocaleString()}
                </span>
                <p>{message.body}</p>
              </li>
            ))}
          </ul>
        ))}

      {session && viewerRole !== "read-only" && (
        <form className="message-form" onSubmit={send}>
          <input
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder={t("messages.writePlaceholder")}
            maxLength={2000}
            required
          />
          <button className="button button-small" disabled={sending}>
            {sending ? t("messages.sending") : t("messages.send")}
          </button>
        </form>
      )}
    </div>
  );
}

function LoginView({ onLogin, onNavigate }) {
  const t = useT();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      onLogin(await api.login(form));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page auth-page">
      <div className="auth-panel">
        <p className="eyebrow orange">{t("auth.eyebrow")}</p>
        <h1>{t("auth.welcome")}</h1>
        <p className="auth-subcopy">{t("auth.subcopy")}</p>
        <form onSubmit={submit} className="stack-form">
          <Field
            label={t("auth.email")}
            type="email"
            value={form.email}
            onChange={(value) => setForm({ ...form, email: value })}
            placeholder={t("ph.email")}
          />
          <Field
            label={t("auth.password")}
            type="password"
            value={form.password}
            onChange={(value) => setForm({ ...form, password: value })}
            placeholder={t("ph.passwordMask")}
          />
          {error && <InlineError message={error} />}
          <button className="button full" disabled={loading}>
            {loading ? t("auth.signingIn") : t("nav.signIn")}
          </button>
        </form>
        <p className="auth-switch">
          {t("auth.newHere")}{" "}
          <button onClick={() => onNavigate("/register")}>
            {t("auth.createAccount")}
          </button>
        </p>
      </div>
    </div>
  );
}

function RegisterView({ onNavigate, onFlash }) {
  const t = useT();
  const [role, setRole] = useState("customer");
  const [form, setForm] = useState({
    display_name: "",
    email: "",
    password: "",
    shop_name: "",
    region: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const update = (key, value) => setForm({ ...form, [key]: value });

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      if (role === "customer") {
        await api.registerCustomer({
          display_name: form.display_name,
          email: form.email,
          password: form.password,
        });
      } else {
        await api.registerShop({
          display_name: form.display_name,
          email: form.email,
          password: form.password,
          shop_name: form.shop_name,
          region: form.region,
          phone: form.phone || undefined,
        });
      }
      setDone(true);
      onFlash(t("reg.receivedEyebrow"));
    } catch (err) {
      setError(err.message);
    }
  };

  if (done) {
    return (
      <div className="page auth-page">
        <div className="auth-panel success-panel">
          <p className="eyebrow green">{t("reg.receivedEyebrow")}</p>
          <h1>{role === "shop" ? t("reg.underReview") : t("reg.accountReady")}</h1>
          <p>{role === "shop" ? t("reg.reviewNote") : t("reg.customerReadyNote")}</p>
          <button className="button full" onClick={() => onNavigate("/login")}>
            {t("reg.continueSignIn")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page auth-page">
      <div className="auth-panel wide">
        <p className="eyebrow orange">{t("reg.eyebrow")}</p>
        <h1>{t("reg.chooseTitle")}</h1>
        <div className="role-choice">
          <button
            className={role === "customer" ? "active" : ""}
            onClick={() => setRole("customer")}
          >
            <b>{t("reg.customerTag")}</b>
            <span>{t("reg.customerDesc")}</span>
          </button>
          <button
            className={role === "shop" ? "active" : ""}
            onClick={() => setRole("shop")}
          >
            <b>{t("reg.shopTag")}</b>
            <span>{t("reg.shopDesc")}</span>
          </button>
        </div>

        <form onSubmit={submit} className="stack-form">
          <Field
            label={t("reg.fullName")}
            value={form.display_name}
            onChange={(value) => update("display_name", value)}
            placeholder={t("ph.yourName")}
          />
          <Field
            label={t("auth.email")}
            type="email"
            value={form.email}
            onChange={(value) => update("email", value)}
            placeholder={t("ph.email")}
          />
          <Field
            label={t("auth.password")}
            type="password"
            value={form.password}
            onChange={(value) => update("password", value)}
            placeholder={t("ph.passwordHint")}
          />

          {role === "shop" && (
            <div className="shop-fields">
              <Field
                label={t("reg.shopName")}
                value={form.shop_name}
                onChange={(value) => update("shop_name", value)}
                placeholder={t("ph.shopOrStall")}
              />
              <Field
                label={t("reg.region")}
                value={form.region}
                onChange={(value) => update("region", value)}
                placeholder={t("ph.regionExample")}
              />
            </div>
          )}

          {error && <InlineError message={error} />}
          <button className="button full">
            {role === "shop" ? t("reg.submitShop") : t("reg.submitCustomer")}
          </button>
        </form>

        <p className="auth-switch">
          {t("reg.alreadyRegistered")}{" "}
          <button onClick={() => onNavigate("/login")}>{t("nav.signIn")}</button>
        </p>
      </div>
    </div>
  );
}

function DashboardRouter({ session, onNavigate, onFlash }) {
  const t = useT();
  if (session.user.role === "customer") {
    return <CustomerDashboard onNavigate={onNavigate} onFlash={onFlash} />;
  }
  if (session.user.role === "shop") {
    return <ShopDashboard onFlash={onFlash} />;
  }
  if (session.user.role === "admin") {
    return <AdminDashboard onFlash={onFlash} />;
  }
  return (
    <div className="page empty-state">
      <InlineError message={t("misc.unknownRole")} />
      <button
        className="button"
        onClick={() => {
          clearSession();
          window.location.reload();
        }}
      >
        {t("misc.returnToSignIn")}
      </button>
    </div>
  );
}

function CustomerDashboard({ onNavigate }) {
  const t = useT();
  const pluralS = (n) => (n === 1 ? "" : "s");
  const [dashboard, setDashboard] = useState(null);
  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState(null);
  const [error, setError] = useState("");

  const refresh = () =>
    Promise.all([
      api.customerDashboard(),
      api.customerThreads().catch(() => ({ threads: [] })),
    ])
      .then(([dash, messageData]) => {
        setDashboard(dash);
        setThreads(messageData.threads || []);
      })
      .catch((err) => setError(err.message));

  useEffect(() => {
    refresh();
  }, []);

  if (error) {
    return (
      <div className="page">
        <InlineError message={error} />
      </div>
    );
  }

  if (!dashboard) {
    return <div className="page empty-state">{t("load.customer")}</div>;
  }

  return (
    <div className="page dashboard-page">
      <SectionHeading
        eyebrow={t("cust.eyebrow")}
        title={t("cust.greeting", {
          name: dashboard.user.display_name.split(" ")[0],
        })}
        detail={t("cust.detail")}
      />

      <div className="metric-grid">
        <Metric
          label={t("metric.conversations")}
          value={dashboard.message_thread_count}
          accent="green"
        />
        <Metric
          label={t("metric.catalog")}
          value={dashboard.catalog_count}
        />
      </div>

      <div className="dashboard-columns">
        <aside className="side-note">
          <p className="eyebrow">{t("how.eyebrow")}</p>
          <h3>{t("how.title")}</h3>
          <p>{t("how.body")}</p>
          <button className="button outline" onClick={() => onNavigate("/")}>
            {t("how.openCatalog")}
          </button>
        </aside>
      </div>

      <section className="dashboard-section messages-section">
        <div className="section-title-row">
          <h2>{t("threads.title")}</h2>
          <span className="muted">
            {threads.length
              ? t("threads.count", {
                  n: threads.length,
                  s: pluralS(threads.length),
                })
              : t("threads.directWithShops")}
          </span>
        </div>

        {threads.length === 0 && !activeThread ? (
          <p className="muted">{t("threads.customerEmpty")}</p>
        ) : activeThread ? (
          <MessageThreadPanel
            productId={activeThread.product_id}
            heading={`${activeThread.product_name || t("misc.productFallback")} · ${
              activeThread.shop_name || t("misc.shopFallback")
            }`}
            thread={activeThread}
            onBack={() => setActiveThread(null)}
          />
        ) : (
          <div className="thread-list">
            {threads.map((thread) => (
              <button
                className="thread-row"
                key={`${thread.product_id}-${thread.customer_id}`}
                onClick={() => setActiveThread(thread)}
              >
                <div>
                  <b>{thread.product_name}</b>
                  <span>
                    {thread.shop_name} ·{" "}
                    {t("misc.messageCount", {
                      n: thread.message_count,
                      s: thread.message_count > 1 ? "s" : "",
                    })}
                  </span>
                  <small>{thread.last_body}</small>
                </div>
                <em>{new Date(thread.last_created_at).toLocaleDateString()}</em>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function ShopDashboard({ onFlash }) {
  const t = useT();
  const pluralS = (n) => (n === 1 ? "" : "s");
  const [dashboard, setDashboard] = useState(null);
  const [meta, setMeta] = useState({ categories: CATEGORIES, seasons: SEASONS });
  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState(null);
  const [phoneDraft, setPhoneDraft] = useState("");
  const blankForm = {
    name: "",
    category: "Fruit",
    price_azn: "",
    stock: "",
    season: "",
    image_url: "",
    description: "",
  };
  const [form, setForm] = useState(blankForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  const refresh = () =>
    Promise.all([
      api.shopDashboard(),
      api.meta(),
      api.shopThreads().catch(() => ({ threads: [] })),
    ])
      .then(([dash, metadata, messageData]) => {
        setDashboard(dash);
        setMeta(metadata);
        setPhoneDraft(dash.user.shop_profile?.phone || "");
        setThreads(messageData.threads || []);
        if (
          metadata.categories?.length &&
          !metadata.categories.includes(form.category)
        ) {
          setForm((current) => ({
            ...current,
            category: metadata.categories[0],
          }));
        }
      })
      .catch((err) => setError(err.message));

  useEffect(() => {
    refresh();
  }, []);

  const saveListing = async (event) => {
    event.preventDefault();
    setError("");
    try {
      if (editingId) {
        await api.shopListingUpdate(editingId, form);
        onFlash(t("flash.listingUpdated"));
      } else {
        await api.shopListing(form);
        onFlash(t("flash.listingPublished"));
      }
      setEditingId(null);
      setForm(blankForm);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const editListing = (listing) => {
    setEditingId(listing.id);
    setForm({
      name: listing.name,
      category: listing.category,
      price_azn: listing.price_azn,
      stock: listing.stock,
      season: listing.season,
      image_url: listing.image_url,
      description: listing.description || "",
    });
  };

  const savePhone = async () => {
    setError("");
    try {
      await api.updatePhone({ phone: phoneDraft });
      onFlash(t("flash.contactUpdated"));
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  if (error && !dashboard) {
    return (
      <div className="page">
        <InlineError message={error} />
      </div>
    );
  }

  if (!dashboard) {
    return <div className="page empty-state">{t("load.shop")}</div>;
  }

  const pending = dashboard.verification_status !== "approved";

  return (
    <div className="page dashboard-page">
      <SectionHeading
        eyebrow={t("shop.eyebrow")}
        title={
          dashboard.user.shop_profile?.shop_name || dashboard.user.display_name
        }
        detail={dashboard.user.shop_profile?.region || "Azerbaijan"}
      />

      {pending && (
        <div className="verification-banner">
          <div>
            <span className="status-pip orange-pip" />
            <strong>
              {t("shop.verification", {
                status: dashboard.verification_status.replaceAll("_", " "),
              })}
            </strong>
          </div>
          <span>{t("shop.bannerNote")}</span>
        </div>
      )}

      <section className="dashboard-section contact-section">
        <div className="section-title-row">
          <h2>{t("contact.number")}</h2>
          <span className="muted">{t("contact.shownNote")}</span>
        </div>
        <div className="phone-row">
          <input
            value={phoneDraft}
            onChange={(event) => setPhoneDraft(event.target.value)}
            placeholder="+994 22 216 01 45"
          />
          <button className="button button-small" onClick={savePhone}>
            {t("contact.save")}
          </button>
        </div>
        <small className="muted">{t("contact.hubsNote")}</small>
      </section>

      <div className="metric-grid">
        <Metric label="Listings" value={dashboard.listing_count} />
      </div>

      <div className="dashboard-columns shop-columns">
        <section className="dashboard-section">
          <div className="section-title-row">
            <h2>{t("listings.yours")}</h2>
            <span className="muted">
              {pending ? t("listings.locked") : t("listings.manage")}
            </span>
          </div>

          {error && <InlineError message={error} />}

          {!pending && (
            <form className="listing-form" onSubmit={saveListing}>
              <Field
                label={t("form.name")}
                value={form.name}
                onChange={(value) => setForm({ ...form, name: value })}
                placeholder={t("form.namePlaceholder")}
              />
              <label>
                <span>{t("filter.category")}</span>
                <select
                  value={form.category}
                  onChange={(event) =>
                    setForm({ ...form, category: event.target.value })
                  }
                >
                  {(meta.categories || CATEGORIES).map((category) => (
                    <option key={category}>{category}</option>
                  ))}
                </select>
              </label>
              <div className="form-row">
                <Field
                  label={t("form.price")}
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.price_azn}
                  onChange={(value) =>
                    setForm({ ...form, price_azn: value })
                  }
                  placeholder={t("form.pricePlaceholder")}
                />
                <Field
                  label={t("form.stock")}
                  type="number"
                  min="0"
                  step="1"
                  value={form.stock}
                  onChange={(value) => setForm({ ...form, stock: value })}
                  placeholder={t("form.stockPlaceholder")}
                />
              </div>
              <Field
                label={t("form.seasonWindow")}
                value={form.season}
                onChange={(value) => setForm({ ...form, season: value })}
                placeholder={t("form.seasonPlaceholder")}
              />
              <Field
                label={t("form.imageUrl")}
                type="url"
                value={form.image_url}
                onChange={(value) => setForm({ ...form, image_url: value })}
                placeholder={t("form.imagePlaceholder")}
              />
              <Field
                label={t("form.description")}
                value={form.description}
                onChange={(value) =>
                  setForm({ ...form, description: value })
                }
                placeholder={t("form.descriptionPlaceholder")}
              />
              <button className="button">
                {editingId ? t("listings.save") : t("listings.publish")}
              </button>
              {editingId && (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    setEditingId(null);
                    setForm(blankForm);
                  }}
                >
                  {t("listings.cancelEdit")}
                </button>
              )}
            </form>
          )}

          {dashboard.listings.length ? (
            <div className="listing-list">
              {dashboard.listings.map((listing) => (
                <div className="listing-row" key={listing.id}>
                  <img src={listing.image_url} alt="" />
                  <div>
                    <b>{listing.name}</b>
                    <span>
                      {listing.category} · {listing.stock} in stock
                    </span>
                  </div>
                  <strong>{money(listing.price_azn)}</strong>
                  <button
                    className="text-button"
                    onClick={() => editListing(listing)}
                  >
                    {t("listings.edit")}
                  </button>
                  <button
                    className="text-button danger-text"
                    onClick={async () => {
                      try {
                        await api.shopListingDelete(listing.id);
                        onFlash(t("flash.listingArchived"));
                        await refresh();
                      } catch (err) {
                        setError(err.message);
                      }
                    }}
                  >
                    {t("listings.archive")}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state compact">{t("listings.none")}</div>
          )}
        </section>
      </div>

      <section className="dashboard-section messages-section">
        <div className="section-title-row">
          <h2>{t("buyers.title")}</h2>
          <span className="muted">
            {threads.length
              ? t("threads.count", {
                  n: threads.length,
                  s: pluralS(threads.length),
                })
              : t("buyers.replyNote")}
          </span>
        </div>

        {threads.length === 0 && !activeThread ? (
          <p className="muted">{t("buyers.empty")}</p>
        ) : activeThread ? (
          <MessageThreadPanel
            productId={activeThread.product_id}
            heading={`${activeThread.product_name || t("misc.productFallback")} · ${
              activeThread.customer_name || t("misc.buyer")
            }`}
            thread={activeThread}
            onBack={() => setActiveThread(null)}
          />
        ) : (
          <div className="thread-list">
            {threads.map((thread) => (
              <button
                className="thread-row"
                key={`${thread.product_id}-${thread.customer_id}`}
                onClick={() => setActiveThread(thread)}
              >
                <div>
                  <b>{thread.product_name}</b>
                  <span>
                    {thread.customer_name} ·{" "}
                    {t("misc.messageCount", {
                      n: thread.message_count,
                      s: thread.message_count > 1 ? "s" : "",
                    })}
                  </span>
                  <small>{thread.last_body}</small>
                </div>
                <em>{new Date(thread.last_created_at).toLocaleDateString()}</em>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function AdminDashboard({ onFlash }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [newCategory, setNewCategory] = useState(CATEGORIES[0]);
  const [newRegion, setNewRegion] = useState("");

  const refresh = () =>
    Promise.all([
      api.adminDashboard(),
      api.adminShops("pending_verification"),
      api.adminUsers(),
      api.adminCategories(),
      api.adminRegions(),
    ])
      .then(([dashboard, shops, users, categories, regions]) =>
        setData({
          dashboard,
          shops: shops.shops || [],
          users: users.users || [],
          categories: categories.categories || [],
          regions: regions.regions || [],
        }),
      )
      .catch((err) => setError(err.message));

  useEffect(() => {
    refresh();
  }, []);

  const act = async (fn, id, message) => {
    try {
      await fn(id);
      onFlash(message);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const activateCategory = async (name) => {
    try {
      await api.createCategory({ name });
      onFlash(t("flash.categoryActivated"));
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const createCategory = () => activateCategory(newCategory);

  const createRegion = async (event) => {
    event.preventDefault();
    try {
      await api.createRegion({ name: newRegion });
      setNewRegion("");
      onFlash(t("flash.regionAdded"));
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const activateRegion = async (name) => {
    try {
      await api.createRegion({ name });
      onFlash(t("flash.regionActivated"));
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  if (error && !data) {
    return (
      <div className="page">
        <InlineError message={error} />
      </div>
    );
  }

  if (!data) {
    return <div className="page empty-state">{t("load.admin")}</div>;
  }

  const { dashboard } = data;

  return (
    <div className="page dashboard-page">
      <SectionHeading
        eyebrow={t("admin.eyebrow")}
        title={t("admin.title")}
        detail={t("admin.detail")}
      />

      {error && <InlineError message={error} />}

      <div className="metric-grid">
        <Metric
          label={t("admin.pendingShops")}
          value={dashboard.pending_shop_count}
          accent="orange"
        />
        <Metric label={t("metric.catalog")} value={dashboard.listing_count} />
        <Metric label={t("admin.users")} value={dashboard.user_count} />
      </div>

      <div className="admin-grid">
        <section className="dashboard-section">
          <div className="section-title-row">
            <h2>{t("admin.queue")}</h2>
            <span className="muted">
              {t("admin.waiting", { n: data.shops.length })}
            </span>
          </div>

          {data.shops.length ? (
            data.shops.map((shopEntry) => (
              <div className="queue-row" key={shopEntry.user.id}>
                <div>
                  <b>{shopEntry.profile.shop_name}</b>
                  <span>
                    {shopEntry.user.email} · {shopEntry.profile.region}
                  </span>
                </div>
                <div className="row-actions">
                  <button
                    className="button button-small"
                    onClick={() =>
                      act(
                        api.approveShop,
                        shopEntry.user.id,
                        t("flash.shopApproved"),
                      )
                    }
                  >
                    {t("admin.approve")}
                  </button>
                  <button
                    className="text-button danger-text"
                    onClick={() =>
                      act(
                        api.suspendShop,
                        shopEntry.user.id,
                        t("flash.shopSuspended"),
                      )
                    }
                  >
                    {t("admin.suspend")}
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state compact">{t("admin.noPending")}</div>
          )}
        </section>

        <section className="dashboard-section">
          <div className="section-title-row">
            <h2>{t("admin.userMgmt")}</h2>
            <span className="muted">{t("admin.suspendRestore")}</span>
          </div>

          {data.users.map((user) => (
            <div className="user-row" key={user.id}>
              <div>
                <b>{user.display_name}</b>
                <span>
                  {user.email} · {user.role}
                </span>
              </div>
              {user.role !== "admin" && (
                <button
                  className="text-button"
                  onClick={() =>
                    act(
                      user.account_status === "suspended"
                        ? user.role === "shop"
                          ? api.restoreShop
                          : api.restoreUser
                        : api.suspendUser,
                      user.id,
                      user.account_status === "suspended"
                        ? t("flash.userRestored")
                        : t("flash.userSuspended"),
                    )
                  }
                >
                  {user.account_status === "suspended"
                    ? t("admin.restore")
                    : t("admin.suspend")}
                </button>
              )}
            </div>
          ))}
        </section>

        <section className="dashboard-section taxonomy-section">
          <div className="section-title-row">
            <h2>{t("admin.controls")}</h2>
            <span className="muted">{t("admin.taxonomyNote")}</span>
          </div>

          <div className="taxonomy-grid">
            <div>
              <h3>{t("admin.categoriesHeading")}</h3>
              <div className="taxonomy-list">
                {data.categories.map((category) => (
                  <div className="taxonomy-item" key={category.id}>
                    <span className={category.active ? "" : "inactive-label"}>
                      {category.name}
                    </span>
                    <button
                      className="text-button"
                      onClick={() =>
                        category.active
                          ? act(
                              api.archiveCategory,
                              category.id,
                              t("flash.categoryArchived"),
                            )
                          : activateCategory(category.name)
                      }
                    >
                      {category.active
                        ? t("admin.archive")
                        : t("admin.activate")}
                    </button>
                  </div>
                ))}
              </div>
              <label className="taxonomy-form">
                <span>{t("admin.activateAllowed")}</span>
                <select
                  value={newCategory}
                  onChange={(event) => setNewCategory(event.target.value)}
                >
                  {CATEGORIES.map((category) => (
                    <option key={category}>{category}</option>
                  ))}
                </select>
                <button
                  className="button button-small"
                  onClick={createCategory}
                >
                  {t("admin.activate")}
                </button>
              </label>
            </div>

            <div>
              <h3>{t("admin.regionsHeading")}</h3>
              <div className="taxonomy-list">
                {data.regions.map((region) => (
                  <div className="taxonomy-item" key={region.id}>
                    <span className={region.active ? "" : "inactive-label"}>
                      {region.name}
                    </span>
                    <button
                      className="text-button"
                      onClick={() =>
                        region.active
                          ? act(
                              api.archiveRegion,
                              region.id,
                              t("flash.regionArchived"),
                            )
                          : activateRegion(region.name)
                      }
                    >
                      {region.active
                        ? t("admin.archive")
                        : t("admin.activate")}
                    </button>
                  </div>
                ))}
              </div>
              <form className="taxonomy-form" onSubmit={createRegion}>
                <span>{t("admin.addRegion")}</span>
                <input
                  value={newRegion}
                  onChange={(event) => setNewRegion(event.target.value)}
                  placeholder={t("admin.regionPlaceholder")}
                  required
                />
                <button className="button button-small">
                  {t("admin.addRegion")}
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  min,
  max,
  step,
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        type={type}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required
      />
    </label>
  );
}

function Metric({ label, value, accent }) {
  return (
    <div className={`metric ${accent || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function InlineError({ message }) {
  return <div className="inline-error">{message}</div>;
}

export default App;
