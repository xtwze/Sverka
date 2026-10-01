import type {
  ImportResult,
  ChatReply,
  ReconciliationGateway,
  Report,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8080";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(
      body?.detail ?? `Backend вернул ошибку HTTP ${response.status}.`,
    );
  }
  return (await response.json()) as T;
}

export const apiGateway: ReconciliationGateway = {
  importData(signal) {
    return request<ImportResult>("/api/import", { method: "POST", signal });
  },
  reconcile(period, signal) {
    return request<Report>(
      `/api/reconcile?period=${encodeURIComponent(period)}`,
      { signal },
    );
  },
  chat(message, period, signal) {
    return request<ChatReply>("/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, period }),
      signal,
    });
  },
};
