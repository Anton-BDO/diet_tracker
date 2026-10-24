import { api } from "./api.js";
import { store } from "./store.js";
import { renderLogin } from "./views/login.js";
import { renderDashboard } from "./views/dashboard.js";

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
  cleanup = renderDashboard(root, {
  store,
  onLogout: async () => {
    try {
      await store.logout();
    } catch {
      store.clearSession();
    } finally {
      location.replace("#/login");
    }
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
