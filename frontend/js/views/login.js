import { localDate, validateAuth } from "../auth-validation.js";

const activityOptions = [
  ["1.2", "Минимальная"], ["1.375", "Низкая"], ["1.55", "Средняя"],
  ["1.725", "Высокая"], ["1.9", "Очень высокая"],
];

function field(mode, name, label, { type = "text", options, attrs = "", wide = false } = {}) {
  const id = `${mode}-${name}`;
  const control = options
    ? `<select id="${id}" name="${name}" required aria-describedby="${id}-error">
        <option value="">Выберите</option>
        ${options.map(([value, text]) => `<option value="${value}">${text}</option>`).join("")}
      </select>`
    : `<div class="input-wrap">
        <input id="${id}" name="${name}" type="${type}" required ${attrs}
          aria-describedby="${id}-error">
        ${type === "password" ? `<button type="button" class="password-toggle"
          data-password="${id}" aria-label="Показать пароль" aria-pressed="false">Показать</button>` : ""}
      </div>`;
  return `<div class="field${wide ? " field-wide" : ""}">
    <label for="${id}">${label}</label>${control}
    <span class="field-error" id="${id}-error" aria-live="polite"></span>
  </div>`;
}

export function renderLogin(root, { store, mock = false, onSuccess }) {
  root.innerHTML = `
    <section class="auth-layout" aria-labelledby="auth-title">
      <div class="auth-card" data-mode="login">
        <div class="auth-card-heading">
          <h1 id="auth-title" data-auth-title>Вход в аккаунт</h1>
        </div>
        <div class="auth-tabs" role="tablist" aria-label="Доступ к аккаунту">
          <button type="button" role="tab" id="login-tab" aria-selected="true"
            aria-controls="login-panel" data-auth-tab="login">Вход</button>
          <button type="button" role="tab" id="register-tab" aria-selected="false"
            aria-controls="register-panel" tabindex="-1" data-auth-tab="register">Регистрация</button>
        </div>
        <div id="login-panel" role="tabpanel" aria-labelledby="login-tab">
          <form id="login-form" novalidate>
            <div class="form-grid login-fields">
              ${field("login", "email", "Электронная почта", {
                type: "email", attrs: 'autocomplete="username" placeholder="user@example.com"',
              })}
              ${field("login", "password", "Пароль", {
                type: "password", attrs: 'autocomplete="current-password"',
              })}
            </div>
            <p class="form-error" role="alert" hidden></p>
            <button class="button-primary" type="submit" data-idle-text="Войти">Войти</button>
          </form>
        </div>
        <div id="register-panel" role="tabpanel" aria-labelledby="register-tab" hidden>
          <form id="register-form" novalidate>
            <div class="form-grid">
              ${field("register", "email", "Электронная почта", {
                type: "email", attrs: 'autocomplete="email" placeholder="user@example.com"',
              })}
              ${field("register", "password", "Пароль", {
                type: "password", attrs: 'autocomplete="new-password" minlength="8" placeholder="От 8 символов"',
              })}
              ${field("register", "name", "Имя", { wide: true, attrs: 'autocomplete="name"' })}
              ${field("register", "sex", "Пол", { options: [["male", "Мужской"], ["female", "Женский"]] })}
              ${field("register", "birth_date", "Дата рождения", { type: "date", attrs: `autocomplete="bday" max="${localDate()}"` })}
              ${field("register", "height_cm", "Рост, см", { type: "number", attrs: 'min="100" max="250" step="0.1" inputmode="decimal" placeholder="Например, 180"' })}
              ${field("register", "weight_kg", "Вес, кг", { type: "number", attrs: 'min="30" max="300" step="0.1" inputmode="decimal" placeholder="Например, 80"' })}
              ${field("register", "activity", "Активность", { options: activityOptions })}
              ${field("register", "goal", "Ваша цель", { options: [["lose", "Снизить вес"], ["keep", "Поддерживать вес"], ["gain", "Набрать вес"]] })}
            </div>
            <p class="form-error" role="alert" hidden></p>
            <button class="button-primary" type="submit" data-idle-text="Создать аккаунт">Создать аккаунт</button>
          </form>
        </div>
        <p class="request-status" role="status" aria-live="polite"></p>
        <p class="auth-footnote">${mock
          ? "Демо-режим: аккаунт на сервере не создаётся."
          : "Параметры профиля нужны для расчёта вашей дневной нормы."}</p>
      </div>
    </section>`;

  const forms = {
    login: root.querySelector("#login-form"),
    register: root.querySelector("#register-form"),
  };
  const tabs = [...root.querySelectorAll("[data-auth-tab]")];
  let mode = "login";
  let lastError = null;

  function clearErrors(form) {
    form.querySelectorAll("[aria-invalid]").forEach(input => input.removeAttribute("aria-invalid"));
    form.querySelectorAll(".field-error").forEach(error => { error.textContent = ""; });
    form.querySelector(".form-error").hidden = true;
  }

  function showFieldError(form, name, message) {
    const input = form.elements.namedItem(name);
    if (!input) return false;
    input.setAttribute("aria-invalid", "true");
    document.getElementById(`${input.id}-error`).textContent = message;
    return true;
  }

  function switchTab(next) {
    if (store.getState().pending) return;
    mode = next;
    store.dismissError();
    clearErrors(forms[mode]);
    tabs.forEach(tab => {
      const selected = tab.dataset.authTab === mode;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      root.querySelector(`#${tab.dataset.authTab}-panel`).hidden = !selected;
    });
    root.querySelector(".auth-card").dataset.mode = mode;
    root.querySelector("[data-auth-title]").textContent = mode === "login"
      ? "Вход в аккаунт" : "Регистрация";
  }

  tabs.forEach(tab => {
    tab.addEventListener("click", () => switchTab(tab.dataset.authTab));
    tab.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? tabs[0] : event.key === "End"
        ? tabs[1] : tabs.find(item => item !== tab);
      switchTab(next.dataset.authTab);
      next.focus();
    });
  });

  root.querySelectorAll("[data-password]").forEach(button => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.password);
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.textContent = visible ? "Скрыть" : "Показать";
      button.setAttribute("aria-pressed", String(visible));
      button.setAttribute("aria-label", visible ? "Скрыть пароль" : "Показать пароль");
    });
  });

  for (const [formMode, form] of Object.entries(forms)) {
    form.addEventListener("input", event => {
      const input = event.target;
      input.removeAttribute("aria-invalid");
      const error = document.getElementById(`${input.id}-error`);
      if (error) error.textContent = "";
    });
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (store.getState().pending) return;
      clearErrors(form);
      const { data, errors } = validateAuth(formMode, Object.fromEntries(new FormData(form)));
      if (Object.keys(errors).length) {
        Object.entries(errors).forEach(([name, message]) => showFieldError(form, name, message));
        form.querySelector('[aria-invalid="true"]').focus();
        return;
      }
      try {
        await store[formMode](data);
        onSuccess();
      } catch {
        return;
      }
    });
  }

  return store.subscribe(state => {
    tabs.forEach(tab => { tab.disabled = state.pending; });
    Object.values(forms).forEach(form => {
      form.setAttribute("aria-busy", String(state.pending));
      form.querySelectorAll("input, select, button").forEach(input => { input.disabled = state.pending; });
      const submit = form.querySelector('[type="submit"]');
      submit.textContent = state.pending ? "Подождите…" : submit.dataset.idleText;
    });
    root.querySelector(".request-status").textContent = state.pending ? "Проверяем данные…" : "";
    if (state.error && state.error !== lastError) {
      const form = forms[mode];
      clearErrors(form);
      const message = state.error instanceof TypeError
        ? "Не удалось связаться с сервером. Проверьте подключение"
        : state.error.message || "Не удалось отправить запрос. Попробуйте ещё раз";
      if (showFieldError(form, state.error.field, message)) {
        const input = form.elements.namedItem(state.error.field);
        requestAnimationFrame(() => {
          if (input.isConnected && forms[mode] === form && !store.getState().pending) input.focus();
        });
      } else {
        const error = form.querySelector(".form-error");
        error.textContent = message;
        error.hidden = false;
      }
    }
    lastError = state.error;
  });
}
