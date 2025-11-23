const API = {
  base: "",

  token: () => localStorage.getItem("token") || "",
  role: () => localStorage.getItem("role") || "",
  login: () => localStorage.getItem("login") || "",
  setAuth(token, role, login){
    localStorage.setItem("token", token);
    localStorage.setItem("role", role);
    localStorage.setItem("login", login);
  },
  clearAuth(){
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("login");
  },
  headers(extra = {}){
    const h = {"Content-Type":"application/json", ...extra};
    const t = API.token();
    if (t) h["Authorization"] = "Bearer " + t;
    return h;
  },

  async req(path, {method="GET", body=null, headers=null}={}){
    const res = await fetch(API.base + path, {
      method,
      headers: headers || API.headers(),
      body: body ? JSON.stringify(body) : null
    });

    let raw = "";
    try { raw = await res.text(); } catch(e){}

    let data = null;
    if (raw) {
      try { data = JSON.parse(raw); }
      catch { data = raw; }
    }

    if (!res.ok) {
      const msg = formatApiError(data) || `HTTP ${res.status}`;
      throw new Error(msg);
    }

    return (data && typeof data === "object") ? data : {};
  }
};

function formatApiError(data){
  if (!data) return null;
  if (typeof data === "string") return data;
  if (data.error && typeof data.error === "string") return data.error;

  const d = data.detail;
  if (typeof d === "string") return d;

  if (Array.isArray(d)) {
    return d.map(err => {
      if (typeof err === "string") return err;
      const loc = Array.isArray(err.loc) ? err.loc.join(".") : (err.loc ?? "");
      const msg = err.msg || err.message || "Ошибка валидации";
      return loc ? `${loc}: ${msg}` : msg;
    }).join("\n");
  }

  if (d && typeof d === "object") {
    return d.msg || d.message || JSON.stringify(d);
  }

  return data.message || null;
}

const PERMISSIONS_CATALOG = [
  { group: "Компания", key: "company.update", title: "Управление компанией", desc: "Менять название, ИНН и общие данные компании." },

  { group: "Сотрудники", key: "users.create", title: "Создание сотрудников", desc: "Добавлять новых работников своей компании." },
  { group: "Сотрудники", key: "users.update", title: "Управление сотрудниками", desc: "Менять должности, права, блокировать/разблокировать." },

  { group: "Склады", key: "warehouses.create", title: "Создание складов", desc: "Создавать новые склады компании." },
  { group: "Склады", key: "warehouses.update", title: "Редактирование складов", desc: "Переименовать склад, менять пороги, email-уведомления." },
  { group: "Склады", key: "warehouses.delete", title: "Удаление складов", desc: "Удалять (мягко) склады компании." },
  { group: "Склады", key: "camera.create_key", title: "Ключ камеры склада", desc: "Смотреть/перегенерировать API-ключ камеры." },

  { group: "Товары", key: "items.create", title: "Добавление товаров", desc: "Создавать новые позиции товаров на складе." },
  { group: "Товары", key: "items.update", title: "Редактирование товаров", desc: "Менять название, категорию, единицы, пороги low-stock." },
  { group: "Товары", key: "items.delete", title: "Удаление товаров", desc: "Удалять товары (мягко) со склада." },
  { group: "Товары", key: "items.op", title: "Операции приход/расход", desc: "Увеличивать/уменьшать остаток товара." },

  { group: "Поставки", key: "supplies.create", title: "Создание поставок", desc: "Планировать будущие поставки." },
  { group: "Поставки", key: "supplies.update", title: "Управление поставками", desc: "Менять статус поставки (waiting/done/canceled)." },
  { group: "Поставки", key: "supplies.delete", title: "Удаление поставок", desc: "Удалять поставки (если добавишь эндпоинт)." },
];

function renderPermsSelector(selected = []) {
  const selectedSet = new Set(selected || []);
  const groups = {};
  for (const p of PERMISSIONS_CATALOG) (groups[p.group] ||= []).push(p);

  return Object.entries(groups).map(([groupName, perms]) => `
    <div class="perm-group">${groupName}</div>
    <div class="perm-list">
      ${perms.map(p => `
        <label class="perm-item">
          <input type="checkbox" class="perm-check" value="${p.key}" ${selectedSet.has(p.key) ? "checked" : ""}/>
          <div class="perm-text">
            <div class="perm-title">${p.title}</div>
            <div class="perm-desc">${p.desc}</div>
            <div class="perm-key">${p.key}</div>
          </div>
        </label>
      `).join("")}
    </div>
  `).join("");
}
function collectSelectedPerms(rootEl=document) {
  return Array.from(rootEl.querySelectorAll(".perm-check:checked")).map(x => x.value);
}

const $  = (q) => document.querySelector(q);
const $$ = (q) => Array.from(document.querySelectorAll(q));
const toastEl = $("#toast");

function toast(msg, type="good"){
  if (!toastEl) return alert(msg);
  const item = document.createElement("div");
  item.className = `toast-item ${type}`;
  item.innerHTML = `<div class="toast-msg"></div><button class="icon-btn">✕</button>`;
  item.querySelector(".toast-msg").textContent = msg;
  item.querySelector("button").onclick = () => item.remove();
  toastEl.appendChild(item);
  setTimeout(() => item.remove(), 3500);
}

const modal = {
  el: $("#modal"),
  title: $("#modalTitle"),
  body: $("#modalBody"),
  footer: $("#modalFooter"),
  open({title, bodyHTML, footerHTML, onMount}){
    if (!modal.el) return;
    modal.title.textContent = title || "Modal";
    modal.body.innerHTML = bodyHTML || "";
    modal.footer.innerHTML = footerHTML || "";
    modal.el.classList.remove("hidden");
    onMount?.(modal.el);
  },
  close(){
    if (!modal.el) return;
    modal.el.classList.add("hidden");
    modal.body.innerHTML = "";
    modal.footer.innerHTML = "";
  }
};
$("#modalClose")?.addEventListener("click", modal.close);
$("#modalBackdrop")?.addEventListener("click", modal.close);

