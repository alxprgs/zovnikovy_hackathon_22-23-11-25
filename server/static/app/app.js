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
  headers(){
    const h = {"Content-Type":"application/json"};
    const t = API.token();
    if (t) h["Authorization"] = "Bearer " + t;
    return h;
  },
  async req(path, {method="GET", body=null}={}){
    const res = await fetch(API.base + path, {
      method,
      headers: API.headers(),
      body: body ? JSON.stringify(body) : null
    });
    let data = null;
    try{ data = await res.json(); } catch(e){}
    if (!res.ok) {
      throw new Error(data?.error || data?.detail || `HTTP ${res.status}`);
    }
    return data ?? {};
  }
};

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
  for (const p of PERMISSIONS_CATALOG) {
    (groups[p.group] ||= []).push(p);
  }

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


const $ = (q) => document.querySelector(q);
const $$ = (q) => Array.from(document.querySelectorAll(q));
const toastEl = $("#toast");

function toast(msg, type="good"){
  const item = document.createElement("div");
  item.className = `toast-item ${type}`;
  item.innerHTML = `<div>${msg}</div><button class="icon-btn">✕</button>`;
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
    modal.title.textContent = title || "Modal";
    modal.body.innerHTML = bodyHTML || "";
    modal.footer.innerHTML = footerHTML || "";
    modal.el.classList.remove("hidden");
    onMount?.(modal.el);
  },
  close(){
    modal.el.classList.add("hidden");
    modal.body.innerHTML = "";
    modal.footer.innerHTML = "";
  }
};
$("#modalClose").onclick = modal.close;
$("#modalBackdrop").onclick = modal.close;


const views = {
  auth: $("#view-auth"),
  register: $("#view-register"),
  warehouses: $("#view-warehouses"),
  items: $("#view-items"),
  supplies: $("#view-supplies"),
  employees: $("#view-employees"),
  "root-companies": $("#view-root-companies"),
};

function setView(name){
  if (API.token() && (name === "auth" || name === "register")) {
    name = "warehouses";
  }
  Object.values(views).forEach(v => v.classList.add("hidden"));
  views[name]?.classList.remove("hidden");

  $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === name));

  const titleMap = {
    auth: ["Авторизация", "/user/auth"],
    register: ["Регистрация CEO", "/user/register/ceo"],
    warehouses: ["Склады", "/warehouse/list"],
    items: ["Товары", "/items/list/{warehouse_id}"],
    supplies: ["Поставки", "/supplies/list/{warehouse_id}"],
    employees: ["Сотрудники", "/company/users/*"],
    "root-companies": ["Компании", "/root/companies/*"],
  };
  $("#pageTitle").textContent = titleMap[name]?.[0] || name;
  $("#pageCrumb").textContent = titleMap[name]?.[1] || "";
}

