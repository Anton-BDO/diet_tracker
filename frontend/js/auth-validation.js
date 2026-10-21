const ACTIVITIES = [1.2, 1.375, 1.55, 1.725, 1.9];

export function localDate(value = new Date()) {
  return [value.getFullYear(), String(value.getMonth() + 1).padStart(2, "0"),
    String(value.getDate()).padStart(2, "0")].join("-");
}

export function ageOn(birthDate, today = new Date()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) return NaN;
  const [year, month, day] = birthDate.split("-").map(Number);
  const birth = new Date(year, month - 1, day);
  if (birth.getFullYear() !== year || birth.getMonth() !== month - 1
      || birth.getDate() !== day) return NaN;
  const birthdayPassed = today.getMonth() > month - 1
    || (today.getMonth() === month - 1 && today.getDate() >= day);
  return today.getFullYear() - year - (birthdayPassed ? 0 : 1);
}

export function validateAuth(mode, values, today = new Date()) {
  const errors = {};
  const data = {
    email: String(values.email ?? "").trim(),
    password: String(values.password ?? ""),
  };
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    errors.email = "Укажите корректную электронную почту";
  }
  if (!data.password) errors.password = "Введите пароль";
  if (mode === "register") {
    if (data.password.length < 8) errors.password = "Минимум 8 символов";
    data.name = String(values.name ?? "").trim();
    data.sex = String(values.sex ?? "");
    data.birth_date = String(values.birth_date ?? "");
    data.height_cm = Number(values.height_cm);
    data.weight_kg = Number(values.weight_kg);
    data.activity = Number(values.activity);
    data.goal = String(values.goal ?? "");
    if (!data.name) errors.name = "Введите имя";
    if (!["male", "female"].includes(data.sex)) errors.sex = "Выберите пол";
    const age = ageOn(data.birth_date, today);
    if (!Number.isFinite(age) || age < 14 || age > 100) {
      errors.birth_date = "Возраст должен быть от 14 до 100 лет";
    }
    if (!Number.isFinite(data.height_cm) || data.height_cm < 100
        || data.height_cm > 250) errors.height_cm = "Укажите рост от 100 до 250 см";
    if (!Number.isFinite(data.weight_kg) || data.weight_kg < 30
        || data.weight_kg > 300) errors.weight_kg = "Укажите вес от 30 до 300 кг";
    if (!ACTIVITIES.includes(data.activity)) errors.activity = "Выберите активность";
    if (!["lose", "keep", "gain"].includes(data.goal)) errors.goal = "Выберите цель";
  }
  return { data, errors };
}
