export type Totals = { count: number; total_kopecks: number };
export type Difference = {
  type:
    | "missing_in_postgres"
    | "extra_in_postgres"
    | "amount_mismatch"
    | "account_mismatch";
  record_id: string;
  account_number: string;
  source_value: number | string | null;
  postgres_value: number | string | null;
};
export type Report = {
  run_id: string;
  period: string;
  status: "MATCH" | "MISMATCH" | "FAILED";
  source: Totals | null;
  postgres: Totals | null;
  differences: Difference[];
  error?: string;
  source_mode?: "mock" | "real" | "unknown";
};
export type ImportResult = {
  accounts: number;
  charges: number;
  payments: number;
};
export type ChatReply = { answer: string };

// Интерфейс отображает результат единого Python-сервиса сверки.
export interface ReconciliationGateway {
  importData(signal?: AbortSignal): Promise<ImportResult>;
  reconcile(period: string, signal?: AbortSignal): Promise<Report>;
  chat(message: string, period: string, signal?: AbortSignal): Promise<ChatReply>;
}