$$(".nav-item").forEach(btn=>{
  btn.onclick = () => {
    const view = btn.dataset.view;
    setView(view);
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
  setView("warehouses");
  loadWarehouses();
}

$("#btnLogin").onclick = async () => {
  try{
    await doLogin($("#loginLogin").value.trim(), $("#loginPassword").value);
  }catch(e){ toast(e.message, "bad"); }
};

$("#btnLoginDemo").onclick = () => {
  $("#loginLogin").value = "root";
  $("#loginPassword").value = "root_password";
};

$("#btnRegisterCEO").onclick = async () => {
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
    setView("warehouses");
    loadWarehouses();
  }catch(e){ toast(e.message, "bad"); }
};

$("#btnLogout").onclick = () => {
  API.clearAuth();
  applyRoleUI();
  setView("auth");
};


function applyRoleUI(){
  const token = API.token();
  const role = API.role();

  $("#devPill").textContent = `DEV = ${String(window.__DEV__ ?? true)}`;

  $("#navGuest").classList.toggle("hidden", !!token);

  $("#navAuthed").classList.toggle("hidden", !token);
  $("#btnLogout").classList.toggle("hidden", !token);
  $("#userMini").classList.toggle("hidden", !token);

  $("#miniLogin").textContent = API.login() || "—";
  $("#miniRole").textContent = role || "—";

  $("#navEmployees").classList.toggle("hidden", !(role==="ceo" || role==="root"));
  $("#navRootCompanies").classList.toggle("hidden", role!=="root");
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
  grid.innerHTML = "";

  if (!list.length){
    grid.innerHTML = `<div class="card muted">Складов пока нет. Создай первый 🙂</div>`;
    return;
  }

  list.forEach(w=>{
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700; font-size:16px">${escapeHtml(w.name)}</div>
        <span class="badge">${w.id.slice(-6)}</span>
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
        <button class="btn btn-small btn-danger" data-delete="${w.id}">Удалить</button>
      </div>
    `;
    grid.appendChild(card);

    card.querySelector("[data-open-items]").onclick = () => {
      currentWarehouseId = w.id;
      setView("items");
      $("#itemsWarehouseSelect").value = w.id;
      loadItemsView();
    };

    card.querySelector("[data-delete]").onclick = async () => {
      if (!confirm(`Удалить склад "${w.name}"?`)) return;
      try{
        await API.req(`/warehouse/delete/${w.id}`, {method:"DELETE"});
        toast("Склад удалён", "good");
        loadWarehouses();
      }catch(e){ toast(e.message, "bad"); }
    };
  });
}

$("#btnWarehouseCreate").onclick = () => {
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
    onMount: (el) => {
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
        }catch(e){ toast(e.message, "bad"); }
      };
    }
  });
};

$("#warehouseSearch").oninput = (e) => {
  const q = e.target.value.toLowerCase().trim();
  renderWarehouses(
    warehousesCache.filter(w => w.name.toLowerCase().includes(q))
  );
};

function fillWarehouseSelects(){
  const selects = [$("#itemsWarehouseSelect"), $("#suppliesWarehouseSelect")];
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
    $("#itemsWarehouseSelect").value = currentWarehouseId;
    $("#suppliesWarehouseSelect").value = currentWarehouseId;
  }
}

let itemsCache = [];

async function loadItemsView(){
  if (!warehousesCache.length){
    await loadWarehouses();
    if (!warehousesCache.length) return;
  }
  const wid = $("#itemsWarehouseSelect").value;
  currentWarehouseId = wid;

  try{
    const data = await API.req(`/items/list/${wid}`);
    itemsCache = data.items || [];
    renderItems(itemsCache);
  }catch(e){ toast(e.message, "bad"); }
}

$("#itemsWarehouseSelect").onchange = loadItemsView;
$("#itemsSearch").oninput = (e)=>{
  const q = e.target.value.toLowerCase().trim();
  renderItems(itemsCache.filter(i => i.name.toLowerCase().includes(q)));
};

function itemLowBadge(i, wh){
  const low = i.low_limit ?? wh.low_stock_default ?? 1;
  if (i.count <= low) return `<span class="badge bad">low ≤ ${low}</span>`;
  if (i.count <= low*2) return `<span class="badge warn">warn</span>`;
  return `<span class="badge good">ok</span>`;
}

function renderItems(list){
  const grid = $("#itemsGrid");
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

$("#btnItemCreate").onclick = () => {
  const wid = currentWarehouseId || $("#itemsWarehouseSelect").value;

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
        }catch(e){ toast(e.message, "bad"); }
      };
    }
  });
};

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

$("#btnLowStock").onclick = async ()=>{
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
};

let suppliesCache = [];

async function loadSuppliesView(){
  if (!warehousesCache.length){
    await loadWarehouses();
    if (!warehousesCache.length) return;
  }
  const wid = $("#suppliesWarehouseSelect").value;
  currentWarehouseId = wid;

  try{
    const data = await API.req(`/supplies/list/${wid}`);
    suppliesCache = data.supplies || [];
    renderSupplies(suppliesCache);
  }catch(e){ toast(e.message, "bad"); }
}

$("#suppliesWarehouseSelect").onchange = loadSuppliesView;

function renderSupplies(list){
  const grid = $("#suppliesGrid");
  grid.innerHTML = "";

  if (!list.length){
    grid.innerHTML = `<div class="card muted">Поставок нет.</div>`;
    return;
  }

  list.forEach(s=>{
    const statusBadge =
      s.status==="done" ? "good" :
      s.status==="canceled" ? "bad" : "warn";

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <div style="font-weight:700">${s.item_id?.slice(-6) || "item"}</div>
        <span class="badge ${statusBadge}">${escapeHtml(s.status)}</span>
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
        }catch(e){ toast(e.message,"bad"); }
      };
    });
  });
}

$("#btnSupplyCreate").onclick = async ()=>{
  const wid = currentWarehouseId || $("#suppliesWarehouseSelect").value;

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
        }catch(e){ toast(e.message,"bad"); }
      };
    }
  });
};


async function loadEmployees(){
  try{
    const data = await API.req("/company/users/list");
    renderEmployees(data.users || []);
  }catch(e){ toast(e.message,"bad"); }
}

function renderEmployees(list){
  const grid = $("#employeesGrid");
  grid.innerHTML = "";
  if (!list.length){
    grid.innerHTML = `<div class="card muted">Сотрудников нет.</div>`;
    return;
  }
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
      </div>
    `;
    grid.appendChild(card);

    card.querySelector("[data-edit]").onclick = () => openEmployeeEdit(u);
  });
}

$("#btnEmployeeCreate").onclick = ()=>{
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
};

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
    </div

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

$("#btnRootRefresh").onclick = loadRootCompanies;

function renderRootCompanies(list){
  const grid = $("#rootCompaniesGrid");
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


function escapeHtml(s){
  return String(s ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}
function escapeAttr(s){ return escapeHtml(s).replaceAll("\n"," "); }

(function boot(){
  applyRoleUI();
  if (API.token()){
    setView("warehouses");
    loadWarehouses();
  } else {
    setView("auth");
  }
})();
