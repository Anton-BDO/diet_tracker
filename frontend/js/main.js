import { api } from "./api.js";

async function showApiStatus() {
  const el = document.getElementById("api-status");
  try {
    const data = await api.health();
    el.textContent = `Сервер: ${data.status}`;
    el.classList.add("ok");
  } catch {
    el.textContent = "Сервер недоступен";
    el.classList.add("error");
  }
}

showApiStatus();