function escapeHtml(s){
  return String(s ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}
function escapeAttr(s){ return escapeHtml(s).replaceAll("\n"," "); }

function debounce(fn, ms=250){
  let t = null;
  return (...args)=>{
    clearTimeout(t);
    t = setTimeout(()=>fn(...args), ms);
  };
}

const views = {
  auth: $("#view-auth"),
  register: $("#view-register"),
  dashboard: $("#view-dashboard"),
  warehouses: $("#view-warehouses"),
  items: $("#view-items"),
  supplies: $("#view-supplies"),
  employees: $("#view-employees"),
  "root-companies": $("#view-root-companies"),
};

function setView(name){
  const token = API.token();
  if (token && (name === "auth" || name === "register")) name = "dashboard";

  if (name === "dashboard" && !views.dashboard) name = "warehouses";

  Object.values(views).forEach(v => v?.classList.add("hidden"));
  views[name]?.classList.remove("hidden");

  $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === name));

  const titleMap = {
    auth: ["Авторизация", "/user/auth"],
    register: ["Регистрация CEO", "/user/register/ceo"],
    dashboard: ["Дашборд", "/dashboard/summary"],
    warehouses: ["Склады", "/warehouse/list"],
    items: ["Товары", "/items/list/{warehouse_id}"],
    supplies: ["Поставки", "/supplies/list/{warehouse_id}"],
    employees: ["Сотрудники", "/company/users/*"],
    "root-companies": ["Компании", "/root/companies/*"],
  };
  $("#pageTitle") && ($("#pageTitle").textContent = titleMap[name]?.[0] || name);
  $("#pageCrumb") && ($("#pageCrumb").textContent = titleMap[name]?.[1] || "");
  if (name === "items") startItemsAutoRefresh();
  else stopItemsAutoRefresh();
}

$$(".nav-item").forEach(btn=>{
  btn.onclick = () => {
    const view = btn.dataset.view;
    setView(view);
    if (view === "dashboard") loadDashboard();
    if (view === "warehouses") loadWarehouses();
    if (view === "items") loadItemsView();
    if (view === "supplies") loadSuppliesView();
    if (view === "employees") loadEmployees();
    if (view === "root-companies") loadRootCompanies();
  };
});

async function doLogin(login, password){
  const data = await API.req("/user/auth", {method:"POST", body:{login, password}});
  if (!data.ok || !data.token) throw new Error("Auth failed");
  API.setAuth(data.token, data.role, login);
  applyRoleUI();
  toast("Успешный вход", "good");
  setView("dashboard");
  loadDashboard();
  loadNotificationsCount(true);
}

$("#btnLogin")?.addEventListener("click", async () => {
  try{
    await doLogin($("#loginLogin").value.trim(), $("#loginPassword").value);
  }catch(e){ toast(e.message, "bad"); }
});
$("#btnLoginDemo")?.addEventListener("click", () => {
  $("#loginLogin").value = "root";
  $("#loginPassword").value = "root_password";
});

$("#btnRegisterCEO")?.addEventListener("click", async () => {
  try{
    const body = {
      company_name: $("#regCompanyName").value.trim(),
      company_inn: $("#regCompanyInn").value.trim() || null,
      login: $("#regLogin").value.trim(),
      password: $("#regPassword").value,
      email: $("#regEmail").value.trim()
    };
    const data = await API.req("/user/register/ceo", {method:"POST", body});
    if (!data.ok || !data.token) throw new Error("Register failed");
    API.setAuth(data.token, "ceo", body.login);
    applyRoleUI();
    toast("CEO зарегистрирован и вошёл", "good");
    setView("dashboard");
    loadDashboard();
    loadNotificationsCount(true);
  }catch(e){ toast(e.message, "bad"); }
});

$("#btnLogout")?.addEventListener("click", () => {
  API.clearAuth();
  applyRoleUI();
  setView("auth");
});

function applyRoleUI(){
  const token = API.token();
  const role = API.role();

  $("#devPill") && ($("#devPill").textContent =
    `DEV = ${window.__DEV__ === undefined ? "—" : String(window.__DEV__)}`);

  $("#navGuest")?.classList.toggle("hidden", !!token);
  $("#navAuthed")?.classList.toggle("hidden", !token);
  $("#btnLogout")?.classList.toggle("hidden", !token);
  $("#userMini")?.classList.toggle("hidden", !token);

  $("#miniLogin") && ($("#miniLogin").textContent = API.login() || "—");
  $("#miniRole") && ($("#miniRole").textContent = role || "—");

  $("#navEmployees")?.classList.toggle("hidden", !(role==="ceo" || role==="root"));
  $("#navRootCompanies")?.classList.toggle("hidden", role!=="root");
}

let warehousesCache = [];
let currentWarehouseId = null;

async function loadWarehouses(){
  try{
    const data = await API.req("/warehouse/list");
    warehousesCache = data.warehouses || [];
    renderWarehouses(warehousesCache);
    fillWarehouseSelects();
  }catch(e){ toast(e.message, "bad"); }
}

