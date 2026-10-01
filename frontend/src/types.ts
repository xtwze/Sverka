export type Totals = { count: number; total_kopecks: number };
export type Difference = {
  type:
    | "missing_in_postgres"
    | "extra_in_postgres"
    | "amount_mismatch"
    | "account_mismatch";
  record_id: string;
  account_number: string;
  source_value: number | null;
  postgres_value: number | null;
};
export type Report = {
  run_id: string;
  period: string;
  status: "MATCH" | "MISMATCH" | "FAILED";
  source: Totals | null;
  postgres: Totals | null;
  differences: Difference[];
  error?: string;
};
export type ImportResult = {
  accounts: number;
  charges: number;
  payments: number;
};

// Контракт для интерфейса. Реальная сверка будет выполняться в Python backend.
export interface ReconciliationGateway {
  importData(signal?: AbortSignal): Promise<ImportResult>;
  reconcile(period: string, signal?: AbortSignal): Promise<Report>;
}
