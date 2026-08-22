import React, { useEffect, useState } from "react";
import { api, clearSession, getSession, saveSession } from "./api";

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
        flash("Your session has expired. Please sign in again.", "error");
        navigate("/login");
      });
    return () => { active = false; };
  }, [session?.access_token]);

  const onLogin = (payload) => {
    saveSession(payload);
    setSession(payload);
    flash(`Signed in as ${payload.user.display_name}`);
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
  } else {
    content = <CatalogView onNavigate={navigate} />;
  }

  return (
    <div className="app-shell">
      <Header session={session} onNavigate={navigate} onLogout={onLogout} />
      {notice && <div className={`toast ${notice.kind}`}>{notice.message}</div>}
      <main>{content}</main>
      <Footer />
    </div>
  );
}

function Header({ session, onNavigate, onLogout }) {
  return (
    <header className="site-header">
      <button className="wordmark" onClick={() => onNavigate("/")} aria-label="Bazaario home">
        bazaario<span>.</span>
      </button>
      <nav className="main-nav">
        <button onClick={() => onNavigate("/")}>Catalog</button>
        {session && <button onClick={() => onNavigate("/dashboard")}>Dashboard</button>}
      </nav>
      <div className="header-actions">
        {session ? (
          <>
            <span className={`role-tag ${session.user.role}`}>{session.user.role}</span>
            <button className="text-button" onClick={onLogout}>Sign out</button>
          </>
        ) : (
          <>
            <button className="text-button" onClick={() => onNavigate("/login")}>Sign in</button>
            <button className="button button-small" onClick={() => onNavigate("/register")}>Join</button>
          </>
        )}
      </div>
    </header>
  );
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
  const [products, setProducts] = useState([]);
  const [meta, setMeta] = useState({ categories: CATEGORIES, regions: [], seasons: SEASONS });
  const [filters, setFilters] = useState({ q: "", category: "", region: "", season: "" });
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
    setLoading(true);
    const params = new URLSearchParams(
      Object.entries(filters).filter(([, value]) => value),
    ).toString();
    api.products(params)
      .then((data) => {
        if (active) setProducts(data.products || []);
      })
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [filters]);

  return (
    <div className="page page-catalog">
      <section className="catalog-intro">
        <h1>Catalog</h1>
        <p className="intro-copy">Contact the shop directly to buy. There are no delivery hubs; buyers and shops agree on pickup and payment between themselves.</p>
      </section>

      <section className="filter-bar" aria-label="Catalog filters">
        <label className="search-field">
          <span>Search</span>
          <input
            value={filters.q}
            onChange={(event) => setFilters({ ...filters, q: event.target.value })}
            placeholder="Apples, honey, tea..."
          />
        </label>
        <label>
          <span>Category</span>
          <select value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
            <option value="">All categories</option>
            {meta.categories.map((category) => <option key={category}>{category}</option>)}
          </select>
        </label>
        <label>
          <span>Region</span>
          <select value={filters.region} onChange={(event) => setFilters({ ...filters, region: event.target.value })}>
            <option value="">Every region</option>
            {meta.regions.map((region) => <option key={region}>{region}</option>)}
          </select>
        </label>
        <label>
          <span>Season</span>
          <select value={filters.season} onChange={(event) => setFilters({ ...filters, season: event.target.value })}>
            <option value="">Any season</option>
            {meta.seasons.map((season) => <option key={season}>{season}</option>)}
          </select>
        </label>
      </section>

      <div className="catalog-meta">
        <span>{loading ? "Loading catalog" : `${products.length} products`}</span>
        <span>{meta.categories.length} active agricultural categories</span>
      </div>
      {error && <InlineError message={error} />}
      {loading ? (
        <div className="empty-state">Loading catalog…</div>
      ) : products.length ? (
        <div className="product-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} onOpen={() => onNavigate(`/product/${product.id}`)} />
          ))}
        </div>
      ) : (
        <div className="empty-state">No products match these filters.</div>
      )}
    </div>
  );
}

