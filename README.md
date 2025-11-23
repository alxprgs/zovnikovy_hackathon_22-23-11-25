# ASFES Warehouse System

**ASFES Warehouse** — компактная система учёта складов, товаров и поставок с ролями (root / CEO / employee), low-stock уведомлениями и WebSocket-камерой для автообновления остатков.  
Фронт — лёгкая SPA на чистом JS/CSS, бэк — FastAPI + MongoDB.

---

## ✨ Возможности

- **Склады**
  - создание / редактирование / мягкое удаление
  - порог low-stock по умолчанию на склад
  - список email для уведомлений
  - блокировка складов (root)

- **Товары**
  - CRUD товаров внутри склада
  - операции **приход / расход**
  - история по товару и по складу
  - автоматический low-stock контроль  
    → письмо на email + запись уведомления в системе

- **Поставки**
  - планирование будущих поставок (expected_at)
  - статусы: `waiting / done / canceled`
  - авто-mark `overdue` и уведомления о просрочке
  - при `done` остаток увеличивается автоматически

- **Уведомления**
  - системные уведомления по ключевым событиям
  - отметка прочитанным
  - счётчик непрочитанных в UI

- **Экспорт**
  - экспорт товаров / поставок / истории в CSV

- **Камера (WebSocket)**
  - камера подключается к складу и присылает детекции
  - при изменении количества создаётся история + low-stock обработка

---

## 🧱 Архитектура

**Backend**
- FastAPI (ASGI)
- MongoDB (через `asfeslib.databases.MongoDB`)
- JWT авторизация
- RBAC-permissions
- Mailer (через `asfeslib.net.mail`)
- Notifications subsystem
- Dev-режим с Swagger/Redoc

**Frontend**
- `/static/app` — SPA на Vanilla JS
- роли/права динамически скрывают/показывают UI
- UI в стиле “dark-glass” (CSS variables)

---

## 👤 Роли и доступы

**root**
- видит все компании/склады/товары
- может блокировать/удалять компании и склады
- wildcard-permission: `*`

**CEO**
- управляет своей компанией
- создаёт/редактирует сотрудников
- создаёт склады

**employee**
- работает только в рамках своей компании и выданных permissions

Проверка прав идёт через dependency `require_permission(perm)`.

---

## 🔐 Permissions (каталог)

Используются в JWT payload и в UI-каталоге.

- `company.update`
- `users.create`, `users.update`
- `warehouses.create`, `warehouses.update`, `warehouses.delete`
- `items.create`, `items.update`, `items.delete`, `items.op`
- `supplies.create`, `supplies.update`, `supplies.delete` *(эндпоинт можно добавить позже)*
- `camera.create_key`
- `*` — полный доступ (root)

---

## 🚀 Быстрый старт

### 1) Установка

```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) `.env`

Минимальный набор переменных:

```env
# App
DEV=true
DOMAIN_WITHOUT_WWW=asfes.ru
DOMAIN=hackathon.asfes.ru
PORT=9105
WEATHER_API_KEY=your_key

# Mongo
MONGO_URL=mongodb://user:pass@host:27017/dbname

# JWT
JWT_SECRET_KEY=supersecret
JWT_ALGORITHM=HS256
JWT_TOKEN_EXPIRE_SEC=3600

# Mail
MAIL_USERNAME=noreply@asfes.ru
MAIL_PASSWORD=mail_pass
MAIL_SERVER_SMTP=mail.asfes.ru
MAIL_PORT_SMTP=465
MAIL_SERVER_IMAP=mail.asfes.ru
MAIL_PORT_IMAP=993

# Root user (создаётся автоматически)
ROOT_USER_LOGIN=root
ROOT_USER_PASSWORD=root_password
ROOT_USER_MAIL=admin@asfes.ru
```

> Если `MONGO_URL` не задан, можно собрать URL из `MONGO_USER / MONGO_PASSWORD / MONGO_HOST / MONGO_PORT / MONGO_NAME`.

### 3) Запуск

```bash
uvicorn server:app --reload --port 9105
```

Открой:  
- UI: `http://localhost:9105/`  
- Swagger: `http://localhost:9105/docs` *(только DEV)*

---

## 🗂️ Основные эндпоинты

