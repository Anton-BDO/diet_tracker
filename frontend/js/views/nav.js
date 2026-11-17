const ITEMS = [
  ["dashboard", "#/dashboard", "Главная",
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>'],
  ["add-food", "#/add-food", "Добавить",
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>'],
  ["stats", "#/stats", "Статистика",
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 20V10M10 20V4M16 20v-7M21 20H3"/></svg>'],
  ["profile", "#/profile", "Профиль",
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 5-5.5 8-5.5s6.5 1.5 8 5.5"/></svg>'],
];

export function renderNav(current) {
  // Нижняя навигация: четыре равные кнопки-карточки.
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
    glyph.setAttribute("aria-hidden", "true");
    glyph.innerHTML = icon;
    const text = document.createElement("span");
    text.textContent = label;
    link.append(glyph, text);
    item.appendChild(link);
    list.appendChild(item);
  }
  nav.appendChild(list);
  return nav;
}