function ProductCard({ product, onOpen }) {
  return (
    <article className="product-card">
      <button className="product-image-button" onClick={onOpen} aria-label={`View ${product.name}`}>
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="image-label">{product.category}</span>
      </button>
      <div className="product-card-body">
        <div className="product-card-topline">
          <span>{product.region}</span>
          <span>{product.season}</span>
        </div>
        <button className="product-name" onClick={onOpen}>{product.name}</button>
        <div className="product-shop">{product.shop?.name}</div>
        <div className="product-card-bottom">
          <strong>{money(product.price_azn)}</strong>
          <button className="add-button" onClick={onOpen}>View</button>
        </div>
      </div>
    </article>
  );
}

function ProductDetail({ id, onNavigate, onFlash }) {
  const [product, setProduct] = useState(null);
  const [error, setError] = useState("");
  const load = () => api.product(id).then((data) => setProduct(data.product)).catch((err) => setError(err.message));
  useEffect(() => { load(); }, [id]);
  if (error) return <div className="page"><InlineError message={error} /></div>;
  if (!product) return <div className="page empty-state">Loading product…</div>;
  return (
    <div className="page product-detail-page">
      <button className="back-link" onClick={() => onNavigate("/")}>← Back to catalog</button>
      <section className="product-detail">
        <div className="detail-image-wrap"><img src={product.image_url} alt={product.name} /></div>
        <div className="detail-copy">
          <p className="eyebrow orange">{product.category} / {product.region}</p>
          <h1>{product.name}</h1>
          <p className="detail-description">{product.description}</p>
          <div className="detail-shop"><span>Sold by</span><strong>{product.shop?.name}</strong><small>{product.shop?.region}, Azerbaijan</small></div>
          <div className="detail-season"><span>Season</span><strong>{product.season}</strong><span className="stock-note">{product.stock} in stock</span></div>
          <div className="detail-purchase"><strong>{money(product.price_azn)}</strong><span className="muted">Contact the shop to buy.</span></div>
          <ReviewSection productId={product.id} reviews={product.reviews} onDone={() => { load().then(onFlash ? undefined : undefined); }} />
        </div>
      </section>
      <section className="seller-contact-section">
        <SellerContact shop={product.shop} />
        <MessageThreadPanel productId={product.id} heading={`Messages with ${product.shop?.name || "the shop"}`} />
      </section>
    </div>
  );
}

function ReviewSection({ productId, reviews, onDone }) {
  const session = getSession();
  const isCustomer = session?.user?.role === "customer";
  const mine = isCustomer && session ? (reviews || []).find((review) => review.customer === session.user.display_name) : null;
  return (
    <div className="review-section">
      <h3>Reviews {reviews?.length ? `(${reviews.length})` : ""}</h3>
      {!reviews?.length && <p className="muted">No reviews yet.</p>}
      {reviews?.length > 0 && (
        <div className="review-list">
          {reviews.map((review) => (
            <div className="review-line" key={review.id}><b>{"★".repeat(review.rating)}</b><span>{review.body || "No comment."}</span><small>{review.customer}</small></div>
          ))}
        </div>
      )}
      {isCustomer && (
        <ReviewForm productId={productId} existing={mine} onSaved={onDone} />
      )}
      {!session && <p className="muted">Sign in as a customer to leave a review.</p>}
    </div>
  );
}

function ReviewForm({ productId, existing, onSaved }) {
  const [rating, setRating] = useState(existing?.rating || 5);
  const [body, setBody] = useState(existing?.body || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setSaving(true); setError("");
    try { await api.createReview(productId, { rating, body }); onSaved(); }
    catch (err) { setError(err.message); }
    finally { setSaving(false); }
  };
  return (
    <form className="inline-form review-form" onSubmit={submit}>
      <label>Rating <select value={rating} onChange={(event) => setRating(Number(event.target.value))}><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select></label>
      <input value={body} onChange={(event) => setBody(event.target.value)} placeholder={existing ? "Update your comment" : "What stood out?"} />
      <button className="button button-small" disabled={saving}>{existing ? "Update review" : "Publish"}</button>
      {error && <InlineError message={error} />}
    </form>
  );
}

function telHref(phone) {
  return `tel:${String(phone).replace(/[^+0-9]/g, "")}`;
}

