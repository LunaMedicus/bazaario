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

const STATUS_LABELS = {
  placed: "Placed",
  confirmed: "Confirmed",
  harvested: "Harvested",
  in_transit: "In transit",
  delivered: "Delivered",
};

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
  const [basket, setBasket] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("bazaario_basket")) || [];
    } catch {
      return [];
    }
  });
  const [notice, setNotice] = useState(null);

  const navigate = (to) => {
    window.history.pushState({}, "", to);
    window.dispatchEvent(new PopStateEvent("popstate"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    localStorage.setItem("bazaario_basket", JSON.stringify(basket));
  }, [basket]);

  const flash = (message, kind = "success") => {
    setNotice({ message, kind });
    window.setTimeout(() => setNotice(null), 3600);
  };

  const addToBasket = (product) => {
    setBasket((current) => {
      const existing = current.find((item) => item.product.id === product.id);
      if (existing) {
        return current.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: Math.min(item.quantity + 1, product.stock) }
            : item,
        );
      }
      return [...current, { product, quantity: 1 }];
    });
    flash(`${product.name} added to basket`);
  };

  const updateBasket = (productId, quantity) => {
    setBasket((current) =>
      current
        .map((item) =>
          item.product.id === productId ? { ...item, quantity: Math.max(0, quantity) } : item,
        )
        .filter((item) => item.quantity > 0),
    );
  };

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
  } else if (route === "/basket") {
    content = (
      <BasketView
        basket={basket}
        onUpdate={updateBasket}
        session={session}
        onNavigate={navigate}
        onFlash={flash}
        onClear={() => setBasket([])}
      />
    );
  } else if (route.startsWith("/product/")) {
    content = (
      <ProductDetail
        id={route.split("/").pop()}
        onAdd={addToBasket}
        onNavigate={navigate}
      />
    );
  } else {
    content = <CatalogView onAdd={addToBasket} onNavigate={navigate} />;
  }

  return (
    <div className="app-shell">
      <Header
        session={session}
        basketCount={basket.reduce((sum, item) => sum + item.quantity, 0)}
        onNavigate={navigate}
        onLogout={onLogout}
      />
      {notice && <div className={`toast ${notice.kind}`}>{notice.message}</div>}
      <main>{content}</main>
      <Footer />
    </div>
  );
}

function Header({ session, basketCount, onNavigate, onLogout }) {
  return (
    <header className="site-header">
      <button className="wordmark" onClick={() => onNavigate("/")} aria-label="Bazaario home">
        bazaario<span>.</span>
      </button>
      <nav className="main-nav">
        <button onClick={() => onNavigate("/")}>Catalog</button>
        {session && <button onClick={() => onNavigate("/dashboard")}>Dashboard</button>}
        <button className="basket-link" onClick={() => onNavigate("/basket")}>
          Basket <span>{basketCount}</span>
        </button>
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
      <span>BAZAARIO / AZERBAIJANI FARM MARKET</span>
      <span>Cash on delivery · Card sandbox</span>
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

function CatalogView({ onAdd, onNavigate }) {
  const [products, setProducts] = useState([]);
  const [regions, setRegions] = useState([]);
  const [filters, setFilters] = useState({ q: "", category: "", region: "", season: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.meta().then((data) => setRegions(data.regions || [])).catch(() => {});
  }, []);

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
        <div>
          <p className="eyebrow orange">THE OPEN MARKET</p>
          <h1>Harvests, delivered<br />from their source.</h1>
        </div>
        <p className="intro-copy">
          Browse seasonal produce, pantry staples and small-batch goods from farms across Azerbaijan.
        </p>
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
            {CATEGORIES.map((category) => <option key={category}>{category}</option>)}
          </select>
        </label>
        <label>
          <span>Region</span>
          <select value={filters.region} onChange={(event) => setFilters({ ...filters, region: event.target.value })}>
            <option value="">Every region</option>
            {regions.map((region) => <option key={region}>{region}</option>)}
          </select>
        </label>
        <label>
          <span>Season</span>
          <select value={filters.season} onChange={(event) => setFilters({ ...filters, season: event.target.value })}>
            <option value="">Any season</option>
            <option>Spring</option><option>Summer</option><option>Autumn</option><option>Winter</option><option>All year</option>
          </select>
        </label>
      </section>

      <div className="catalog-meta">
        <span>{loading ? "Loading catalog" : `${products.length} products`}</span>
        <span>8 agricultural categories</span>
      </div>
      {error && <InlineError message={error} />}
      {loading ? (
        <div className="empty-state">Loading the latest harvests…</div>
      ) : products.length ? (
        <div className="product-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} onAdd={onAdd} onOpen={() => onNavigate(`/product/${product.id}`)} />
          ))}
        </div>
      ) : (
        <div className="empty-state">No products match these filters.</div>
      )}
    </div>
  );
}

