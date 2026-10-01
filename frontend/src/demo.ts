import type { ReconciliationGateway, Report, Scenario } from "./types";

export const DEMO_PERIOD = "2026-08";

// Готовые ответы на основе тестовых данных. Настоящую сверку позже выполнит Python backend.
export function demoReport(period: string, scenario: Scenario): Report {
  const base = {
    run_id: `demo-${crypto.randomUUID()}`,
    period,
    differences: [],
  };
  if (scenario === "unavailable") {
    return {
      ...base,
      status: "FAILED",
      source: null,
      postgres: null,
      error:
        "Не удалось получить данные из 1С. Сверка не завершена; совпадение данных не подтверждено.",
    };
  }
  const totals =
    period === "2026-08"
      ? { count: 3, total_kopecks: 1140000 }
      : period === "2026-09"
        ? { count: 1, total_kopecks: 5000 }
        : { count: 0, total_kopecks: 0 };
  if (period !== DEMO_PERIOD || scenario === "match") {
    return {
      ...base,
      status: "MATCH",
      source: { ...totals },
      postgres: { ...totals },
    };
  }
  return {
    ...base,
    status: "MISMATCH",
    source: totals,
    postgres: { count: 2, total_kopecks: 1015050 },
    differences: [
      {
        type: "missing_in_postgres",
        record_id: "charge-1",
        account_number: "10001",
        source_value: 125050,
        postgres_value: null,
      },
      {
        type: "amount_mismatch",
        record_id: "charge-2",
        account_number: "10001",
        source_value: 24950,
        postgres_value: 25050,
      },
    ],
  };
}

// Задержка нужна только для показа загрузки. При закрытии страницы отменяем ожидание.
function delay(signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, 850);
    signal?.addEventListener("abort", abort, { once: true });
  });
}

// Здесь позже заменим демо-ответы запросами к API, сохранив интерфейс страницы.
export const demoGateway: ReconciliationGateway = {
  async importData(scenario, signal) {
    await delay(signal);
    if (scenario === "unavailable")
      throw new Error("1С недоступна. Импорт не выполнен. Данные не изменены.");
    return { accounts: 2, charges: 4, payments: 1 };
  },
  async reconcile(period, scenario, signal) {
    await delay(signal);
    return demoReport(period, scenario);
  },
};

// Суммы храним в целых копейках. Рубли и остаток форматируем отдельно, без округления.
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
