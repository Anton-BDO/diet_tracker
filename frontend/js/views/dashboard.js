import { renderNav } from "./nav.js";

const MEAL_NAMES = {
  breakfast: "Завтрак",
  lunch: "Обед",
  dinner: "Ужин",
  snack: "Перекус",
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function skeleton() {
  const box = el("div", "dashboard-container");
  box.setAttribute("role", "status");
  box.setAttribute("aria-label", "Загрузка данных");
  for (let i = 0; i < 4; i += 1) {
    const line = el("div", "skeleton");
    line.style.marginBottom = "16px";
    line.style.height = `${56 - i * 8}px`;
    box.appendChild(line);
  }
  return box;
}

function errorState(message, onRetry) {
  const box = el("div", "error-state");
  box.appendChild(el("p", "form-error", message));
  const retry = el("button", "button-secondary", "Повторить");
  retry.addEventListener("click", onRetry);
  box.appendChild(retry);
  return box;
}

function mealList(entries, actions) {
  const container = el("div", "dashboard-meals-list");
  if (!entries.length) {
    const empty = el("div", "empty-state");
    empty.appendChild(el("p", "", "Пока ничего не добавлено"));
    const cta = el("button", "button-primary", "Добавить первую запись");
    cta.addEventListener("click", () => { location.hash = "/add-food"; });
    empty.appendChild(cta);
    container.appendChild(empty);
    return container;
  }
  const groups = {};
  for (const entry of entries) {
    (groups[entry.meal] ??= []).push(entry);
  }
  for (const meal of ["breakfast", "lunch", "dinner", "snack"]) {
    const items = groups[meal];
    if (!items) continue;
    const group = el("div");
    group.appendChild(el("h4", "meal-type-title", MEAL_NAMES[meal] ?? meal));
    const list = el("ul", "meal-items-list");
    for (const item of items) {
      const row = el("li", "meal-item");
      const name = el("span");
      name.append(`${item.product_name} `);
      name.appendChild(el("span", "muted", `(${item.grams} г)`));
      row.appendChild(name);
      const actionsBox = el("span", "meal-item-actions");
      const kcal = el("strong", "", `${item.kcal} ккал`);
      actionsBox.appendChild(kcal);
      const editButton = el("button", "", "Изменить");
      editButton.addEventListener("click", () => {
        location.hash = `/add-food?entry=${encodeURIComponent(item.id)}`;
      });
      const deleteButton = el("button", "", "Удалить");
      deleteButton.addEventListener("click", async () => {
        if (!globalThis.confirm("Удалить эту запись?")) return;
        deleteButton.disabled = true;
        try {
          await actions.deleteEntry(item.id);
        } catch {
          deleteButton.disabled = false;
        }
      });
      actionsBox.append(editButton, deleteButton);
      row.appendChild(actionsBox);
      list.appendChild(row);
    }
    group.appendChild(list);
    container.appendChild(group);
  }
  return container;
}

function renderContent(root, state, actions) {
  const { totals, norm, remaining, entries, is_success: isSuccess } =
    state.daySummary;
  const screen = el("section", "dashboard-container");
  screen.setAttribute("aria-labelledby", "dashboard-title");

  const header = el("div", "dashboard-header");
  const title = el("h1", "dashboard-title");
  title.id = "dashboard-title";
  title.tabIndex = -1;
  title.textContent = `Привет, ${state.profile.name}!`;
  const logout = el("button", "button-secondary", "Выйти");
  logout.addEventListener("click", async () => {
    logout.disabled = true;
    logout.textContent = "Выходим…";
    await actions.logout();
  });
  header.append(title, logout);
  screen.appendChild(header);

  const caloriesCard = el("div", "auth-card dashboard-card");
  caloriesCard.appendChild(el("p", "calories-big", `${totals.kcal}`));
  caloriesCard.appendChild(el(
    "p", "calories-caption",
    `ккал из нормы ${norm.kcal} ккал · осталось ${remaining.kcal} ккал`,
  ));
  const progress = el("div", "dashboard-progress-bg");
  const fill = el("div", "dashboard-progress-fill");
  fill.classList.add(remaining.kcal < 0 ? "bg-error" : "bg-primary");
  fill.style.width = `${Math.min((totals.kcal / norm.kcal) * 100, 100)}%`;
  progress.appendChild(fill);
  caloriesCard.appendChild(progress);

  const macros = el("div", "dashboard-macros");
  const macroData = [
    ["Белки", totals.protein, norm.protein],
    ["Жиры", totals.fat, norm.fat],
    ["Углеводы", totals.carbs, norm.carbs],
  ];
  for (const [label, value, target] of macroData) {
    const cell = el("div");
    cell.appendChild(el("span", "muted macro-label", label));
    cell.appendChild(el("div", "macro-value", `${value} г `))
      .appendChild(el("span", "muted macro-norm", `/ ${target}`));
    macros.appendChild(cell);
  }
  caloriesCard.appendChild(macros);

  const streakCard = el("div", "auth-card dashboard-card streak-card");
  const streakText = el("div");
  const streak = state.streak ?? { current: 0, record: 0 };
  streakText.appendChild(el("p", "streak-value", `${streak.current}`));
  streakText.appendChild(el(
    "p", "streak-label",
    `дней подряд · рекорд ${streak.record}`,
  ));
  const flame = el(
    "span", `streak-flame ${isSuccess ? "streak-success" : "streak-fail"}`,
    "🔥",
  );
  flame.setAttribute("role", "img");
  flame.setAttribute(
    "aria-label",
    isSuccess ? "Сегодняшний день в пределах нормы" : "Сегодняшний день вне нормы",
  );
  streakCard.append(streakText, flame);
  const dashTop = el("div", "dash-top");
  dashTop.append(caloriesCard, streakCard);
  screen.appendChild(dashTop);

  screen.appendChild(el("h2", "dashboard-meals-title", "Что съедено сегодня"));
  screen.appendChild(mealList(entries, actions));

  screen.appendChild(renderNav("dashboard"));
  root.replaceChildren(screen);
  title.focus();
}

export function renderDashboard(root, { store, onLogout }) {
  root.replaceChildren(skeleton());

  const actions = {
    deleteEntry: id => store.deleteEntry(id),
    logout: onLogout,
  };

  const unsubscribe = store.subscribe(state => {
    if (state.error && !state.daySummary) {
      const message = state.error.message || "Не удалось загрузить данные";
      root.replaceChildren(errorState(message, () => {
        store.dismissError();
        store.loadDashboard().catch(() => {});
      }));
      return;
    }
    if (!state.daySummary || !state.profile) return;
    renderContent(root, state, actions);
  });

  store.loadDashboard().catch(() => {});
  return unsubscribe;
}
