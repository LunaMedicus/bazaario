const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem("bazaario_session")) || null;
  } catch {
    return null;
  }
}

export function saveSession(session) {
  localStorage.setItem("bazaario_session", JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem("bazaario_session");
}

export async function apiFetch(path, options = {}) {
  const session = getSession();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.message || payload.error || "Something went wrong");
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export const api = {
  login: (body) => apiFetch("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  registerCustomer: (body) => apiFetch("/auth/register/customer", { method: "POST", body: JSON.stringify(body) }),
  registerFarmer: (body) => apiFetch("/auth/register/farmer", { method: "POST", body: JSON.stringify(body) }),
  meta: () => apiFetch("/meta"),
  products: (params = "") => apiFetch(`/products${params ? `?${params}` : ""}`),
  product: (id) => apiFetch(`/products/${id}`),
  customerDashboard: () => apiFetch("/customer/dashboard"),
  customerOrders: () => apiFetch("/customer/orders"),
  checkout: (body) => apiFetch("/customer/orders", { method: "POST", body: JSON.stringify(body) }),
  deliver: (id) => apiFetch(`/customer/orders/${id}/delivered`, { method: "POST" }),
  review: (id, body) => apiFetch(`/customer/orders/${id}/reviews`, { method: "POST", body: JSON.stringify(body) }),
  dispute: (id, body) => apiFetch(`/customer/orders/${id}/dispute`, { method: "POST", body: JSON.stringify(body) }),
  farmerDashboard: () => apiFetch("/farmer/dashboard"),
  farmerOrders: () => apiFetch("/farmer/orders"),
  farmerListing: (body) => apiFetch("/farmer/listings", { method: "POST", body: JSON.stringify(body) }),
  farmerListingUpdate: (id, body) => apiFetch(`/farmer/listings/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  farmerListingDelete: (id) => apiFetch(`/farmer/listings/${id}`, { method: "DELETE" }),
  farmerConfirm: (id) => apiFetch(`/farmer/orders/${id}/confirm`, { method: "POST" }),
  farmerHarvest: (id) => apiFetch(`/farmer/orders/${id}/harvested`, { method: "POST" }),
  adminDashboard: () => apiFetch("/admin/dashboard"),
  adminFarmers: (status = "") => apiFetch(`/admin/farmers${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  approveFarmer: (id) => apiFetch(`/admin/farmers/${id}/approve`, { method: "POST" }),
  suspendFarmer: (id) => apiFetch(`/admin/farmers/${id}/suspend`, { method: "POST" }),
  adminOrders: () => apiFetch("/admin/orders"),
  transit: (id) => apiFetch(`/admin/orders/${id}/in-transit`, { method: "POST" }),
  adminDisputes: () => apiFetch("/admin/disputes"),
  resolveDispute: (id) => apiFetch(`/admin/disputes/${id}/resolve`, { method: "POST" }),
  adminUsers: () => apiFetch("/admin/users"),
  suspendUser: (id) => apiFetch(`/admin/users/${id}/suspend`, { method: "POST" }),
  restoreUser: (id) => apiFetch(`/admin/users/${id}/restore`, { method: "POST" }),
  adminCategories: () => apiFetch("/admin/categories"),
  createCategory: (body) => apiFetch("/admin/categories", { method: "POST", body: JSON.stringify(body) }),
  archiveCategory: (id) => apiFetch(`/admin/categories/${id}`, { method: "DELETE" }),
  adminRegions: () => apiFetch("/admin/regions"),
  createRegion: (body) => apiFetch("/admin/regions", { method: "POST", body: JSON.stringify(body) }),
  archiveRegion: (id) => apiFetch(`/admin/regions/${id}`, { method: "DELETE" }),
};
