import { api } from "./api.js";
import { store } from "./store.js";
import { renderLogin } from "./views/login.js";

const root = document.getElementById("app");
let cleanup = () => {};

async function showApiStatus() {
  const status = document.getElementById("api-status");
  if (api.mock) {
    status.textContent = "Демо-режим";
    status.classList.add("demo");
    return;
  }
  try {
    await api.health();
    status.textContent = "Сервер подключён";
    status.classList.add("ok");
  } catch {
    status.textContent = "API недоступен";
    status.classList.add("error");
  }
}

function renderRoute() {
  cleanup();
  cleanup = () => {};
  const path = location.hash.slice(1) || "/dashboard";
  if (!store.isAuthenticated() && path !== "/login") {
    location.replace("#/login");
    return;
  }
  if (store.isAuthenticated() && path === "/login") {
    location.replace("#/dashboard");
    return;
  }
  if (path === "/login") {
    cleanup = renderLogin(root, {
      store, mock: api.mock,
      onSuccess: () => { location.hash = "/dashboard"; },
    });
    return;
  }
  if (path !== "/dashboard") {
    location.replace("#/dashboard");
    return;
  }
  root.innerHTML = `
    <section class="dashboard-placeholder">
      <h1 tabindex="-1">Вход выполнен</h1>
      <p>Пользователь: <strong data-profile-name></strong>.</p>
      <p class="muted">Главная страница пока в разработке.</p>
      <button type="button" class="button-secondary" data-logout>Выйти из аккаунта</button>
    </section>`;
  root.querySelector("[data-profile-name]").textContent = store.getState().profile.name;
  root.querySelector("h1").focus();
  root.querySelector("[data-logout]").addEventListener("click", async event => {
    event.target.disabled = true;
    event.target.textContent = "Выходим…";
    try {
      await store.logout();
    } catch {
      store.clearSession();
    } finally {
      location.replace("#/login");
    }
  });
}

window.addEventListener("auth:expired", () => {
  store.clearSession();
  if (location.hash !== "#/login") location.replace("#/login");
});

async function start() {
  showApiStatus();
  await store.restore();
  window.addEventListener("hashchange", renderRoute);
  renderRoute();
}

start();