function ProductCard({ product, onAdd, onOpen }) {
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
        <div className="product-farm">{product.farm?.name}</div>
        <div className="product-card-bottom">
          <strong>{money(product.price_azn)}</strong>
          <button className="add-button" onClick={() => onAdd(product)}>Add +</button>
        </div>
      </div>
    </article>
  );
}

function ProductDetail({ id, onAdd, onNavigate }) {
  const [product, setProduct] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.product(id).then((data) => setProduct(data.product)).catch((err) => setError(err.message));
  }, [id]);
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
          <div className="detail-farm"><span>Source farm</span><strong>{product.farm?.name}</strong><small>{product.farm?.region}, Azerbaijan</small></div>
          <div className="detail-season"><span>Season</span><strong>{product.season}</strong><span className="stock-note">{product.stock} in stock</span></div>
          <div className="detail-purchase"><strong>{money(product.price_azn)}</strong><button className="button" onClick={() => onAdd(product)}>Add to basket</button></div>
          {product.reviews?.length > 0 && <div className="review-list"><h3>Customer notes</h3>{product.reviews.map((review) => <div className="review-line" key={review.id}><b>{"★".repeat(review.rating)}</b><span>{review.body || "A good harvest."}</span></div>)}</div>}
        </div>
      </section>
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
      <div className="auth-panel"><p className="eyebrow orange">ACCOUNT ACCESS</p><h1>Welcome back.</h1><p className="auth-subcopy">Sign in to manage your harvests, orders or marketplace operations.</p>
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
  const [form, setForm] = useState({ display_name: "", email: "", password: "", farm_name: "", region: "", document_reference: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const update = (key, value) => setForm({ ...form, [key]: value });
  const submit = async (event) => {
    event.preventDefault(); setError("");
    try {
      if (role === "customer") await api.registerCustomer({ display_name: form.display_name, email: form.email, password: form.password });
      else await api.registerFarmer(form);
      setDone(true); onFlash("Application received");
    } catch (err) { setError(err.message); }
  };
  if (done) return <div className="page auth-page"><div className="auth-panel success-panel"><p className="eyebrow green">APPLICATION RECEIVED</p><h1>{role === "farmer" ? "Under review." : "Account ready."}</h1><p>{role === "farmer" ? "An admin will review your farm profile. Publishing unlocks after approval." : "Your customer account is ready to use."}</p><button className="button full" onClick={() => onNavigate("/login")}>Continue to sign in</button></div></div>;
  return (
    <div className="page auth-page"><div className="auth-panel wide"><p className="eyebrow orange">CREATE ACCOUNT</p><h1>Choose your path.</h1><div className="role-choice"><button className={role === "customer" ? "active" : ""} onClick={() => setRole("customer")}><b>Customer</b><span>Shop and track deliveries.</span></button><button className={role === "farmer" ? "active" : ""} onClick={() => setRole("farmer")}><b>Farmer</b><span>Sell after farm verification.</span></button></div>
      <form onSubmit={submit} className="stack-form"><Field label="Full name" value={form.display_name} onChange={(value) => update("display_name", value)} placeholder="Your name" /><Field label="Email" type="email" value={form.email} onChange={(value) => update("email", value)} placeholder="you@example.com" /><Field label="Password" type="password" value={form.password} onChange={(value) => update("password", value)} placeholder="At least 8 characters" />
        {role === "farmer" && <div className="farmer-fields"><Field label="Farm name" value={form.farm_name} onChange={(value) => update("farm_name", value)} placeholder="Your farm or cooperative" /><Field label="Region" value={form.region} onChange={(value) => update("region", value)} placeholder="e.g. Lankaran" /><Field label="Document reference" value={form.document_reference} onChange={(value) => update("document_reference", value)} placeholder="Agricultural registration reference" /></div>}
        {error && <InlineError message={error} />}<button className="button full">Submit {role} registration</button>
      </form><p className="auth-switch">Already registered? <button onClick={() => onNavigate("/login")}>Sign in</button></p>
    </div></div>
  );
}

function DashboardRouter({ session, onNavigate, onFlash }) {
  if (session.user.role === "customer") return <CustomerDashboard onNavigate={onNavigate} onFlash={onFlash} />;
  if (session.user.role === "farmer") return <FarmerDashboard onFlash={onFlash} />;
  return <AdminDashboard onFlash={onFlash} />;
}

function CustomerDashboard({ onNavigate, onFlash }) {
  const [dashboard, setDashboard] = useState(null);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const refresh = () => Promise.all([api.customerDashboard(), api.customerOrders()]).then(([dash, orderData]) => { setDashboard(dash); setOrders(orderData.orders || []); }).catch((err) => setError(err.message));
  useEffect(() => { refresh(); }, []);
  if (error) return <div className="page"><InlineError message={error} /></div>;
  if (!dashboard) return <div className="page empty-state">Loading customer dashboard…</div>;
  return <div className="page dashboard-page"><SectionHeading eyebrow="CUSTOMER / DASHBOARD" title={`Good to see you, ${dashboard.user.display_name.split(" ")[0]}.`} detail="Your basket and every delivery in one place." />
    <div className="metric-grid"><Metric label="Orders" value={dashboard.order_count} /><Metric label="Catalog" value={dashboard.catalog_count} /><Metric label="Active delivery" value={orders.filter((order) => order.status !== "delivered").length} accent="green" /></div>
    <div className="dashboard-columns"><section className="dashboard-section"><div className="section-title-row"><h2>Order history</h2><button className="text-button" onClick={() => onNavigate("/")}>Keep shopping →</button></div>{orders.length ? orders.map((order) => <CustomerOrder key={order.id} order={order} onDelivered={async () => { await api.deliver(order.id); onFlash("Delivery confirmed"); refresh(); }} onReview={async (body) => { await api.review(order.id, body); onFlash("Review published"); refresh(); }} onDispute={async (reason) => { await api.dispute(order.id, { reason }); onFlash("Dispute flag sent to Bazaario ops"); }} />) : <div className="empty-state compact">No orders yet. Browse the catalog to start.</div>}</section><aside className="side-note"><p className="eyebrow">PAYMENT</p><h3>Two live checkout paths.</h3><p>Choose cash on delivery for a handoff payment, or use the card sandbox for an immediate test authorization.</p><button className="button outline" onClick={() => onNavigate("/basket")}>Open basket</button></aside></div>
  </div>;
}

function CustomerOrder({ order, onDelivered, onReview, onDispute }) {
  const [showReview, setShowReview] = useState(false);
  const [showDispute, setShowDispute] = useState(false);
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState("");
  const [reason, setReason] = useState("");
  const [working, setWorking] = useState(false);
  const firstItem = order.items[0];
  const run = async (fn) => { setWorking(true); try { await fn(); } finally { setWorking(false); } };
  return <article className="order-card"><div className="order-card-head"><div><span className="eyebrow">ORDER #{String(order.id).padStart(4, "0")}</span><h3>{firstItem?.name}{order.items.length > 1 ? ` + ${order.items.length - 1} more` : ""}</h3></div><strong>{money(order.total_azn)}</strong></div><OrderTimeline status={order.status} /><div className="order-card-foot"><span>{order.payment_method === "cash_on_delivery" ? "Cash on delivery" : "Card sandbox"} · {order.delivery_address}</span>{order.status === "in_transit" && <button className="button button-small" disabled={working} onClick={() => run(onDelivered)}>Confirm delivered</button>}{order.status === "delivered" && <><button className="text-button" onClick={() => setShowReview(!showReview)}>Review</button><button className="text-button danger-text" onClick={() => setShowDispute(!showDispute)}>Flag issue</button></>}</div>{showReview && <div className="inline-form"><label>Rating <select value={rating} onChange={(event) => setRating(Number(event.target.value))}><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select></label><input value={body} onChange={(event) => setBody(event.target.value)} placeholder="What stood out?" /><button className="button button-small" onClick={() => run(() => onReview({ product_id: firstItem.product_id, rating, body }))}>Publish</button></div>}{showDispute && <div className="inline-form"><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Describe the issue" /><button className="button button-small" onClick={() => run(() => onDispute(reason))}>Send flag</button></div>}</article>;
}

function OrderTimeline({ status }) {
  return <div className="timeline">{Object.entries(STATUS_LABELS).map(([key, label], index) => <div className={`timeline-step ${Object.keys(STATUS_LABELS).indexOf(status) >= index ? "complete" : ""}`} key={key}><span className="timeline-dot" /><span>{label}</span></div>)}</div>;
}

function FarmerDashboard({ onFlash }) {
  const [dashboard, setDashboard] = useState(null);
  const [orders, setOrders] = useState([]);
  const [meta, setMeta] = useState({ categories: CATEGORIES });
  const [form, setForm] = useState({ name: "", category: "Fruit", price_azn: "", stock: "", season: "", image_url: "", description: "" });
  const [error, setError] = useState("");
  const refresh = () => Promise.all([api.farmerDashboard(), api.farmerOrders(), api.meta()]).then(([dash, orderData, metadata]) => { setDashboard(dash); setOrders(orderData.orders || []); setMeta(metadata); }).catch((err) => setError(err.message));
  useEffect(() => { refresh(); }, []);
  const create = async (event) => { event.preventDefault(); setError(""); try { await api.farmerListing(form); onFlash("Listing published"); setForm({ ...form, name: "", price_azn: "", stock: "", season: "", image_url: "", description: "" }); refresh(); } catch (err) { setError(err.message); } };
  const transition = async (action, id) => { try { await action(id); onFlash("Order status updated"); refresh(); } catch (err) { setError(err.message); } };
  if (!dashboard) return <div className="page empty-state">Loading farmer dashboard…</div>;
  const pending = dashboard.verification_status !== "approved";
  return <div className="page dashboard-page"><SectionHeading eyebrow="FARMER / DASHBOARD" title={dashboard.user.farmer_profile?.farm_name || dashboard.user.display_name} detail={dashboard.user.farmer_profile?.region || "Azerbaijan"} />
    {pending && <div className="verification-banner"><div><span className="status-pip orange-pip" /><strong>Verification {dashboard.verification_status.replaceAll("_", " ")}</strong></div><span>Your farm profile is being reviewed. Listing publication unlocks after approval.</span></div>}
    <div className="metric-grid"><Metric label="Listings" value={dashboard.listing_count} /><Metric label="Incoming orders" value={dashboard.incoming_order_count} /><Metric label="Delivered earnings" value={money(dashboard.earnings_azn)} accent="green" /></div>
    <div className="dashboard-columns farmer-columns"><section className="dashboard-section"><div className="section-title-row"><h2>Your listings</h2><span className="muted">{pending ? "Publishing locked" : "Manage your catalog"}</span></div>{error && <InlineError message={error} />}{!pending && <form className="listing-form" onSubmit={create}><Field label="Product name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} placeholder="e.g. Orchard apples" /><label><span>Category</span><select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{(meta.categories || CATEGORIES).map((category) => <option key={category}>{category}</option>)}</select></label><div className="form-row"><Field label="Price / AZN" type="number" value={form.price_azn} onChange={(value) => setForm({ ...form, price_azn: value })} placeholder="4.50" /><Field label="Stock" type="number" value={form.stock} onChange={(value) => setForm({ ...form, stock: value })} placeholder="20" /></div><Field label="Season window" value={form.season} onChange={(value) => setForm({ ...form, season: value })} placeholder="August–October" /><Field label="Real image URL" value={form.image_url} onChange={(value) => setForm({ ...form, image_url: value })} placeholder="https://..." /><Field label="Description" value={form.description} onChange={(value) => setForm({ ...form, description: value })} placeholder="How this harvest is grown" /><button className="button">Publish listing</button></form>}{dashboard.listings.length ? <div className="listing-list">{dashboard.listings.map((listing) => <div className="listing-row" key={listing.id}><img src={listing.image_url} alt="" /><div><b>{listing.name}</b><span>{listing.category} · {listing.stock} in stock</span></div><strong>{money(listing.price_azn)}</strong><button className="text-button danger-text" onClick={async () => { try { await api.farmerListingDelete(listing.id); onFlash("Listing archived"); refresh(); } catch (err) { setError(err.message); } }}>Archive</button></div>)}</div> : <div className="empty-state compact">No listings yet.</div>}</section><section className="dashboard-section"><div className="section-title-row"><h2>Incoming orders</h2><span className="muted">Owned transitions only</span></div>{orders.length ? orders.map((order) => <article className="compact-order" key={order.id}><div><b>Order #{String(order.id).padStart(4, "0")}</b><span>{order.customer?.name} · {money(order.total_azn)}</span></div><div className="compact-order-actions"><span className={`status-chip ${order.status}`}>{STATUS_LABELS[order.status]}</span>{order.status === "placed" && <button className="button button-small" onClick={() => transition(api.farmerConfirm, order.id)}>Accept</button>}{order.status === "confirmed" && <button className="button button-small" onClick={() => transition(api.farmerHarvest, order.id)}>Harvested</button>}</div></article>) : <div className="empty-state compact">Incoming orders will appear here.</div>}</section></div>
  </div>;
}

function AdminDashboard({ onFlash }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [newCategory, setNewCategory] = useState(CATEGORIES[0]);
  const [newRegion, setNewRegion] = useState("");
  const refresh = () => Promise.all([
    api.adminDashboard(),
    api.adminFarmers("pending_verification"),
    api.adminOrders(),
    api.adminDisputes(),
    api.adminUsers(),
    api.adminCategories(),
    api.adminRegions(),
  ]).then(([dashboard, farmers, orders, disputes, users, categories, regions]) => setData({
    dashboard,
    farmers: farmers.farmers || [],
    orders: orders.orders || [],
    disputes: disputes.disputes || [],
    users: users.users || [],
    categories: categories.categories || [],
    regions: regions.regions || [],
  })).catch((err) => setError(err.message));
  useEffect(() => { refresh(); }, []);
  const act = async (fn, id, message) => {
    try { await fn(id); onFlash(message); refresh(); } catch (err) { setError(err.message); }
  };
  const activateCategory = async (name) => {
    try { await api.createCategory({ name }); onFlash("Category activated"); refresh(); }
    catch (err) { setError(err.message); }
  };
  const createCategory = () => activateCategory(newCategory);
  const createRegion = async (event) => {
    event.preventDefault();
    try { await api.createRegion({ name: newRegion }); setNewRegion(""); onFlash("Region added"); refresh(); }
    catch (err) { setError(err.message); }
  };
  const activateRegion = async (name) => {
    try { await api.createRegion({ name }); onFlash("Region activated"); refresh(); }
    catch (err) { setError(err.message); }
  };
  if (error && !data) return <div className="page"><InlineError message={error} /></div>;
  if (!data) return <div className="page empty-state">Loading admin console…</div>;
  const { dashboard } = data;
  return <div className="page dashboard-page"><SectionHeading eyebrow="ADMIN / OPERATIONS" title="Marketplace control." detail="Verification, orders and account health." />
    {error && <InlineError message={error} />}
    <div className="metric-grid"><Metric label="Pending farms" value={dashboard.pending_farmer_count} accent="orange" /><Metric label="Orders" value={dashboard.order_count} /><Metric label="Open disputes" value={dashboard.open_dispute_count} accent="orange" /><Metric label="Users" value={dashboard.user_count} /></div>
    <div className="admin-grid"><section className="dashboard-section"><div className="section-title-row"><h2>Verification queue</h2><span className="muted">{data.farmers.length} waiting</span></div>{data.farmers.length ? data.farmers.map((farmer) => <div className="queue-row" key={farmer.user.id}><div><b>{farmer.profile.farm_name}</b><span>{farmer.user.email} · {farmer.profile.region}</span><small>Document: {farmer.profile.document_reference}</small></div><div className="row-actions"><button className="button button-small" onClick={() => act(api.approveFarmer, farmer.user.id, "Farmer approved")}>Approve</button><button className="text-button danger-text" onClick={() => act(api.suspendFarmer, farmer.user.id, "Farmer suspended")}>Suspend</button></div></div>) : <div className="empty-state compact">No pending applications.</div>}</section>
      <section className="dashboard-section"><div className="section-title-row"><h2>Order oversight</h2><span className="muted">Courier/admin transit action</span></div>{data.orders.length ? data.orders.slice(0, 8).map((order) => <div className="compact-order" key={order.id}><div><b>#{String(order.id).padStart(4, "0")} · {order.customer?.name}</b><span>{order.items[0]?.name} · {money(order.total_azn)}</span></div><div className="compact-order-actions"><span className={`status-chip ${order.status}`}>{STATUS_LABELS[order.status]}</span>{order.status === "harvested" && <button className="button button-small" onClick={() => act(api.transit, order.id, "Order marked in transit")}>In transit</button>}</div></div>) : <div className="empty-state compact">No orders yet.</div>}</section>
      <section className="dashboard-section"><div className="section-title-row"><h2>User management</h2><span className="muted">Suspend / restore</span></div>{data.users.map((user) => <div className="user-row" key={user.id}><div><b>{user.display_name}</b><span>{user.email} · {user.role}</span></div>{user.role !== "admin" && <button className="text-button" onClick={() => act(user.account_status === "suspended" ? api.restoreUser : api.suspendUser, user.id, user.account_status === "suspended" ? "User restored" : "User suspended")}>{user.account_status === "suspended" ? "Restore" : "Suspend"}</button>}</div>)}</section>
      <section className="dashboard-section"><div className="section-title-row"><h2>Dispute flags</h2><span className="muted">Operational follow-up</span></div>{data.disputes.length ? data.disputes.map((dispute) => <div className="queue-row" key={dispute.id}><div><b>Order #{dispute.order_id}</b><span>{dispute.reason}</span><small>Raised by {dispute.raised_by}</small></div>{dispute.status === "open" && <button className="button button-small" onClick={() => act(api.resolveDispute, dispute.id, "Dispute resolved")}>Resolve</button>}</div>) : <div className="empty-state compact">No dispute flags.</div>}</section>
      <section className="dashboard-section taxonomy-section"><div className="section-title-row"><h2>Catalog controls</h2><span className="muted">Categories / regions</span></div><div className="taxonomy-grid"><div><h3>Categories</h3><div className="taxonomy-list">{data.categories.map((category) => <div className="taxonomy-item" key={category.id}><span className={category.active ? "" : "inactive-label"}>{category.name}</span><button className="text-button" onClick={() => category.active ? act(api.archiveCategory, category.id, "Category archived") : activateCategory(category.name)}>{category.active ? "Archive" : "Activate"}</button></div>)}</div><label className="taxonomy-form"><span>Activate allowed category</span><select value={newCategory} onChange={(event) => setNewCategory(event.target.value)}>{CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select><button className="button button-small" onClick={createCategory}>Activate</button></label></div><div><h3>Regions</h3><div className="taxonomy-list">{data.regions.map((region) => <div className="taxonomy-item" key={region.id}><span className={region.active ? "" : "inactive-label"}>{region.name}</span><button className="text-button" onClick={() => region.active ? act(api.archiveRegion, region.id, "Region archived") : activateRegion(region.name)}>{region.active ? "Archive" : "Activate"}</button></div>)}</div><form className="taxonomy-form" onSubmit={createRegion}><span>Add region</span><input value={newRegion} onChange={(event) => setNewRegion(event.target.value)} placeholder="e.g. Nakhchivan" required /><button className="button button-small">Add region</button></form></div></div></section>
    </div>
  </div>;
}

function BasketView({ basket, onUpdate, session, onNavigate, onFlash, onClear }) {
  const [address, setAddress] = useState("");
  const [payment, setPayment] = useState("cash_on_delivery");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const total = basket.reduce((sum, item) => sum + Number(item.product.price_azn) * item.quantity, 0);
  const checkout = async (event) => { event.preventDefault(); if (!session) return onNavigate("/login"); setLoading(true); setError(""); try { await api.checkout({ items: basket.map((item) => ({ product_id: item.product.id, quantity: item.quantity })), delivery_address: address, payment_method: payment }); onClear(); onFlash("Order placed"); onNavigate("/dashboard"); } catch (err) { setError(err.message); } finally { setLoading(false); } };
  return <div className="page basket-page"><SectionHeading eyebrow="YOUR BASKET" title={basket.length ? "Ready for checkout." : "Your basket is empty."} detail="Farm-fresh orders are reserved when you place them." />{basket.length ? <div className="basket-layout"><section className="basket-list">{basket.map((item) => <div className="basket-row" key={item.product.id}><img src={item.product.image_url} alt="" /><div><b>{item.product.name}</b><span>{item.product.farm?.name}</span><small>{money(item.product.price_azn)} each</small></div><div className="quantity-control"><button onClick={() => onUpdate(item.product.id, item.quantity - 1)}>−</button><span>{item.quantity}</span><button onClick={() => onUpdate(item.product.id, item.quantity + 1)}>+</button></div><strong>{money(Number(item.product.price_azn) * item.quantity)}</strong></div>)}</section><form className="checkout-panel" onSubmit={checkout}><p className="eyebrow green">CHECKOUT</p><div className="checkout-total"><span>Total</span><strong>{money(total)}</strong></div><Field label="Delivery address" value={address} onChange={setAddress} placeholder="Street, building, city" /><label><span>Payment</span><select value={payment} onChange={(event) => setPayment(event.target.value)}><option value="cash_on_delivery">Cash on delivery</option><option value="card_sandbox">Card sandbox</option></select></label>{error && <InlineError message={error} />}<button className="button full" disabled={loading}>{loading ? "Placing…" : session ? "Place order" : "Sign in to checkout"}</button></form></div> : <div className="empty-state"><button className="button" onClick={() => onNavigate("/")}>Browse the catalog</button></div>}</div>;
}

function Field({ label, value, onChange, type = "text", placeholder = "" }) {
  return <label><span>{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required /></label>;
}

function Metric({ label, value, accent }) { return <div className={`metric ${accent || ""}`}><span>{label}</span><strong>{value}</strong></div>; }
function InlineError({ message }) { return <div className="inline-error">{message}</div>; }

export default App;
