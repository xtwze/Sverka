// Суммы храним в целых копейках. Рубли и остаток форматируем без округления.
export function money(kopecks: number): string {
  const absolute = Math.abs(kopecks);
  const rubles = Math.trunc(absolute / 100).toLocaleString("ru-RU");
  return `${kopecks < 0 ? "−" : ""}${rubles},${String(absolute % 100).padStart(2, "0")} ₽`;
}

export function monthLabel(period: string): string {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period)) return "Выберите месяц";
  const [year, month] = period.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, 1)));
}
