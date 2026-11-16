const ITEMS = [
  ["dashboard", "#/dashboard", "Главная", "⌂"],
  ["add-food", "#/add-food", "Добавить", "＋"],
  ["stats", "#/stats", "Статистика", "📈"],
  ["profile", "#/profile", "Профиль", "👤"],
];

export function renderNav(current) {
  // Нижняя навигация приложения с подсветкой активного экрана.
  const nav = document.createElement("nav");
  nav.className = "app-nav";
  nav.setAttribute("aria-label", "Основная навигация");
  const list = document.createElement("ul");
  for (const [key, href, label, icon] of ITEMS) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = href;
    if (key === current) {
      link.classList.add("active");
      link.setAttribute("aria-current", "page");
    }
    const glyph = document.createElement("span");
    glyph.className = "nav-icon";
    glyph.textContent = icon;
    const text = document.createElement("span");
    text.textContent = label;
    link.append(glyph, text);
    item.appendChild(link);
    list.appendChild(item);
  }
  nav.appendChild(list);
  return nav;
}
