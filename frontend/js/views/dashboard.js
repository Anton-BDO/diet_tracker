
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
      root.querySelector(".dashboard-placeholder").innerHTML = 
        `<p class="form-error">Ошибка: ${state.error.message || "Не удалось загрузить данные"}</p>`;
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
      <section class="dashboard-placeholder" style="max-width: 600px; margin: 0 auto; text-align: left;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
          <h1 tabindex="-1" style="margin: 0;">Привет, ${name}!</h1>
          <button type="button" class="button-secondary" data-logout>Выйти</button>
        </div>
        
        <div class="auth-card" style="max-width: 100%; margin: 0 0 24px 0; padding: 20px;">
          <h2 style="margin: 0 0 10px 0; font-size: 18px;">Калории: ${totals.kcal} / ${norm.kcal} ккал</h2>
          
          <!-- Прогресс-бар -->
          <div style="width: 100%; height: 8px; background: #e0e0e0; border-radius: 4px; margin-bottom: 20px; overflow: hidden;">
            <div style="height: 100%; width: ${Math.min((totals.kcal / norm.kcal) * 100, 100)}%; background: ${remaining.kcal < 0 ? 'var(--error)' : 'var(--primary)'};"></div>
          </div>

          <!-- БЖУ -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            <div>
              <span class="muted" style="font-size: 12px;">Белки</span>
              <div style="font-weight: 600;">${totals.protein} г <span class="muted" style="font-weight: normal; font-size: 12px;">/ ${norm.protein}</span></div>
            </div>
            <div>
              <span class="muted" style="font-size: 12px;">Жиры</span>
              <div style="font-weight: 600;">${totals.fat} г <span class="muted" style="font-weight: normal; font-size: 12px;">/ ${norm.fat}</span></div>
            </div>
            <div>
              <span class="muted" style="font-size: 12px;">Углеводы</span>
              <div style="font-weight: 600;">${totals.carbs} г <span class="muted" style="font-weight: normal; font-size: 12px;">/ ${norm.carbs}</span></div>
            </div>
            <div>
              <span class="muted" style="font-size: 12px;">Осталось</span>
              <div style="font-weight: 600; color: ${remaining.kcal < 0 ? 'var(--error)' : 'var(--ok)'};">${remaining.kcal} ккал</div>
            </div>
          </div>

          <!-- Список еды -->
          <h3 style="font-size: 15px; border-top: 1px solid var(--border); padding-top: 16px; margin-bottom: 12px;">Что съедено сегодня:</h3>
          
          <div style="display: flex; flex-direction: column; gap: 16px;">
            ${Object.entries(groupedMeals).map(([mealType, items]) => `
              <div>
                <h4 style="margin: 0 0 6px 0; font-size: 13px; color: var(--primary);">${getMealName(mealType)}</h4>
                <ul style="list-style: none; padding: 0; margin: 0;">
                  ${items.map(item => `
                    <li style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 14px;">
                      <span>${item.product_name} <span class="muted">(${item.grams}г)</span></span>
                      <strong>${item.kcal} ккал</strong>
                    </li>
                  `).join('')}
                </ul>
              </div>
            `).join('')}
          </div>
        </div>

        <button type="button" class="button-primary" style="width: 100%;">+ Добавить еду</button>
      </section>`;

    root.querySelector("[data-logout]").addEventListener("click", async (e) => {
      e.target.disabled = true;
      e.target.textContent = "Выходим...";
      await onLogout();
    });
  });

  store.loadDashboard().catch(() => {});

  return unsubscribe;
}