function renderWarehouses(list){
  const grid = $("#warehousesGrid");
  if (!grid) return;
  grid.innerHTML = "";

  if (!list.length){
    grid.innerHTML = `<div class="card muted">Складов пока нет. Создай первый 🙂</div>`;
    return;
  }

  const role = API.role();

  list.forEach(w=>{
    const blocked = !!w.blocked_at;

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700; font-size:16px">${escapeHtml(w.name)}</div>
        <div class="row" style="gap:6px">
          <span class="badge ${blocked?"bad":"good"}">${blocked?"blocked":"active"}</span>
          <span class="badge">${w.id.slice(-6)}</span>
        </div>
      </div>

      <div class="kv">
        <div class="k">Камера API key</div>
        <div class="v mono">${escapeHtml(w.camera_api_key || "—")}</div>
      </div>
      <div class="kv">
        <div class="k">Email уведомлений</div>
        <div class="v">${(w.notification_emails||[]).map(escapeHtml).join(", ") || "—"}</div>
      </div>

      <div class="sep"></div>
      <div class="row">
        <button class="btn btn-small btn-ghost" data-open-items="${w.id}">Товары</button>
        <button class="btn btn-small btn-ghost" data-open-supplies="${w.id}">Поставки</button>
        ${role==="root" ? `<button class="btn btn-small btn-ghost" data-block="${w.id}">${blocked?"Разблок":"Блок"}</button>` : ""}
        <button class="btn btn-small btn-danger" data-delete="${w.id}">Удалить</button>
      </div>
    `;
    grid.appendChild(card);

    card.querySelector("[data-open-items]").onclick = () => {
      currentWarehouseId = w.id;
      setView("items");
      $("#itemsWarehouseSelect") && ($("#itemsWarehouseSelect").value = w.id);
      loadItemsView();
    };

    card.querySelector("[data-open-supplies]").onclick = () => {
      currentWarehouseId = w.id;
      setView("supplies");
      $("#suppliesWarehouseSelect") && ($("#suppliesWarehouseSelect").value = w.id);
      loadSuppliesView();
    };

    card.querySelector("[data-delete]").onclick = async () => {
      if (!confirm(`Удалить склад "${w.name}"?`)) return;
      try{
        await API.req(`/warehouse/delete/${w.id}`, {method:"DELETE"});
        toast("Склад удалён", "good");
        loadWarehouses();
        loadDashboard();
      }catch(e){ toast(e.message, "bad"); }
    };

    const blockBtn = card.querySelector("[data-block]");
    if (blockBtn){
      blockBtn.onclick = async () => {
        try{
          await API.req(`/warehouse/${blocked ? "unblock" : "block"}/${w.id}`, {method:"POST"});
          toast(blocked ? "Склад разблокирован" : "Склад заблокирован", "good");
          loadWarehouses();
          loadDashboard();
        }catch(e){ toast(e.message,"bad"); }
      };
    }
  });
}

$("#btnWarehouseCreate")?.addEventListener("click", () => {
  modal.open({
    title: "Создать склад",
    bodyHTML: `
      <label class="label">Название</label>
      <input class="input" id="mWhName" placeholder="Склад №1"/>
      <label class="label">Emails уведомлений (через запятую)</label>
      <input class="input" id="mWhEmails" placeholder="a@b.ru, c@d.ru"/>
      <label class="label">Порог low-stock по умолчанию</label>
      <input class="input" id="mWhLow" type="number" min="0" value="1"/>
    `,
    footerHTML: `
      <button class="btn btn-ghost" id="mCancel">Отмена</button>
      <button class="btn" id="mOk">Создать</button>
    `,
    onMount: () => {
      $("#mCancel").onclick = modal.close;
      $("#mOk").onclick = async () => {
        try{
          const name = $("#mWhName").value.trim();
          const emails = $("#mWhEmails").value.split(",").map(x=>x.trim()).filter(Boolean);
          const low = parseInt($("#mWhLow").value || "1", 10);

          await API.req("/warehouse/create", {
            method:"POST",
            body:{name, notification_emails: emails, low_stock_default: low}
          });
          modal.close();
          toast("Склад создан", "good");
          loadWarehouses();
          loadDashboard();
        }catch(e){ toast(e.message, "bad"); }
      };
    }
  });
});

$("#warehouseSearch")?.addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  renderWarehouses(
    warehousesCache.filter(w => w.name.toLowerCase().includes(q))
  );
});

function fillWarehouseSelects(){
  const selects = [$("#itemsWarehouseSelect"), $("#suppliesWarehouseSelect")].filter(Boolean);
  selects.forEach(sel=>{
    sel.innerHTML = "";
    warehousesCache.forEach(w=>{
      const opt = document.createElement("option");
      opt.value = w.id;
      opt.textContent = w.name;
      sel.appendChild(opt);
    });
  });

  if (!currentWarehouseId && warehousesCache[0]) currentWarehouseId = warehousesCache[0].id;
  if (currentWarehouseId){
    $("#itemsWarehouseSelect") && ($("#itemsWarehouseSelect").value = currentWarehouseId);
    $("#suppliesWarehouseSelect") && ($("#suppliesWarehouseSelect").value = currentWarehouseId);
  }
}

let itemsCache = [];
let itemsAutoTimer = null;
let itemsInFlight = false;
let itemsById = new Map();

function startItemsAutoRefresh(){
  stopItemsAutoRefresh(); // на всякий случай

  itemsAutoTimer = setInterval(() => {
    if (!views.items || views.items.classList.contains("hidden")) return;

    if (itemsInFlight) return;

    if (document.hidden) return;

    loadItemsView({ silent: true });
  }, 2000);
}

function stopItemsAutoRefresh(){
  if (itemsAutoTimer){
    clearInterval(itemsAutoTimer);
    itemsAutoTimer = null;
  }
}

function fillItemsCategorySelect(){
  const sel = $("#itemsCategorySelect");
  if (!sel) return;
  const cats = Array.from(new Set(itemsCache.map(i=>i.category||"other"))).sort();
  const cur = sel.value;
  sel.innerHTML = `<option value="">все категории</option>` +
    cats.map(c=>`<option value="${escapeAttr(c)}">${escapeHtml(c)}</option>`).join("");
  if (cats.includes(cur)) sel.value = cur;
}

async function loadItemsView({ silent = false } = {}){
  if (!warehousesCache.length){
    await loadWarehouses();
    if (!warehousesCache.length) return;
  }
  const wid = $("#itemsWarehouseSelect")?.value || currentWarehouseId;
  if (!wid) return;
  currentWarehouseId = wid;

  const search   = $("#itemsSearch")?.value?.trim() || "";
  const category = $("#itemsCategorySelect")?.value || "";
  const sort     = $("#itemsSortSelect")?.value || "";
  const order    = $("#itemsOrderSelect")?.value || "";
  const low_only = $("#itemsLowOnly")?.checked || false;

  const qs = new URLSearchParams();
  if (search) qs.set("search", search);
  if (category) qs.set("category", category);
  if (sort) qs.set("sort", sort);
  if (order) qs.set("order", order);
  if (low_only) qs.set("low_only", "true");

  try{
    itemsInFlight = true;

    const data = await API.req(`/items/list/${wid}` + (qs.toString() ? `?${qs}` : ""));
    itemsCache = data.items || [];
    itemsById = new Map(itemsCache.map(i => [i.id, i]));
    fillItemsCategorySelect();
    renderItems(itemsCache);

  }catch(e){
    if (!silent) toast(e.message, "bad");
  }finally{
    itemsInFlight = false;
  }
}

$("#itemsWarehouseSelect")?.addEventListener("change", loadItemsView);

const debouncedItemsReload = debounce(loadItemsView, 250);
$("#itemsSearch")?.addEventListener("input", debouncedItemsReload);
$("#itemsCategorySelect")?.addEventListener("change", loadItemsView);
$("#itemsSortSelect")?.addEventListener("change", loadItemsView);
$("#itemsOrderSelect")?.addEventListener("change", loadItemsView);
$("#itemsLowOnly")?.addEventListener("change", loadItemsView);

function itemLowBadge(i, wh){
  const low = i.low_limit ?? wh.low_stock_default ?? 1;
  if (i.count <= low) return `<span class="badge bad">low ≤ ${low}</span>`;
  if (i.count <= low*2) return `<span class="badge warn">warn</span>`;
  return `<span class="badge good">ok</span>`;
}

function renderItems(list){
  const grid = $("#itemsGrid");
  if (!grid) return;
  grid.innerHTML = "";

  const wh = warehousesCache.find(w=>w.id===currentWarehouseId) || {};

  if (!list.length){
    grid.innerHTML = `<div class="card muted">Товаров нет. Добавь первый 🙂</div>`;
    return;
  }

  list.forEach(i=>{
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700; font-size:16px">${escapeHtml(i.name)}</div>
        ${itemLowBadge(i, wh)}
      </div>
      <div class="kv">
        <div class="k">Категория</div>
        <div class="v">${escapeHtml(i.category || "other")}</div>
      </div>
      <div class="kv">
        <div class="k">Остаток</div>
        <div class="v" style="font-size:18px">${i.count} ${escapeHtml(i.unit||"шт")}</div>
      </div>

      <div class="sep"></div>
      <div class="row">
        <button class="btn btn-small btn-ghost" data-income="${i.id}">+ Приход</button>
        <button class="btn btn-small btn-ghost" data-outcome="${i.id}">- Расход</button>
        <button class="btn btn-small btn-ghost" data-history="${i.id}">История</button>
      </div>
    `;
    grid.appendChild(card);

    card.querySelector("[data-income]").onclick = () => openItemOp(i, "income");
    card.querySelector("[data-outcome]").onclick = () => openItemOp(i, "outcome");
    card.querySelector("[data-history]").onclick = () => openHistory(i.id);
  });
}

