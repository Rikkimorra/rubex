const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const API_BASE = ""; // backend раздаёт и API, и статику с одного домена

const state = {
  tab: "0-50k",
  direction: "",
  me: null,
};

function authHeader() {
  const initData = tg?.initData || "";
  return { Authorization: `tma ${initData}` };
}

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = body.detail || msg;
    } catch (_) {}
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

function fmtRub(n) {
  return new Intl.NumberFormat("ru-RU").format(n) + " ₽";
}

function renderSubBadge() {
  const el = document.getElementById("sub-badge");
  if (!state.me) return;
  if (state.me.is_subscribed) {
    const until = new Date(state.me.subscription_until);
    el.textContent = "Подписка до " + until.toLocaleDateString("ru-RU");
    el.classList.add("active");
  } else {
    el.textContent = "Нет подписки";
    el.classList.remove("active");
  }
}

async function loadMe() {
  state.me = await api("/api/me");
  renderSubBadge();
}

function cardHtml(listing) {
  const dirLabel = listing.direction === "buy" ? "Купить рубли" : "Продать рубли";
  const dirClass = listing.direction === "buy" ? "buy" : "sell";
  const details = listing.details ? `<div class="card-details">${escapeHtml(listing.details)}</div>` : "";

  let contact;
  if (listing.contact_locked) {
    contact = `<div class="card-locked">Оформите подписку, чтобы увидеть автора и написать ему</div>`;
  } else {
    const name = listing.author_username
      ? `<a href="https://t.me/${listing.author_username}" target="_blank">@${listing.author_username}</a>`
      : (listing.author_first_name || "пользователь");
    contact = `<div class="card-contact">Автор: ${name}</div>`;
  }

  return `
    <div class="card">
      <div class="card-top">
        <div class="card-amount">${fmtRub(listing.amount_rub)}</div>
        <div class="card-dir ${dirClass}">${dirLabel}</div>
      </div>
      ${details}
      ${contact}
    </div>
  `;
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

async function loadListings() {
  const container = document.getElementById("listings");
  const empty = document.getElementById("empty-state");
  container.innerHTML = '<div class="empty-state">Загрузка…</div>';

  const params = new URLSearchParams({ tab: state.tab });
  if (state.direction) params.set("direction", state.direction);

  try {
    const items = await api(`/api/listings?${params.toString()}`);
    if (items.length === 0) {
      container.innerHTML = '<div class="empty-state">Пока нет объявлений в этой вкладке</div>';
      return;
    }
    container.innerHTML = items.map(cardHtml).join("");
  } catch (e) {
    container.innerHTML = `<div class="empty-state">Ошибка загрузки: ${escapeHtml(e.message)}</div>`;
  }
}

// --- вкладки по суммам ---
document.getElementById("amount-tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  state.tab = btn.dataset.tab;
  loadListings();
});

document.getElementById("direction-toggle").addEventListener("click", (e) => {
  const btn = e.target.closest(".dir");
  if (!btn) return;
  document.querySelectorAll(".dir").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  state.direction = btn.dataset.dir;
  loadListings();
});

// --- overlay / sheets ---
const overlay = document.getElementById("overlay");
function openSheet(id) {
  overlay.classList.add("open");
  document.querySelectorAll(".sheet").forEach((s) => s.classList.remove("open"));
  document.getElementById(id).classList.add("open");
}
function closeSheets() {
  overlay.classList.remove("open");
  document.querySelectorAll(".sheet").forEach((s) => s.classList.remove("open"));
}
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) closeSheets();
});

// --- форма добавления объявления ---
let formDir = "buy";
document.querySelectorAll("[data-form-dir]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("[data-form-dir]").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    formDir = btn.dataset.formDir;
  });
});

document.getElementById("fab-add").addEventListener("click", () => {
  if (!state.me?.is_subscribed) {
    openPaywall();
    return;
  }
  document.getElementById("form-error").textContent = "";
  document.getElementById("form-amount").value = "";
  document.getElementById("form-details").value = "";
  openSheet("sheet-add");
});

document.getElementById("form-cancel").addEventListener("click", closeSheets);

document.getElementById("form-submit").addEventListener("click", async () => {
  const amount = parseFloat(document.getElementById("form-amount").value);
  const details = document.getElementById("form-details").value.trim();
  const errorEl = document.getElementById("form-error");
  errorEl.textContent = "";

  if (!amount || amount <= 0) {
    errorEl.textContent = "Укажите корректную сумму";
    return;
  }

  try {
    await api("/api/listings", {
      method: "POST",
      body: JSON.stringify({ direction: formDir, amount_rub: amount, details: details || null }),
    });
    closeSheets();
    tg?.HapticFeedback?.notificationOccurred("success");
    await loadListings();
  } catch (e) {
    if (e.status === 402) {
      closeSheets();
      openPaywall();
    } else {
      errorEl.textContent = e.message;
    }
  }
});

// --- пэйвол / оплата подписки ---
function openPaywall() {
  document.getElementById("paywall-error").textContent = "";
  if (state.me) {
    document.getElementById("paywall-price").textContent =
      `${state.me.subscription_price_usdt} USDT / ${state.me.subscription_days} дней`;
  }
  openSheet("sheet-paywall");
}
document.getElementById("paywall-cancel").addEventListener("click", closeSheets);

document.getElementById("paywall-pay").addEventListener("click", async () => {
  const errorEl = document.getElementById("paywall-error");
  errorEl.textContent = "";
  try {
    const { payment_id, confirmation_url } = await api("/api/subscribe", { method: "POST" });
    tg?.openLink(confirmation_url);
    pollPaymentStatus(payment_id);
  } catch (e) {
    errorEl.textContent = e.message;
  }
});

async function pollPaymentStatus(paymentId) {
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 4000));
    try {
      const res = await api(`/api/subscribe/${paymentId}/status`);
      if (res.status === "succeeded") {
        await loadMe();
        closeSheets();
        tg?.HapticFeedback?.notificationOccurred("success");
        return;
      }
      if (res.status === "canceled") return;
    } catch (_) {
      // игнорируем разовые ошибки поллинга
    }
  }
}

// --- init ---
(async function init() {
  try {
    await loadMe();
  } catch (e) {
    document.getElementById("empty-state").textContent =
      "Не удалось авторизоваться через Telegram: " + e.message;
    return;
  }
  await loadListings();
})();