function SellerContact({ shop }) {
  if (!shop?.phone) {
    return (
      <div className="seller-contact">
        <h3>Call the seller</h3>
        <p className="muted">This shop has not added a contact number yet. Send a message instead and they will reply here.</p>
      </div>
    );
  }
  return (
    <div className="seller-contact">
      <h3>Call the seller</h3>
      <p>Bazaario has no delivery hubs yet, so orders are arranged directly with the shop.</p>
      <a className="call-button" href={telHref(shop.phone)}>📞 Call {shop.phone}</a>
    </div>
  );
}

function MessageThreadPanel({ productId, heading, thread, viewerRole, onBack }) {
  const session = getSession();
  const [messages, setMessages] = useState(null);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const load = () => api.productMessages(productId).then((data) => setMessages(data.messages || [])).catch((err) => setError(err.message));
  useEffect(() => { setMessages(null); load(); }, [productId]);
  const send = async (event) => {
    event.preventDefault();
    if (!session) return;
    const payload = thread && session.user.role === "shop" ? { body, customer_id: thread.customer_id } : { body };
    setSending(true); setError("");
    try { await api.sendMessage(productId, payload); setBody(""); await load(); }
    catch (err) { setError(err.message); }
    finally { setSending(false); }
  };
  return (
    <div className="message-panel">
      <div className="section-title-row">
        <h3>{heading}</h3>
        {onBack && <button className="text-button" onClick={onBack}>← All conversations</button>}
      </div>
      {!session && <p className="muted">Sign in as a customer to message the seller about this listing.</p>}
      {session && error && <InlineError message={error} />}
      {session && (messages === null ? (
        <p className="muted">Loading conversation…</p>
      ) : messages.length === 0 ? (
        <p className="muted">No messages yet. Ask about availability, quantities or pickup.</p>
      ) : (
        <ul className="message-list">
          {messages.map((message) => (
            <li key={message.id} className={`message-line ${message.sender_role}`}>
              <span className="message-meta">{message.sender_role === "customer" ? message.sender : "Shop"} · {new Date(message.created_at).toLocaleString()}</span>
              <p>{message.body}</p>
            </li>
          ))}
        </ul>
      ))}
      {session && viewerRole !== "read-only" && (
        <form className="message-form" onSubmit={send}>
          <input value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write a message…" maxLength={2000} required />
          <button className="button button-small" disabled={sending}>{sending ? "Sending…" : "Send"}</button>
        </form>
      )}
    </div>
  );
}

function LoginView({ onLogin, onNavigate }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setLoading(true); setError("");
    try { onLogin(await api.login(form)); } catch (err) { setError(err.message); } finally { setLoading(false); }
  };
  return (
    <div className="page auth-page">
      <div className="auth-panel"><p className="eyebrow orange">ACCOUNT ACCESS</p><h1>Welcome back.</h1><p className="auth-subcopy">Sign in to manage your listings, messages or marketplace operations.</p>
        <form onSubmit={submit} className="stack-form">
          <Field label="Email" type="email" value={form.email} onChange={(value) => setForm({ ...form, email: value })} placeholder="you@example.com" />
          <Field label="Password" type="password" value={form.password} onChange={(value) => setForm({ ...form, password: value })} placeholder="••••••••" />
          {error && <InlineError message={error} />}
          <button className="button full" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button>
        </form>
        <p className="auth-switch">New to Bazaario? <button onClick={() => onNavigate("/register")}>Create an account</button></p>
      </div>
    </div>
  );
}