$("#btnItemCreate")?.addEventListener("click", () => {
  const wid = currentWarehouseId || $("#itemsWarehouseSelect")?.value;
  if (!wid) return toast("Сначала выбери склад", "bad");

  modal.open({
    title: "Добавить товар",
    bodyHTML: `
      <label class="label">Название</label>
      <input class="input" id="mItemName" placeholder="Шоколад"/>
      <label class="label">Категория</label>
      <input class="input" id="mItemCat" placeholder="еда"/>
      <label class="label">Ед. измерения</label>
      <input class="input" id="mItemUnit" placeholder="шт"/>
      <label class="label">Начальный остаток</label>
      <input class="input" id="mItemCount" type="number" min="0" value="0"/>
      <label class="label">Порог low-stock (опц.)</label>
      <input class="input" id="mItemLow" type="number" min="0" placeholder="например 2"/>
    `,
    footerHTML: `
      <button class="btn btn-ghost" id="mCancel">Отмена</button>
      <button class="btn" id="mOk">Создать</button>
    `,
    onMount: ()=>{
      $("#mCancel").onclick = modal.close;
      $("#mOk").onclick = async ()=>{
        try{
          const body = {
            warehouse_id: wid,
            name: $("#mItemName").value.trim(),
            category: $("#mItemCat").value.trim() || "other",
            unit: $("#mItemUnit").value.trim() || "шт",
            count: parseInt($("#mItemCount").value||"0",10),
            low_limit: $("#mItemLow").value ? parseInt($("#mItemLow").value,10) : null
          };
          await API.req("/items/create", {method:"POST", body});
          modal.close();
          toast("Товар добавлен", "good");
          loadItemsView();
          loadDashboard();
          loadNotificationsCount();
        }catch(e){ toast(e.message, "bad"); }
      };
    }
  });
});

