import { api } from "../api.js";
import { localDate } from "../auth-validation.js";
import { renderNav } from "./nav.js";

const ACTIVITIES = [
  ["1.2", "Минимальная"], ["1.375", "Низкая"], ["1.55", "Средняя"],
  ["1.725", "Высокая"], ["1.9", "Очень высокая"],
];
const GOALS = [
  ["lose", "Снизить вес"], ["keep", "Поддерживать вес"], ["gain", "Набрать вес"],
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function row(label, value) {
  const box = el("div", "profile-row");
  box.appendChild(el("span", "muted", label));
  box.appendChild(el("span", "", String(value)));
  return box;
}

function selectField(id, labelText, options, current) {
  const label = el("label", "", labelText);
  label.htmlFor = id;
  const select = el("select");
  select.id = id;
  select.name = id;
  for (const [value, text] of options) {
    const option = el("option", "", text);
    option.value = value;
    select.appendChild(option);
  }
  select.value = String(current);
  label.appendChild(select);
  return { label, select };
}

export function renderProfile(root, { store }) {
  const state = store.getState();
  const profile = state.profile;
  const screen = el("section", "dashboard-container");
  screen.setAttribute("aria-labelledby", "profile-title");
  screen.appendChild(el("h1", "screen-title", "Профиль"));

  const infoCard = el("div", "auth-card dashboard-card");
  infoCard.appendChild(row("Email", profile.email));
  infoCard.appendChild(row("Имя", profile.name));
  infoCard.appendChild(row("Пол", profile.sex === "male" ? "Мужской" : "Женский"));
  infoCard.appendChild(row("Дата рождения", profile.birth_date));
  const normCard = el("div", "auth-card dashboard-card");
  normCard.appendChild(el(
    "h2", "dashboard-meals-title",
    `Норма: ${profile.norm.kcal} ккал · Б ${profile.norm.protein} · Ж ${profile.norm.fat} · У ${profile.norm.carbs}`,
  ));
  screen.append(infoCard, normCard);

  const editCard = el("div", "auth-card dashboard-card");
  editCard.appendChild(el("h2", "dashboard-meals-title", "Изменить параметры"));
  const form = el("form");
  form.noValidate = true;
  const errorBox = el("p", "alert alert-error");
  errorBox.setAttribute("role", "alert");
  errorBox.hidden = true;
  form.appendChild(errorBox);

  const height = el("input");
  height.id = "edit-height";
  height.type = "number";
  height.min = "100";
  height.max = "250";
  height.step = "0.1";
  height.value = profile.height_cm;
  const heightLabel = el("label", "", "Рост, см");
  heightLabel.htmlFor = height.id;
  heightLabel.appendChild(height);

  const weight = el("input");
  weight.id = "edit-weight";
  weight.type = "number";
  weight.min = "30";
  weight.max = "300";
  weight.step = "0.1";
  weight.value = profile.weight_kg;
  const weightLabel = el("label", "", "Вес, кг");
  weightLabel.htmlFor = weight.id;
  weightLabel.appendChild(weight);

  const activity = selectField("edit-activity", "Активность", ACTIVITIES,
    profile.activity);
  const goal = selectField("edit-goal", "Цель", GOALS, profile.goal);

  const submit = el("button", "button-primary", "Сохранить");
  submit.type = "submit";
  form.append(heightLabel, weightLabel, activity.label, goal.label, submit);
  editCard.appendChild(form);
  screen.appendChild(editCard);

  const weightCard = el("div", "auth-card dashboard-card");
  weightCard.appendChild(el("h2", "dashboard-meals-title", "Журнал веса"));
  const weightForm = el("form");
  weightForm.noValidate = true;
  const weightError = el("p", "alert alert-error");
  weightError.setAttribute("role", "alert");
  weightError.hidden = true;
  const logInput = el("input");
  logInput.type = "number";
  logInput.min = "30";
  logInput.max = "300";
  logInput.step = "0.1";
  logInput.value = profile.weight_kg;
  const logLabel = el("label", "", "Вес, кг");
  logLabel.appendChild(logInput);
  const logButton = el("button", "button-primary", "Записать вес");
  logButton.type = "submit";
  weightForm.append(weightError, logLabel, logButton);
  weightCard.appendChild(weightForm);
  const history = el("div");
  weightCard.appendChild(history);
  screen.appendChild(weightCard);
  screen.appendChild(renderNav("profile"));
  root.replaceChildren(screen);

  async function loadHistory() {
    history.replaceChildren(el("p", "muted", "Загрузка…"));
    try {
      const logs = await api.weightHistory();
      history.replaceChildren();
      if (!logs.length) {
        history.appendChild(el("p", "muted", "Замеров пока нет"));
        return;
      }
      const table = el("table", "data-table");
      const head = el("tr");
      head.appendChild(el("th", "", "Дата"));
      head.appendChild(el("th", "", "Вес, кг"));
      table.appendChild(head);
      for (const log of logs) {
        const tr = el("tr");
        tr.appendChild(el("td", "", log.date));
        tr.appendChild(el("td", "", String(log.weight_kg)));
        table.appendChild(tr);
      }
      history.appendChild(table);
    } catch (error) {
      history.replaceChildren(el(
        "p", "form-error", error.message || "Не удалось загрузить историю",
      ));
    }
  }
  loadHistory();

  weightForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (logButton.disabled) return;
    weightError.hidden = true;
    logButton.disabled = true;
    try {
      await api.logWeight({
        weight_kg: Number(logInput.value),
        date: localDate(),
      });
      // Сервер обновил вес и норму в профиле: перечитываем и перерисовываем.
      await store.restore();
      renderProfile(root, { store });
    } catch (error) {
      weightError.textContent = error.message || "Не удалось сохранить вес";
      weightError.hidden = false;
    } finally {
      logButton.disabled = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    errorBox.hidden = true;
    submit.disabled = true;
    try {
      await store.updateProfile({
        height_cm: Number(height.value),
        weight_kg: Number(weight.value),
        activity: Number(activity.select.value),
        goal: goal.select.value,
      });
      errorBox.hidden = false;
      errorBox.className = "alert alert-success";
      errorBox.textContent = "Сохранено. Норма пересчитана.";
    } catch (error) {
      errorBox.className = "alert alert-error";
      errorBox.textContent = error.message || "Не удалось сохранить";
      errorBox.hidden = false;
    } finally {
      submit.disabled = false;
    }
  });

  return () => {};
}