### Auth / Users
- `POST /user/auth` — логин, выдача JWT  
  body: `{ login, password }`
- `POST /user/register/ceo` — регистрация CEO + компании *(в UI есть форма)*

### Warehouses
- `POST /warehouse/create`
- `GET /warehouse/list`
- `POST /warehouse/update`
- `DELETE /warehouse/delete/{warehouse_id}`
- `POST /warehouse/block/{warehouse_id}` *(root)*
- `POST /warehouse/unblock/{warehouse_id}` *(root)*

### Items
- `POST /items/create`
- `GET /items/list/{warehouse_id}`
  - query: `search, category, low_only, sort, order`
- `POST /items/update`
- `POST /items/income`
- `POST /items/outcome`
- `GET /items/history/{item_id}`
- `GET /items/history/warehouse/{warehouse_id}`
- `GET /items/low_stock/{warehouse_id}`

### Supplies
- `POST /supplies/create`
- `GET /supplies/list/{warehouse_id}`
  - query: `status, search, sort, order`
- `POST /supplies/status`

### Dashboard
- `GET /dashboard/summary`

### Notifications
- `GET /notifications/list?unread_only=true`
- `POST /notifications/read/{notification_id}`

### Export
- `GET /export/items/{warehouse_id}`
- `GET /export/supplies/{warehouse_id}`
- `GET /export/history/{warehouse_id}`

### Health / Meta
- `GET /healthz`
- `GET /meta`

### DEV-only
- `POST /dev/test_low_stock_email` — тест письма low-stock

---

## 📡 WebSocket камера

**Подключение**
`WS /ws/warehouse/{warehouse_id}/camera`

1) камера сразу отправляет auth:

```json
{
  "company": "ООО Ромашка",
  "warehouse_id": "<warehouse_id>",
  "api_key": "<camera_api_key>"
}
```

2) сервер отвечает:

```json
{ "ok": true, "warehouse": "Склад №1" }
```

3) дальше камера шлёт детекции:

```json
{
  "detect": [
    {"type": "Шоколад", "count": 10},
    {"type": "Вода", "count": 3}
  ]
}
```

**Логика**
- если товара нет — создаётся автоматически (`category="auto"`)
- если количество изменилось — обновление `items.count` + запись в `history`
- если ниже порога — письмо + уведомление

---

## ✉️ Low-stock письма

Отправка идёт из:
- операций с товарами
- статуса поставки `done`
- WebSocket-камеры

HTML письма стилизовано под тёмный ASFES-дизайн (`_render_low_stock_html`).

---

## 🧾 История и мягкое удаление

- все сущности удаляются “мягко” через `deleted_at`
- история операций хранится в `history`
- список/агрегации автоматически исключают удалённые записи

---

## 🧰 Структура проекта (коротко)

```
server/
  __init__.py              # FastAPI app + lifespan + роутеры
  core/
    config.py              # settings/env + DB configs
    functions/             # hash, jwt, permissions
    paths.py               # DATA_ROOT, logs, static
    mailer.py              # low-stock emails
    notifications.py       # create_notification()
    db_utils.py            # oid/to_jsonable/public_id
  routes/
    user/                  # auth, register
    warehouse/             # manage, items, supplies, camera_ws
    company/               # employees CRUD
    root/                  # companies root-tools
    dashboard.py
    export.py
    notifications.py
    health.py
static/
  app/                     # SPA (index.html, app.js, styles.css)
```

---

## 🛡️ Security notes

- bcrypt hashing (rounds=12)
- JWT expiration (`JWT_TOKEN_EXPIRE_SEC`)
- RBAC на каждом приватном эндпоинте
- middleware с заголовками безопасности:
  - `nosniff`, `deny iframe`, strict referrer, permissions-policy

---

## 📌 Идеи для следующих улучшений

- refresh-tokens / httpOnly cookies
- отдельный endpoint `items.delete`
- endpoint `supplies.delete`
- аудит логов действий пользователя (`by_user_id`) везде
- docker-compose + миграции индексов в отдельный скрипт

---

## 📝 Лицензия

Проект учебный/хакатонный. Лицензию добавь по необходимости (MIT/Apache-2.0/etc).