async function openItemOp(item, type){
  modal.open({
    title: type==="income" ? "Приход" : "Расход",
    bodyHTML: `
      <div class="muted">${escapeHtml(item.name)}</div>
      <label class="label">Количество</label>
      <input class="input" id="mOpAmount" type="number" min="1" value="1"/>
    `,
    footerHTML: `
      <button class="btn btn-ghost" id="mCancel">Отмена</button>
      <button class="btn" id="mOk">Подтвердить</button>
    `,
    onMount: ()=>{
      $("#mCancel").onclick = modal.close;
      $("#mOk").onclick = async ()=>{
        try{
          const amount = parseInt($("#mOpAmount").value||"1",10);
          await API.req(`/items/${type}`, {method:"POST", body:{item_id:item.id, amount}});
          modal.close();
          toast("Операция выполнена", "good");
          loadItemsView();
          loadDashboard();
          loadNotificationsCount();
        }catch(e){ toast(e.message, "bad"); }
      };
    }
  });
}

async function openHistory(itemId){
  try{
    const data = await API.req(`/items/history/${itemId}`);
    const h = data.history || [];
    modal.open({
      title: "История операций",
      bodyHTML: h.length ? h.map(x=>`
        <div class="card" style="background:var(--card-2)">
          <div class="row">
            <div>${escapeHtml(x.type)}</div>
            <div class="muted">${new Date(x.ts).toLocaleString()}</div>
          </div>
          <div class="kv">
            <div class="k">amount</div>
            <div class="v">${x.amount}</div>
          </div>
          ${x.note ? `<div class="muted">${escapeHtml(x.note)}</div>`:""}
        </div>
      `).join("") : `<div class="muted">Пока пусто</div>`,
      footerHTML:`<button class="btn btn-ghost" id="mOk">Закрыть</button>`,
      onMount: ()=> $("#mOk").onclick = modal.close
    });
  }catch(e){ toast(e.message,"bad"); }
}

$("#btnLowStock")?.addEventListener("click", async ()=>{
  try{
    const wid = currentWarehouseId;
    const data = await API.req(`/items/low_stock/${wid}`);
    const items = data.items || [];
    modal.open({
      title: "Низкий остаток",
      bodyHTML: items.length ? items.map(i=>`
        <div class="row">
          <div>${escapeHtml(i.name)}</div>
          <div><b>${i.count}</b> ${escapeHtml(i.unit||"шт")}</div>
        </div>
      `).join("<div class='sep'></div>") : `<div class="muted">Всё ок 🙂</div>`,
      footerHTML:`<button class="btn btn-ghost" id="mOk">Закрыть</button>`,
      onMount: ()=> $("#mOk").onclick = modal.close
    });
  }catch(e){ toast(e.message,"bad"); }
});

$("#btnWarehouseHistory")?.addEventListener("click", ()=> openWarehouseHistory(currentWarehouseId));
async function openWarehouseHistory(wid){
  if(!wid) return;
  try{
    const data = await API.req(`/items/history/warehouse/${wid}?limit=200`);
    const h = data.history || [];
    modal.open({
      title: "История склада",
      bodyHTML: h.length ? h.map(x=>`
        <div class="card" style="background:var(--card-2)">
          <div class="row">
            <div><b>${escapeHtml(x.item_name||"—")}</b></div>
            <div class="muted">${new Date(x.ts).toLocaleString()}</div>
          </div>
          <div class="row">
            <div class="muted">${escapeHtml(x.type)}</div>
            <div>${x.amount}</div>
          </div>
          ${x.note ? `<div class="muted">${escapeHtml(x.note)}</div>`:""}
        </div>
      `).join("") : `<div class="muted">Пока пусто</div>`,
      footerHTML:`<button class="btn btn-ghost" id="mOk">Закрыть</button>`,
      onMount: ()=> $("#mOk").onclick = modal.close
    });
  }catch(e){ toast(e.message,"bad"); }
}

