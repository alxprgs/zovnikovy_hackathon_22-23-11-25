const endpoints = [
    {
        id: "auth",
        method: "POST",
        path: "/user/auth",
        description: "Авторизация по логину и паролю",
        payloadLocation: "body",
        fields: [
            { name: "login", label: "Логин", type: "text", placeholder: "root" },
            { name: "password", label: "Пароль", type: "password", placeholder: "root_password" },
        ],
    },
    {
        id: "register",
        method: "POST",
        path: "/user/register",
        description: "Регистрация нового пользователя",
        payloadLocation: "body",
        fields: [
            { name: "login", label: "Логин", type: "text", placeholder: "user123" },
            { name: "password", label: "Пароль", type: "password", placeholder: "min 6 символов" },
        ],
    },
    {
        id: "create",
        method: "POST",
        path: "/user/create",
        description: "Создание пользователя с правами (требуется user_create)",
        payloadLocation: "body",
        fields: [
            { name: "login", label: "Логин", type: "text", placeholder: "new_admin" },
            { name: "password", label: "Пароль", type: "password", placeholder: "min 6 символов" },
            {
                name: "permissions",
                label: "Права (JSON)",
                type: "json",
                placeholder: '{ "user": true, "user_create": true }',
            },
        ],
    },
    {
        id: "update",
        method: "PUT",
        path: "/user/update",
        description: "Обновление пользователя (требуется user_update)",
        payloadLocation: "body",
        fields: [
            { name: "login", label: "Логин пользователя", type: "text", placeholder: "user123" },
            {
                name: "updates",
                label: "Обновления (JSON, без $ операторов)",
                type: "json",
                placeholder: '{ "permissions.user_create": true }',
            },
        ],
    },
    {
        id: "delete",
        method: "DELETE",
        path: "/user/delete",
        description: "Удаление пользователя (требуется user_delete)",
        payloadLocation: "query",
        fields: [
            { name: "login", label: "Логин пользователя", type: "text", placeholder: "user123" },
        ],
    },
    {
        id: "logout",
        method: "POST",
        path: "/user/logout",
        description: "Выход (удаляет access_token cookie)",
        payloadLocation: "none",
        fields: [],
    },
    {
        id: "vk_callback",
        method: "GET",
        path: "/user/auth/vk/callback",
        description: "Тестовый вызов VK callback (обычно вызывается VK ID)",
        payloadLocation: "query",
        fields: [
            { name: "code", label: "code", type: "text", placeholder: "полученный от VK" },
            { name: "device_id", label: "device_id", type: "text", placeholder: "полученный от VK" },
        ],
    },
    {
        id: "test_mail",
        method: "POST",
        path: "/dev/test_mail",
        description: "Тест отправки письма",
        payloadLocation: "body",
        fields: [
            { name: "email", label: "Email", type: "email", placeholder: "you@example.com" },
        ],
    },
    {
        id: "test_weather",
        method: "POST",
        path: "/dev/test_weather",
        description: "Тест получения погоды",
        payloadLocation: "body",
        fields: [
            { name: "city", label: "Город", type: "text", placeholder: "Moscow" },
        ],
    },
    {
        id: "healthz",
        method: "GET",
        path: "/healthz",
        description: "Проверка работоспособности сервиса",
        payloadLocation: "none",
        fields: [],
    },
];

function getBaseUrl() {
    return window.location.origin;
}

function findEndpoint(id) {
    return endpoints.find((e) => e.id === id);
}

function renderFields(ep) {
    const container = document.getElementById("dev-fields");
    container.innerHTML = "";

    if (!ep.fields || ep.fields.length === 0) {
        const empty = document.createElement("div");
        empty.className = "dev-field";
        empty.innerHTML = "<span class='dev-label'>Параметров нет</span>";
        container.appendChild(empty);
        return;
    }

    ep.fields.forEach((field) => {
        const wrapper = document.createElement("div");
        wrapper.className = "dev-field";

        const label = document.createElement("div");
        label.className = "dev-label";
        label.innerHTML = `<span>${field.label}</span><span>${field.name}</span>`;

        if (field.type === "json") {
            const textarea = document.createElement("textarea");
            textarea.className = "dev-textarea";
            textarea.name = field.name;
            textarea.placeholder = field.placeholder || "";
            wrapper.appendChild(label);
            wrapper.appendChild(textarea);
        } else {
            const input = document.createElement("input");
            input.className = "dev-input";
            input.type = field.type || "text";
            input.name = field.name;
            input.placeholder = field.placeholder || "";
            wrapper.appendChild(label);
            wrapper.appendChild(input);
        }

        container.appendChild(wrapper);
    });
}

