
function getMealName(meal) {
  if (meal === "breakfast") return "Завтрак";
  if (meal === "lunch") return "Обед";
  if (meal === "dinner") return "Ужин";
  if (meal === "snack") return "Перекус";
  return meal;
}

export function renderDashboard(root, { store, onLogout }) {
  root.innerHTML = `
    <section class="dashboard-placeholder">
      <p class="loading-message">Загрузка данных...</p>
    </section>`;

  const unsubscribe = store.subscribe(state => {
    if (state.error) {
      const errorContainer = root.querySelector(".dashboard-placeholder");
      errorContainer.innerHTML = `<p class="form-error"></p>`;
      errorContainer.querySelector(".form-error").textContent = 
        `Ошибка: ${state.error.message || "Не удалось загрузить данные"}`;
      return;
    }

    if (state.pending || !state.daySummary || !state.profile) return;

    const { totals, norm, remaining, entries } = state.daySummary;
    const { name } = state.profile;

    const groupedMeals = entries.reduce((acc, item) => {
      if (!acc[item.meal]) acc[item.meal] = [];
      acc[item.meal].push(item);
      return acc;
    }, {});

    root.innerHTML = `
      <section class="dashboard-placeholder dashboard-container">
        <div class="dashboard-header">
          <h1 tabindex="-1" class="dashboard-title"></h1>
          <button type="button" class="button-secondary" data-logout>Выйти</button>
        </div>
        
        <div class="auth-card dashboard-card">
          <h2 class="dashboard-calories-title">
            Калории: <span>${totals.kcal}</span> / <span>${norm.kcal}</span> ккал
          </h2>
          
          <div class="dashboard-progress-bg">
            <!-- Добавили data-progress и классы для цвета -->
            <div class="dashboard-progress-fill ${remaining.kcal < 0 ? 'bg-error' : 'bg-primary'}" data-progress></div>
          </div>

          <div class="dashboard-macros">
            <div><span class="muted macro-label">Белки</span><div class="macro-value">${totals.protein} г <span class="muted macro-norm">/ ${norm.protein}</span></div></div>
            <div><span class="muted macro-label">Жиры</span><div class="macro-value">${totals.fat} г <span class="muted macro-norm">/ ${norm.fat}</span></div></div>
            <div><span class="muted macro-label">Углеводы</span><div class="macro-value">${totals.carbs} г <span class="muted macro-norm">/ ${norm.carbs}</span></div></div>
            <div><span class="muted macro-label">Осталось</span><div class="macro-value ${remaining.kcal < 0 ? 'text-error' : 'text-ok'}">${remaining.kcal} ккал</div></div>
          </div>

          <h3 class="dashboard-meals-title">Что съедено сегодня:</h3>
          <div class="dashboard-meals-list" data-meals-list></div>
        </div>
        <button type="button" class="button-primary dashboard-add-btn">+ Добавить еду</button>
      </section>`;

    root.querySelector(".dashboard-title").textContent = `Привет, ${name}!`;

    const progressBar = root.querySelector("[data-progress]");
    if (progressBar) {
      const percent = Math.min((totals.kcal / norm.kcal) * 100, 100);
      progressBar.style.width = `${percent}%`;
    }

    const mealsListContainer = root.querySelector("[data-meals-list]");
    
    Object.entries(groupedMeals).forEach(([mealType, items]) => {
      const mealDiv = document.createElement("div");
      
      const title = document.createElement("h4");
      title.className = "meal-type-title";
      title.textContent = getMealName(mealType); 
      mealDiv.appendChild(title);

      const ul = document.createElement("ul");
      ul.className = "meal-items-list";

      items.forEach(item => {
        const li = document.createElement("li");
        li.className = "meal-item";

        const spanName = document.createElement("span");
        spanName.className = "meal-item-name";
        spanName.textContent = `${item.product_name} `; 
        
        const spanGrams = document.createElement("span");
        spanGrams.className = "muted";
        spanGrams.textContent = `(${item.grams}г)`;
        
        spanName.appendChild(spanGrams);

        const kcalStrong = document.createElement("strong");
        kcalStrong.textContent = `${item.kcal} ккал`; 

        li.appendChild(spanName);
        li.appendChild(kcalStrong);
        ul.appendChild(li);
      });

      mealDiv.appendChild(ul);
      mealsListContainer.appendChild(mealDiv);
    });

    root.querySelector("[data-logout]").addEventListener("click", async (e) => {
      e.target.disabled = true;
      e.target.textContent = "Выходим...";
      await onLogout();
    });
  });

  store.loadDashboard().catch(() => {});
  return unsubscribe;
}
