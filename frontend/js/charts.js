// Canvas-графики без библиотек: учитываем devicePixelRatio и resize.

function setupCanvas(canvas) {
  const ratio = globalThis.devicePixelRatio || 1;
  const width = canvas.clientWidth || 320;
  const height = canvas.clientHeight || 200;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  return { context, width, height };
}

function cssColor(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name).trim() || "#8b9bb4";
}

export function drawCaloriesChart(canvas, { days, normKcal }) {
  const { context, width, height } = setupCanvas(canvas);
  const accent = cssColor("--accent");
  const danger = cssColor("--danger");
  const muted = cssColor("--muted");
  const grid = cssColor("--chart-grid");
  const pad = { top: 12, right: 8, bottom: 22, left: 8 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const maxValue = Math.max(normKcal, ...days.map(day => day.kcal), 1);
  const stepX = plotW / days.length;
  const barWidth = Math.max(8, Math.min(28, stepX * 0.6));

  // Пунктир нормы
  context.strokeStyle = grid;
  context.setLineDash([4, 4]);
  context.beginPath();
  const normY = pad.top + plotH * (1 - normKcal / maxValue);
  context.moveTo(pad.left, normY);
  context.lineTo(width - pad.right, normY);
  context.stroke();
  context.setLineDash([]);

  days.forEach((day, index) => {
    const barH = plotH * (day.kcal / maxValue);
    const x = pad.left + stepX * index + (stepX - barWidth) / 2;
    const y = pad.top + plotH - barH;
    context.fillStyle = day.kcal === 0 ? grid
      : day.is_success ? accent : danger;
    context.beginPath();
    context.roundRect(x, y, barWidth, Math.max(barH, 2), 3);
    context.fill();
    context.fillStyle = muted;
    context.font = "9px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(day.date.slice(5), x + barWidth / 2, height - 8);
  });
  context.textAlign = "left";
  return true;
}

export function drawWeightChart(canvas, points) {
  const { context, width, height } = setupCanvas(canvas);
  if (!points.length) return false;
  const accent = cssColor("--accent");
  const muted = cssColor("--muted");
  const pad = { top: 12, right: 10, bottom: 22, left: 10 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const weights = points.map(point => point.weight_kg);
  const min = Math.min(...weights);
  const max = Math.max(...weights);
  const span = max - min || 1;
  const xOf = index => pad.left
    + (points.length === 1 ? plotW / 2 : (plotW * index) / (points.length - 1));
  const yOf = value => pad.top + plotH * (1 - (value - min) / span);

  context.strokeStyle = accent;
  context.lineWidth = 2;
  context.beginPath();
  points.forEach((point, index) => {
    const x = xOf(index);
    const y = yOf(point.weight_kg);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.stroke();

  context.fillStyle = accent;
  points.forEach((point, index) => {
    context.beginPath();
    context.arc(xOf(index), yOf(point.weight_kg), 3, 0, Math.PI * 2);
    context.fill();
  });

  context.fillStyle = muted;
  context.font = "9px system-ui, sans-serif";
  context.textAlign = "center";
  points.forEach((point, index) => {
    context.fillText(point.date.slice(5), xOf(index), height - 8);
  });
  context.textAlign = "left";
  return true;
}