function setActiveTab(id) {
    document.querySelectorAll(".dev-tab-btn").forEach((btn) => {
        if (btn.dataset.endpointId === id) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

function renderEndpoint(ep) {
    document.getElementById("ep-method").textContent = ep.method;
    document.getElementById("ep-path").textContent = ep.path;
    renderFields(ep);
    document.getElementById("dev-response-meta").textContent = ep.description || "";
    document.getElementById("dev-response-body").textContent = "// Ответ появится здесь";
}

async function sendRequest(ep, formData) {
    const baseUrl = getBaseUrl();
    let url = baseUrl + ep.path;

    let options = {
        method: ep.method,
        headers: {},
        credentials: "include",
    };

    const payload = {};
    ep.fields.forEach((field) => {
        const value = formData.get(field.name);
        if (value !== null && value !== "") {
            if (field.type === "json") {
                try {
                    payload[field.name] = JSON.parse(value);
                } catch (e) {
                    throw new Error(`Поле "${field.label}" должно быть валидным JSON`);
                }
            } else {
                payload[field.name] = value;
            }
        }
    });

    if (ep.payloadLocation === "body") {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(payload);
    } else if (ep.payloadLocation === "query") {
        const params = new URLSearchParams();
        Object.entries(payload).forEach(([k, v]) => params.append(k, v));
        const qs = params.toString();
        if (qs) {
            url += (url.includes("?") ? "&" : "?") + qs;
        }
    }

    const started = performance.now();
    const res = await fetch(url, options);
    const duration = performance.now() - started;

    let bodyText;
    let parsed;

    const contentType = res.headers.get("content-type") || "";

    try {
        if (contentType.includes("application/json")) {
            parsed = await res.json();
            bodyText = JSON.stringify(parsed, null, 2);
        } else {
            bodyText = await res.text();
        }
    } catch (e) {
        bodyText = `Ошибка чтения ответа: ${e}`;
    }

    return {
        status: res.status,
        ok: res.ok,
        duration,
        bodyText,
    };
}

function initDevPanel() {
    const defaultId = "auth";
    const form = document.getElementById("dev-form");
    const clearBtn = document.getElementById("dev-clear-btn");
    const responseMeta = document.getElementById("dev-response-meta");
    const responseBody = document.getElementById("dev-response-body");

    let currentEp = findEndpoint(defaultId);
    setActiveTab(defaultId);
    renderEndpoint(currentEp);

    document.querySelectorAll(".dev-tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.endpointId;
            const ep = findEndpoint(id);
            if (!ep) return;
            currentEp = ep;
            setActiveTab(id);
            renderEndpoint(ep);
        });
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentEp) return;

        const formData = new FormData(form);
        responseMeta.textContent = "Отправка запроса...";
        responseBody.textContent = "";

        try {
            const res = await sendRequest(currentEp, formData);
            responseMeta.textContent = `${res.status} • ${res.duration.toFixed(1)} ms`;
            responseBody.textContent = res.bodyText;
        } catch (err) {
            responseMeta.textContent = "Ошибка на клиенте";
            responseBody.textContent = String(err);
        }
    });

    clearBtn.addEventListener("click", () => {
        form.reset();
        responseMeta.textContent = "";
        responseBody.textContent = "// Ответ появится здесь";
    });
}

function initVKAuthWidget() {
    const statusEl = document.getElementById("vkid-status");
    const container = document.getElementById("vkid-one-tap");
    const cfg = window.VK_DEV_CONFIG || null;

    if (!container || !cfg) {
        return;
    }

    if (!("VKIDSDK" in window)) {
        if (statusEl) statusEl.textContent = "VKID SDK не загрузился";
        return;
    }

    const VKID = window.VKIDSDK;

    try {
        VKID.Config.init({
            app: cfg.clientId,
            redirectUrl: cfg.redirectUrl,
            responseMode: VKID.ConfigResponseMode.Callback,
            source: VKID.ConfigSource.LOWCODE,
            scope: "", // при необходимости добавишь
        });

        const oneTap = new VKID.OneTap();

        oneTap
            .render({
                container: container,
                showAlternativeLogin: true,
                styles: {
                    borderRadius: 7,
                    width: 260,
                },
            })
            .on(VKID.WidgetEvents.ERROR, function (error) {
                console.error("VKID error:", error);
                if (statusEl) statusEl.textContent = "Ошибка VK: " + (error?.message || String(error));
            })
            .on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, function (payload) {
                const code = payload.code;
                const deviceId = payload.device_id;

                if (statusEl) statusEl.textContent = "VK ID: код получен, авторизация...";

                const url = `/user/auth/vk/callback?code=${encodeURIComponent(
                    code
                )}&device_id=${encodeURIComponent(deviceId)}`;

                fetch(url, {
                    method: "GET",
                    credentials: "include",
                })
                    .then(async (res) => {
                        const text = await res.text();
                        let body = text;

                        try {
                            const json = JSON.parse(text);
                            body = JSON.stringify(json, null, 2);
                        } catch (_) {
                            // не JSON — оставляем как есть
                        }

                        const respBody = document.getElementById("dev-response-body");
                        const respMeta = document.getElementById("dev-response-meta");

                        if (respMeta) {
                            respMeta.textContent = `${res.status} • VK callback`;
                        }
                        if (respBody) {
                            respBody.textContent = body;
                        }

                        if (res.ok) {
                            if (statusEl) statusEl.textContent = "Успешно авторизован через VK (access_token cookie установлена)";
                        } else {
                            if (statusEl) statusEl.textContent = "Ошибка backend при авторизации VK";
                        }
                    })
                    .catch((err) => {
                        console.error("VK callback fetch error:", err);
                        if (statusEl) statusEl.textContent = "Ошибка запроса к /user/auth/vk/callback";
                    });
            });
    } catch (e) {
        console.error("VKID init error:", e);
        if (statusEl) statusEl.textContent = "Ошибка инициализации VKID";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initDevPanel();
    initVKAuthWidget();
});