function RegisterView({ onNavigate, onFlash }) {
  const [role, setRole] = useState("customer");
  const [form, setForm] = useState({ display_name: "", email: "", password: "", shop_name: "", region: "", phone: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const update = (key, value) => setForm({ ...form, [key]: value });
  const submit = async (event) => {
    event.preventDefault(); setError("");
    try {
      if (role === "customer") await api.registerCustomer({ display_name: form.display_name, email: form.email, password: form.password });
      else await api.registerShop({ display_name: form.display_name, email: form.email, password: form.password, shop_name: form.shop_name, region: form.region, phone: form.phone || undefined });
      setDone(true); onFlash("Application received");
    } catch (err) { setError(err.message); }
  };
  if (done) return <div className="page auth-page"><div className="auth-panel success-panel"><p className="eyebrow green">APPLICATION RECEIVED</p><h1>{role === "shop" ? "Under review." : "Account ready."}</h1><p>{role === "shop" ? "An admin will review your shop profile. Publishing unlocks after approval." : "Your customer account is ready to use."}</p><button className="button full" onClick={() => onNavigate("/login")}>Continue to sign in</button></div></div>;
  return (
    <div className="page auth-page"><div className="auth-panel wide"><p className="eyebrow orange">CREATE ACCOUNT</p><h1>Choose your path.</h1><div className="role-choice"><button className={role === "customer" ? "active" : ""} onClick={() => setRole("customer")}><b>Customer</b><span>Contact shops and leave reviews.</span></button><button className={role === "shop" ? "active" : ""} onClick={() => setRole("shop")}><b>Shop</b><span>Sell after verification.</span></button></div>
      <form onSubmit={submit} className="stack-form"><Field label="Full name" value={form.display_name} onChange={(value) => update("display_name", value)} placeholder="Your name" /><Field label="Email" type="email" value={form.email} onChange={(value) => update("email", value)} placeholder="you@example.com" /><Field label="Password" type="password" value={form.password} onChange={(value) => update("password", value)} placeholder="At least 8 characters" />
        {role === "shop" && <div className="shop-fields"><Field label="Shop name" value={form.shop_name} onChange={(value) => update("shop_name", value)} placeholder="Your shop or stall" /><Field label="Region" value={form.region} onChange={(value) => update("region", value)} placeholder="e.g. Lankaran" /></div>}
        {error && <InlineError message={error} />}<button className="button full">Submit {role} registration</button>
      </form><p className="auth-switch">Already registered? <button onClick={() => onNavigate("/login")}>Sign in</button></p>
    </div></div>
  );
}

function DashboardRouter({ session, onNavigate, onFlash }) {
  if (session.user.role === "customer") return <CustomerDashboard onNavigate={onNavigate} onFlash={onFlash} />;
  if (session.user.role === "shop") return <ShopDashboard onFlash={onFlash} />;
  if (session.user.role === "admin") return <AdminDashboard onFlash={onFlash} />;
  return <div className="page empty-state"><InlineError message="This session has an unknown role. Please sign in again." /><button className="button" onClick={() => { clearSession(); window.location.reload(); }}>Return to sign in</button></div>;
}

function CustomerDashboard({ onNavigate }) {
  const [dashboard, setDashboard] = useState(null);
  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState(null);
  const [error, setError] = useState("");
  const refresh = () => Promise.all([api.customerDashboard(), api.customerThreads().catch(() => ({ threads: [] }))]).then(([dash, messageData]) => { setDashboard(dash); setThreads(messageData.threads || []); }).catch((err) => setError(err.message));
  useEffect(() => { refresh(); }, []);
  if (error) return <div className="page"><InlineError message={error} /></div>;
  if (!dashboard) return <div className="page empty-state">Loading dashboard…</div>;
  return <div className="page dashboard-page"><SectionHeading eyebrow="CUSTOMER / DASHBOARD" title={`Good to see you, ${dashboard.user.display_name.split(" ")[0]}.`} detail="Buy by contacting shops directly." />
    <div className="metric-grid"><Metric label="Conversations" value={dashboard.message_thread_count} accent="green" /><Metric label="Catalog" value={dashboard.catalog_count} /></div>
    <div className="dashboard-columns"><aside className="side-note"><p className="eyebrow">HOW BUYING WORKS</p><h3>Agreement based.</h3><p>Pick a listing, call or message the shop, and settle price, quantity and handover with them. Reviews are per product.</p><button className="button outline" onClick={() => onNavigate("/")}>Open catalog</button></aside></div>
    <section className="dashboard-section messages-section"><div className="section-title-row"><h2>Messages with sellers</h2><span className="muted">{threads.length ? `${threads.length} conversation${threads.length > 1 ? "s" : ""}` : "Direct with each shop"}</span></div>{threads.length === 0 && !activeThread ? <p className="muted">No conversations yet. Open any product and use "Write a message" to reach a shop directly. There are no delivery hubs, everything is arranged with the seller.</p> : activeThread ? <MessageThreadPanel productId={activeThread.product_id} heading={`${activeThread.product_name || "Product"} · ${activeThread.shop_name || "shop"}`} thread={activeThread} onBack={() => setActiveThread(null)} /> : <div className="thread-list">{threads.map((thread) => <button className="thread-row" key={`${thread.product_id}-${thread.customer_id}`} onClick={() => setActiveThread(thread)}><div><b>{thread.product_name}</b><span>{thread.shop_name} · {thread.message_count} message{thread.message_count > 1 ? "s" : ""}</span><small>{thread.last_body}</small></div><em>{new Date(thread.last_created_at).toLocaleDateString()}</em></button>)}</div>}</section>
  </div>;
}

function ShopDashboard({ onFlash }) {
  const [dashboard, setDashboard] = useState(null);
  const [meta, setMeta] = useState({ categories: CATEGORIES, seasons: SEASONS });
  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState(null);
  const [phoneDraft, setPhoneDraft] = useState("");
  const blankForm = { name: "", category: "Fruit", price_azn: "", stock: "", season: "", image_url: "", description: "" };
  const [form, setForm] = useState(blankForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const refresh = () => Promise.all([api.shopDashboard(), api.meta(), api.shopThreads().catch(() => ({ threads: [] }))]).then(([dash, metadata, messageData]) => {
    setDashboard(dash);
    setMeta(metadata);
    setPhoneDraft(dash.user.shop_profile?.phone || "");
    setThreads(messageData.threads || []);
    if (metadata.categories?.length && !metadata.categories.includes(form.category)) {
      setForm((current) => ({ ...current, category: metadata.categories[0] }));
    }
  }).catch((err) => setError(err.message));
  useEffect(() => { refresh(); }, []);
  const saveListing = async (event) => {
    event.preventDefault();
    setError("");
    try {
      if (editingId) {
        await api.shopListingUpdate(editingId, form);
        onFlash("Listing updated");
      } else {
        await api.shopListing(form);
        onFlash("Listing published");
      }
      setEditingId(null);
      setForm(blankForm);
      await refresh();
    } catch (err) { setError(err.message); }
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
    try { await api.updatePhone({ phone: phoneDraft }); onFlash("Contact number updated"); await refresh(); }
    catch (err) { setError(err.message); }
  };
  if (error && !dashboard) return <div className="page"><InlineError message={error} /></div>;
  if (!dashboard) return <div className="page empty-state">Loading shop dashboard…</div>;
  const pending = dashboard.verification_status !== "approved";
  return <div className="page dashboard-page"><SectionHeading eyebrow="SHOP / DASHBOARD" title={dashboard.user.shop_profile?.shop_name || dashboard.user.display_name} detail={dashboard.user.shop_profile?.region || "Azerbaijan"} />
    {pending && <div className="verification-banner"><div><span className="status-pip orange-pip" /><strong>Verification {dashboard.verification_status.replaceAll("_", " ")}</strong></div><span>Your shop profile is being reviewed. Listing publication unlocks after approval.</span></div>}
    <section className="dashboard-section contact-section"><div className="section-title-row"><h2>Contact number</h2><span className="muted">Shown on your listings for direct calls</span></div><div className="phone-row"><input value={phoneDraft} onChange={(event) => setPhoneDraft(event.target.value)} placeholder="+994 22 216 01 45" /><button className="button button-small" onClick={savePhone}>Save number</button></div><small className="muted">There are no delivery hubs yet, so buyers arrange handover by calling or messaging you.</small></section>
    <div className="metric-grid"><Metric label="Listings" value={dashboard.listing_count} /></div>
    <div className="dashboard-columns shop-columns"><section className="dashboard-section"><div className="section-title-row"><h2>Your listings</h2><span className="muted">{pending ? "Publishing locked" : "Manage your catalog"}</span></div>{error && <InlineError message={error} />}{!pending && <form className="listing-form" onSubmit={saveListing}><Field label="Product name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} placeholder="e.g. Orchard apples" /><label><span>Category</span><select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{(meta.categories || CATEGORIES).map((category) => <option key={category}>{category}</option>)}</select></label><div className="form-row"><Field label="Price / AZN" type="number" min="0" step="0.01" value={form.price_azn} onChange={(value) => setForm({ ...form, price_azn: value })} placeholder="4.50" /><Field label="Stock" type="number" min="0" step="1" value={form.stock} onChange={(value) => setForm({ ...form, stock: value })} placeholder="20" /></div><Field label="Season window" value={form.season} onChange={(value) => setForm({ ...form, season: value })} placeholder="August–October" /><Field label="Real image URL" type="url" value={form.image_url} onChange={(value) => setForm({ ...form, image_url: value })} placeholder="https://..." /><Field label="Description" value={form.description} onChange={(value) => setForm({ ...form, description: value })} placeholder="How this crop is grown" /><button className="button">{editingId ? "Save listing" : "Publish listing"}</button>{editingId && <button type="button" className="text-button" onClick={() => { setEditingId(null); setForm(blankForm); }}>Cancel edit</button>}</form>}{dashboard.listings.length ? <div className="listing-list">{dashboard.listings.map((listing) => <div className="listing-row" key={listing.id}><img src={listing.image_url} alt="" /><div><b>{listing.name}</b><span>{listing.category} · {listing.stock} in stock</span></div><strong>{money(listing.price_azn)}</strong><button className="text-button" onClick={() => editListing(listing)}>Edit</button><button className="text-button danger-text" onClick={async () => { try { await api.shopListingDelete(listing.id); onFlash("Listing archived"); await refresh(); } catch (err) { setError(err.message); } }}>Archive</button></div>)}</div> : <div className="empty-state compact">No listings yet.</div>}</section></div>
    <section className="dashboard-section messages-section"><div className="section-title-row"><h2>Buyer messages</h2><span className="muted">{threads.length ? `${threads.length} conversation${threads.length > 1 ? "s" : ""}` : "Reply from your listings"}</span></div>{threads.length === 0 && !activeThread ? <p className="muted">No buyer questions yet. Buyers reach out from your product pages.</p> : activeThread ? <MessageThreadPanel productId={activeThread.product_id} heading={`${activeThread.product_name || "Product"} · ${activeThread.customer_name || "buyer"}`} thread={activeThread} onBack={() => setActiveThread(null)} /> : <div className="thread-list">{threads.map((thread) => <button className="thread-row" key={`${thread.product_id}-${thread.customer_id}`} onClick={() => setActiveThread(thread)}><div><b>{thread.product_name}</b><span>{thread.customer_name} · {thread.message_count} message{thread.message_count > 1 ? "s" : ""}</span><small>{thread.last_body}</small></div><em>{new Date(thread.last_created_at).toLocaleDateString()}</em></button>)}</div>}</section>
  </div>;
}

function AdminDashboard({ onFlash }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [newCategory, setNewCategory] = useState(CATEGORIES[0]);
  const [newRegion, setNewRegion] = useState("");
  const refresh = () => Promise.all([
    api.adminDashboard(),
    api.adminShops("pending_verification"),
    api.adminUsers(),
    api.adminCategories(),
    api.adminRegions(),
  ]).then(([dashboard, shops, users, categories, regions]) => setData({
    dashboard,
    shops: shops.shops || [],
    users: users.users || [],
    categories: categories.categories || [],
    regions: regions.regions || [],
  })).catch((err) => setError(err.message));
  useEffect(() => { refresh(); }, []);
  const act = async (fn, id, message) => {
    try { await fn(id); onFlash(message); await refresh(); } catch (err) { setError(err.message); }
  };
  const activateCategory = async (name) => {
    try { await api.createCategory({ name }); onFlash("Category activated"); await refresh(); }
    catch (err) { setError(err.message); }
  };
  const createCategory = () => activateCategory(newCategory);
  const createRegion = async (event) => {
    event.preventDefault();
    try { await api.createRegion({ name: newRegion }); setNewRegion(""); onFlash("Region added"); await refresh(); }
    catch (err) { setError(err.message); }
  };
  const activateRegion = async (name) => {
    try { await api.createRegion({ name }); onFlash("Region activated"); await refresh(); }
    catch (err) { setError(err.message); }
  };
  if (error && !data) return <div className="page"><InlineError message={error} /></div>;
  if (!data) return <div className="page empty-state">Loading admin console…</div>;
  const { dashboard } = data;
  return <div className="page dashboard-page"><SectionHeading eyebrow="ADMIN / OPERATIONS" title="Marketplace control." detail="Verification and account health." />
    {error && <InlineError message={error} />}
    <div className="metric-grid"><Metric label="Pending shops" value={dashboard.pending_shop_count} accent="orange" /><Metric label="Listings" value={dashboard.listing_count} /><Metric label="Users" value={dashboard.user_count} /></div>
    <div className="admin-grid"><section className="dashboard-section"><div className="section-title-row"><h2>Verification queue</h2><span className="muted">{data.shops.length} waiting</span></div>{data.shops.length ? data.shops.map((shopEntry) => <div className="queue-row" key={shopEntry.user.id}><div><b>{shopEntry.profile.shop_name}</b><span>{shopEntry.user.email} · {shopEntry.profile.region}</span></div><div className="row-actions"><button className="button button-small" onClick={() => act(api.approveShop, shopEntry.user.id, "Shop approved")}>Approve</button><button className="text-button danger-text" onClick={() => act(api.suspendShop, shopEntry.user.id, "Shop suspended")}>Suspend</button></div></div>) : <div className="empty-state compact">No pending applications.</div>}</section>
      <section className="dashboard-section"><div className="section-title-row"><h2>User management</h2><span className="muted">Suspend / restore</span></div>{data.users.map((user) => <div className="user-row" key={user.id}><div><b>{user.display_name}</b><span>{user.email} · {user.role}</span></div>{user.role !== "admin" && <button className="text-button" onClick={() => act(user.account_status === "suspended" ? (user.role === "shop" ? api.restoreShop : api.restoreUser) : api.suspendUser, user.id, user.account_status === "suspended" ? "User restored" : "User suspended")}>{user.account_status === "suspended" ? "Restore" : "Suspend"}</button>}</div>)}</section>
      <section className="dashboard-section taxonomy-section"><div className="section-title-row"><h2>Catalog controls</h2><span className="muted">Categories / regions</span></div><div className="taxonomy-grid"><div><h3>Categories</h3><div className="taxonomy-list">{data.categories.map((category) => <div className="taxonomy-item" key={category.id}><span className={category.active ? "" : "inactive-label"}>{category.name}</span><button className="text-button" onClick={() => category.active ? act(api.archiveCategory, category.id, "Category archived") : activateCategory(category.name)}>{category.active ? "Archive" : "Activate"}</button></div>)}</div><label className="taxonomy-form"><span>Activate allowed category</span><select value={newCategory} onChange={(event) => setNewCategory(event.target.value)}>{CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select><button className="button button-small" onClick={createCategory}>Activate</button></label></div><div><h3>Regions</h3><div className="taxonomy-list">{data.regions.map((region) => <div className="taxonomy-item" key={region.id}><span className={region.active ? "" : "inactive-label"}>{region.name}</span><button className="text-button" onClick={() => region.active ? act(api.archiveRegion, region.id, "Region archived") : activateRegion(region.name)}>{region.active ? "Archive" : "Activate"}</button></div>)}</div><form className="taxonomy-form" onSubmit={createRegion}><span>Add region</span><input value={newRegion} onChange={(event) => setNewRegion(event.target.value)} placeholder="e.g. Nakhchivan" required /><button className="button button-small">Add region</button></form></div></div></section>
    </div>
  </div>;
}

function Field({ label, value, onChange, type = "text", placeholder = "", min, max, step }) {
  return <label><span>{label}</span><input type={type} value={value} min={min} max={max} step={step} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required /></label>;
}

function Metric({ label, value, accent }) { return <div className={`metric ${accent || ""}`}><span>{label}</span><strong>{value}</strong></div>; }
function InlineError({ message }) { return <div className="inline-error">{message}</div>; }

export default App;