async function downloadWithAuth(path, filename){
  try{
    const res = await fetch(API.base + path, { headers: API.headers({"Accept":"*/*"}) });
    if(!res.ok){
      const raw = await res.text();
      let msg = raw;
      try{ msg = formatApiError(JSON.parse(raw)); }catch{}
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "export.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }catch(e){
    toast(e.message, "bad");
  }
}

$("#btnItemsExport")?.addEventListener("click", ()=>{
  const wid = currentWarehouseId;
  if(!wid) return toast("Выбери склад", "bad");
  downloadWithAuth(`/export/items/${wid}`, `items_${wid}.csv`);
});
$("#btnSuppliesExport")?.addEventListener("click", ()=>{
  const wid = currentWarehouseId;
  if(!wid) return toast("Выбери склад", "bad");
  downloadWithAuth(`/export/supplies/${wid}`, `supplies_${wid}.csv`);
});

let suppliesCache = [];

function computeOverdue(s){
  if (typeof s.overdue === "boolean") return s.overdue;
  if (s.status && s.status !== "waiting") return false;
  const t = Date.parse(s.expected_at);
  if (Number.isNaN(t)) return false;
  return t < Date.now();
}

async function ensureItemsForWarehouse(wid){
  if (!wid) return;
  if (itemsCache.length && currentWarehouseId === wid) return;
  try{
    const data = await API.req(`/items/list/${wid}`);
    itemsCache = data.items || [];
    itemsById = new Map(itemsCache.map(i => [i.id, i]));
  }catch(e){}
}

async function loadSuppliesView(){
  if (!warehousesCache.length){
    await loadWarehouses();
    if (!warehousesCache.length) return;
  }
  const wid = $("#suppliesWarehouseSelect")?.value || currentWarehouseId;
  if (!wid) return;
  currentWarehouseId = wid;

  const status = $("#suppliesStatusSelect")?.value || "";
  const search = $("#suppliesSearch")?.value?.trim() || "";
  const sort   = $("#suppliesSortSelect")?.value || "";
  const order  = $("#suppliesOrderSelect")?.value || "";
  const overdueOnly = $("#suppliesOverdueOnly")?.checked || false;

  const qs = new URLSearchParams();
  if (status) qs.set("status", status);
  if (search) qs.set("search", search);
  if (sort) qs.set("sort", sort);
  if (order) qs.set("order", order);

  try{
    const data = await API.req(`/supplies/list/${wid}` + (qs.toString() ? `?${qs}` : ""));
    suppliesCache = (data.supplies || []).map(s => ({...s, overdue: computeOverdue(s)}));

    if (suppliesCache.some(s=>!s.item_name)){
      await ensureItemsForWarehouse(wid);
      suppliesCache = suppliesCache.map(s=>{
        const it = itemsById.get(s.item_id);
        return {...s, item_name: s.item_name || it?.name || null};
      });
    }

    if (overdueOnly) suppliesCache = suppliesCache.filter(s=>s.overdue);

    renderSupplies(suppliesCache);
  }catch(e){ toast(e.message, "bad"); }
}

$("#suppliesWarehouseSelect")?.addEventListener("change", loadSuppliesView);
$("#suppliesStatusSelect")?.addEventListener("change", loadSuppliesView);
$("#suppliesSortSelect")?.addEventListener("change", loadSuppliesView);
$("#suppliesOrderSelect")?.addEventListener("change", loadSuppliesView);
$("#suppliesOverdueOnly")?.addEventListener("change", loadSuppliesView);
$("#suppliesSearch")?.addEventListener("input", debounce(loadSuppliesView, 250));

function renderSupplies(list){
  const grid = $("#suppliesGrid");
  if (!grid) return;
  grid.innerHTML = "";

  if (!list.length){
    grid.innerHTML = `<div class="card muted">Поставок нет.</div>`;
    return;
  }

  list.forEach(s=>{
    const statusBadge =
      s.status==="done" ? "good" :
      s.status==="canceled" ? "bad" : "warn";

    const overdueBadge = s.overdue ? `<span class="badge bad">overdue</span>` : "";

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700">
          ${escapeHtml(s.item_name || s.item_id?.slice(-6) || "item")}
        </div>
        <div class="row" style="gap:6px">
          ${overdueBadge}
          <span class="badge ${statusBadge}">${escapeHtml(s.status)}</span>
        </div>
      </div>
      <div class="kv">
        <div class="k">Кол-во</div>
        <div class="v">${s.amount}</div>
      </div>
      <div class="kv">
        <div class="k">Ожидается</div>
        <div class="v">${new Date(s.expected_at).toLocaleString()}</div>
      </div>
      ${s.note ? `<div class="muted">${escapeHtml(s.note)}</div>`:""}

      <div class="sep"></div>
      <div class="row">
        <button class="btn btn-small btn-ghost" data-status="waiting">waiting</button>
        <button class="btn btn-small btn-ghost" data-status="done">done</button>
        <button class="btn btn-small btn-ghost" data-status="canceled">canceled</button>
      </div>
    `;
    grid.appendChild(card);

    card.querySelectorAll("[data-status]").forEach(b=>{
      b.onclick = async ()=>{
        try{
          await API.req("/supplies/status", {
            method:"POST",
            body:{supply_id:s.id, status:b.dataset.status}
          });
          toast("Статус обновлён", "good");
          loadSuppliesView();
          loadItemsView();
          loadDashboard();
          loadNotificationsCount();
        }catch(e){ toast(e.message,"bad"); }
      };
    });
  });
}

$("#btnSupplyCreate")?.addEventListener("click", async ()=>{
  const wid = currentWarehouseId || $("#suppliesWarehouseSelect")?.value;
  if(!wid){
    toast("Сначала выбери склад", "bad");
    return;
  }

  let items = [];
  try{
    const data = await API.req(`/items/list/${wid}`);
    items = data.items || [];
  }catch(e){ toast(e.message, "bad"); return; }

  modal.open({
    title: "Запланировать поставку",
    bodyHTML: `
      <label class="label">Товар</label>
      <select class="select" id="mSupItem">
        ${items.map(i=>`<option value="${i.id}">${escapeHtml(i.name)}</option>`).join("")}
      </select>
      <label class="label">Количество</label>
      <input class="input" id="mSupAmount" type="number" min="1" value="1"/>
      <label class="label">Дата/время поставки</label>
      <input class="input" id="mSupDate" type="datetime-local"/>
      <label class="label">Комментарий (опц.)</label>
      <input class="input" id="mSupNote" placeholder="поставка от поставщика №2"/>
    `,
    footerHTML: `
      <button class="btn btn-ghost" id="mCancel">Отмена</button>
      <button class="btn" id="mOk">Создать</button>
    `,
    onMount: ()=>{
      $("#mCancel").onclick = modal.close;
      $("#mOk").onclick = async ()=>{
        try{
          const expected_at = $("#mSupDate").value;
          if (!expected_at) throw new Error("Укажи дату поставки");
          const body = {
            warehouse_id: wid,
            item_id: $("#mSupItem").value,
            amount: parseInt($("#mSupAmount").value||"1",10),
            expected_at: new Date(expected_at).toISOString(),
            note: $("#mSupNote").value.trim() || null
          };
          await API.req("/supplies/create", {method:"POST", body});
          modal.close();
          toast("Поставка создана", "good");
          loadSuppliesView();
          loadDashboard();
          loadNotificationsCount();
        }catch(e){ toast(e.message,"bad"); }
      };
    }
  });
});

async function loadEmployees(){
  try{
    const data = await API.req("/company/users/list");
    renderEmployees(data.users || []);
  }catch(e){ toast(e.message,"bad"); }
}

function renderEmployees(list){
  const grid = $("#employeesGrid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!list.length){
    grid.innerHTML = `<div class="card muted">Сотрудников нет.</div>`;
    return;
  }

  const role = API.role();
  const canManage = (role === "ceo" || role === "root");

  list.forEach(u=>{
    const card = document.createElement("div");
    card.className = "card";
    const blocked = !!u.blocked_at;

    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700">${escapeHtml(u.login)}</div>
        <span class="badge ${blocked?"bad":"good"}">${blocked?"blocked":"active"}</span>
      </div>
      <div class="kv">
        <div class="k">Должность</div>
        <div class="v">${escapeHtml(u.post||"—")}</div>
      </div>
      <div class="kv">
        <div class="k">Permissions</div>
        <div class="v mono" style="font-size:12px">${(u.permissions||[]).map(escapeHtml).join(", ")||"—"}</div>
      </div>
      <div class="sep"></div>
      <div class="row">
        <button class="btn btn-small btn-ghost" data-edit="${u.id}">Редактировать</button>
        ${canManage ? `<button class="btn btn-small btn-ghost" data-block="${u.id}">${blocked?"Разблок":"Блок"}</button>` : ""}
        ${canManage ? `<button class="btn btn-small btn-danger" data-delete="${u.id}">Удалить</button>` : ""}
      </div>
    `;
    grid.appendChild(card);

    card.querySelector("[data-edit]").onclick = () => openEmployeeEdit(u);

    const blockBtn = card.querySelector("[data-block]");
    if (blockBtn){
      blockBtn.onclick = async ()=>{
        try{
          await API.req("/company/users/update", {
            method:"POST",
            body:{user_id:u.id, blocked: !blocked}
          });
          toast(blocked ? "Сотрудник разблокирован" : "Сотрудник заблокирован", "good");
          loadEmployees();
        }catch(e){ toast(e.message,"bad"); }
      };
    }

    const delBtn = card.querySelector("[data-delete]");
    if (delBtn){
      delBtn.onclick = async ()=>{
        if (!confirm(`Удалить сотрудника "${u.login}"?`)) return;
        try{
          await API.req(`/company/users/delete/${u.id}`, {method:"DELETE"});
          toast("Сотрудник удалён", "good");
          loadEmployees();
        }catch(e){ toast(e.message,"bad"); }
      };
    }
  });
}

$("#btnEmployeeCreate")?.addEventListener("click", ()=>{
  modal.open({
    title: "Создать сотрудника",
    bodyHTML: `
      <label class="label">Логин</label>
      <input class="input" id="mEmpLogin"/>
      <label class="label">Пароль</label>
      <input class="input" id="mEmpPass" type="password"/>
      <label class="label">Email</label>
      <input class="input" id="mEmpEmail"/>
      <label class="label">Должность</label>
      <input class="input" id="mEmpPost" placeholder="кладовщик"/>

      <div class="sep"></div>
      <label class="label">Права сотрудника</label>
      <div class="perms-scroll">
        ${renderPermsSelector([])}
      </div>
    `,
    footerHTML: `
      <button class="btn btn-ghost" id="mCancel">Отмена</button>
      <button class="btn" id="mOk">Создать</button>
    `,
    onMount: ()=>{
      $("#mCancel").onclick = modal.close;
      $("#mOk").onclick = async ()=>{
        try{
          const body = {
            login: $("#mEmpLogin").value.trim(),
            password: $("#mEmpPass").value,
            email: $("#mEmpEmail").value.trim(),
            post: $("#mEmpPost").value.trim(),
            permissions: collectSelectedPerms(modal.el),
          };
          await API.req("/company/users/create", {method:"POST", body});
          modal.close();
          toast("Сотрудник создан", "good");
          loadEmployees();
        }catch(e){ toast(e.message,"bad"); }
      };
    }
  });
});

function openEmployeeEdit(u){
  modal.open({
    title: `Редактировать ${u.login}`,
    bodyHTML: `
      <label class="label">Должность</label>
      <input class="input" id="mEmpPost" value="${escapeAttr(u.post||"")}"/>

      <div class="sep"></div>
      <label class="label">Права сотрудника</label>
      <div class="perms-scroll">
        ${renderPermsSelector(u.permissions || [])}
      </div>

      <div class="sep"></div>
      <label class="label">Блокировка</label>
      <select class="select" id="mEmpBlocked">
        <option value="false" ${u.blocked_at? "" : "selected"}>active</option>
        <option value="true" ${u.blocked_at? "selected" : ""}>blocked</option>
      </select>
    `,
    footerHTML: `
      <button class="btn btn-ghost" id="mCancel">Отмена</button>
      <button class="btn" id="mOk">Сохранить</button>
    `,
    onMount: ()=>{
      $("#mCancel").onclick = modal.close;
      $("#mOk").onclick = async ()=>{
        try{
          const body = {
            user_id: u.id,
            post: $("#mEmpPost").value.trim(),
            permissions: collectSelectedPerms(modal.el),
            blocked: $("#mEmpBlocked").value === "true"
          };
          await API.req("/company/users/update", {method:"POST", body});
          modal.close();
          toast("Сохранено", "good");
          loadEmployees();
        }catch(e){ toast(e.message,"bad"); }
      };
    }
  });
}

async function loadRootCompanies(){
  try{
    const data = await API.req("/root/companies/list");
    renderRootCompanies(data.companies || []);
  }catch(e){ toast(e.message, "bad"); }
}
$("#btnRootRefresh")?.addEventListener("click", loadRootCompanies);

function renderRootCompanies(list){
  const grid = $("#rootCompaniesGrid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!list.length){
    grid.innerHTML = `<div class="card muted">Компаний нет.</div>`;
    return;
  }
  list.forEach(c=>{
    const blocked = !!c.blocked_at;
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700">${escapeHtml(c.name)}</div>
        <span class="badge ${blocked?"bad":"good"}">${blocked?"blocked":"active"}</span>
      </div>
      <div class="kv">
        <div class="k">INN</div>
        <div class="v">${escapeHtml(c.inn || "—")}</div>
      </div>
      <div class="sep"></div>
      <div class="row">
        <button class="btn btn-small btn-ghost" data-block>${blocked?"Разблок":"Блок"}</button>
        <button class="btn btn-small btn-danger" data-del>Удалить</button>
      </div>
    `;
    grid.appendChild(card);

    card.querySelector("[data-block]").onclick = async ()=>{
      try{
        await API.req(`/root/companies/${blocked?"unblock":"block"}/${c.id}`, {method:"POST"});
        toast("Ок", "good");
        loadRootCompanies();
      }catch(e){ toast(e.message,"bad"); }
    };

    card.querySelector("[data-del]").onclick = async ()=>{
      if (!confirm(`Удалить компанию "${c.name}"?`)) return;
      try{
        await API.req(`/root/companies/delete/${c.id}`, {method:"DELETE"});
        toast("Компания удалена", "good");
        loadRootCompanies();
      }catch(e){ toast(e.message,"bad"); }
    };
  });
}

async function loadDashboard(){
  if (!views.dashboard) return;
  try{
    const data = await API.req("/dashboard/summary");
    const s = data.summary || {};

    const grid = $("#dashGrid");
    if (grid){
      grid.innerHTML = `
        <div class="card">
          <div class="muted">Складов</div>
          <div style="font-size:26px;font-weight:800">${s.warehouses||0}</div>
        </div>
        <div class="card">
          <div class="muted">Товарных позиций</div>
          <div style="font-size:26px;font-weight:800">${s.total_items||0}</div>
        </div>
        <div class="card">
          <div class="muted">Низкий остаток</div>
          <div style="font-size:26px;font-weight:800;color:var(--bad)">${s.low_items||0}</div>
        </div>
        <div class="card">
          <div class="muted">Поставок waiting</div>
          <div style="font-size:26px;font-weight:800">${s.supplies?.waiting||0}</div>
          <div class="muted" style="margin-top:6px">overdue: <b style="color:var(--bad)">${s.supplies?.overdue||0}</b></div>
        </div>
      `;
    }

    const up = s.upcoming_supplies || [];
    const elUp = $("#dashUpcoming");
    if (elUp){
      elUp.innerHTML = up.length ? up.map(x=>`
        <div class="row" style="padding:6px 0">
          <div>
            <b>${escapeHtml(x.item_name||"—")}</b>
            <div class="muted" style="font-size:12px">${x.amount} ${escapeHtml(x.unit||"шт")}</div>
          </div>
          <div class="row" style="gap:6px">
            ${x.overdue ? `<span class="badge bad">overdue</span>`:""}
            <span class="muted">${new Date(x.expected_at).toLocaleString()}</span>
          </div>
        </div>
      `).join("<div class='sep'></div>") : `<div class="muted">Поставок пока нет</div>`;
    }

  }catch(e){
    toast(e.message,"bad");
  }
}

let notificationsCache = [];
let lastNotifCount = 0;

async function loadNotificationsCount(showToastOnNew=false){
  if(!API.token()) return;
  try{
    const data = await API.req("/notifications/list?unread_only=true&limit=200");
    notificationsCache = data.notifications || [];
    const count = notificationsCache.length;

    const elCount = $("#notifsCount");
    if (elCount) elCount.textContent = String(count);

    if (showToastOnNew && count > lastNotifCount){
      const diff = count - lastNotifCount;
      toast(`Новых уведомлений: ${diff}`, "good");
    }
    lastNotifCount = count;
  }catch(e){
    $("#notifsCount") && ($("#notifsCount").textContent = "0");
    lastNotifCount = 0;
  }
}

async function openNotifications(){
  await loadNotificationsCount(false);
  const list = notificationsCache;

  modal.open({
    title: "Уведомления",
    bodyHTML: list.length ? list.map(n=>`
      <div class="notif-item ${n.read ? "" : "unread"}" data-id="${n.id}">
        <div class="row">
          <div style="font-weight:700">${escapeHtml(n.title||"—")}</div>
          <div class="muted" style="font-size:12px">${new Date(n.created_at).toLocaleString()}</div>
        </div>
        <div class="muted">${escapeHtml(n.message||"")}</div>
        ${n.type ? `<div class="mono muted" style="font-size:11px">${escapeHtml(n.type)}</div>`:""}
      </div>
    `).join("") : `<div class="muted">Пока пусто 🙂</div>`,
    footerHTML:`<button class="btn btn-ghost" id="mOk">Закрыть</button>`,
    onMount: (el)=>{
      $("#mOk").onclick = modal.close;
      el.querySelectorAll(".notif-item.unread").forEach(card=>{
        card.onclick = async ()=>{
          const id = card.dataset.id;
          try{
            await API.req(`/notifications/read/${id}`, {method:"POST"});
            card.classList.remove("unread");
            await loadNotificationsCount(false);
          }catch(e){}
        };
      });
    }
  });
}

$("#btnNotifs")?.addEventListener("click", openNotifications);

(async function boot(){
  try{
    const meta = await API.req("/meta");
    window.__DEV__ = !!meta.dev;
  }catch(e){
    window.__DEV__ = true;
  }

  applyRoleUI();

  if (API.token()){
    setView("dashboard");
    loadDashboard();
    loadWarehouses();
    loadNotificationsCount(false);
  } else {
    setView("auth");
  }

  if (!views.items?.classList.contains("hidden")) startItemsAutoRefresh();
  setInterval(()=>loadNotificationsCount(true), 30000);
})();