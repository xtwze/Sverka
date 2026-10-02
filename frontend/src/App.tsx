import { useEffect, useRef, useState } from "react";
import {
  ArrowsLeftRight,
  ArrowRight,
  ArrowClockwise,
  Database,
  DownloadSimple,
  Check,
  CheckCircle,
  WarningCircle,
  CalendarBlank,
  Rows,
  CircleNotch,
  Plug,
  Minus,
  ChatCircleText,
  PaperPlaneTilt,
} from "@phosphor-icons/react";
import { apiGateway, getSourceInfo } from "./api";
import { differenceValue, money, monthLabel, sourceLabel } from "./demo";
import { MarkdownMessage } from "./MarkdownMessage";
import type { Report } from "./types";

export default function App() {
  // На странице хранится выбранный период и последний ответ backend.
  const [period, setPeriod] = useState("2026-08");
  const [connectionLabel, setConnectionLabel] = useState("Проверяем подключение…");
  useEffect(() => {
    const controller = new AbortController();
    void getSourceInfo(controller.signal).then((info) => {
      if (!controller.signal.aborted) setConnectionLabel(sourceLabel(info.mode));
    }).catch(() => {
      if (!controller.signal.aborted) setConnectionLabel("API недоступен");
    });
    return () => controller.abort();
  }, []);
  const [report, setReport] = useState<Report | null>(null);
  const [pending, setPending] = useState<"import" | "reconcile" | null>(null);
  const [notice, setNotice] = useState<{
    kind: "success" | "error";
    text: string;
  } | null>(null);
  const request = useRef<AbortController | null>(null);
  const chatRequest = useRef<AbortController | null>(null);
  const [question, setQuestion] = useState("");
  const [chatPending, setChatPending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [messages, setMessages] = useState<{
    role: "user" | "assistant";
    text: string;
  }[]>([]);
  const validPeriod = /^\d{4}-(0[1-9]|1[0-2])$/.test(period);
  // Отменяем незавершённый запрос, если пользователь закрыл страницу.
  useEffect(() => () => {
    request.current?.abort();
    chatRequest.current?.abort();
  }, []);

  // Старый отчёт нельзя показывать как результат для нового периода или сценария.
  function invalidate() {
    setReport(null);
    setNotice(null);
    chatRequest.current?.abort();
    setChatPending(false);
    setMessages([]);
    setChatError(null);
  }
  async function sendQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = question.trim();
    if (!message || !validPeriod || chatPending || pending) return;
    const controller = new AbortController();
    chatRequest.current = controller;
    setQuestion("");
    setMessages((current) => [...current, { role: "user", text: message }]);
    setChatError(null);
    setChatPending(true);
    try {
      const reply = await apiGateway.chat(message, period, controller.signal);
      if (!controller.signal.aborted) {
        setMessages((current) => [...current, { role: "assistant", text: reply.answer }]);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setChatError(error instanceof Error ? error.message : "Не удалось получить ответ.");
      }
    } finally {
      if (!controller.signal.aborted) setChatPending(false);
    }
  }
  // Обе кнопки используют один обработчик, чтобы одинаково показывать загрузку и ошибки.
  async function run(operation: "import" | "reconcile") {
    if (pending || (operation === "reconcile" && !validPeriod)) return;
    const controller = new AbortController();
    request.current = controller;
    setPending(operation);
    invalidate();
    try {
      if (operation === "import") {
        const result = await apiGateway.importData(controller.signal);
        setNotice({
          kind: "success",
          text: `Импорт завершён: ${result.accounts} счёта, ${result.charges} начисления, ${result.payments} платёж. Теперь запустите сверку.`,
        });
      } else {
        setReport(
          await apiGateway.reconcile(period, controller.signal),
        );
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setNotice({
        kind: "error",
        text:
          error instanceof Error
            ? error.message
            : "Операция не выполнена. Повторите попытку.",
      });
    } finally {
      if (!controller.signal.aborted) setPending(null);
    }
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Перейти к сверке
      </a>
      <header className="site-header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-mark">
              <ArrowsLeftRight size={23} weight="bold" />
            </span>
            <span>
              сверка<span className="brand-dot">.</span>
            </span>
          </div>
          <span className="header-description">Контроль переноса данных</span>
          <span className="demo-badge">
            <Plug size={15} />
            {connectionLabel}
          </span>
        </div>
      </header>
      <main id="main" className="workspace">
        <div className="page-heading">
          <div>
            <h1>Сверка начислений</h1>
            <p>Проверьте, что записи и суммы перенесены без расхождений.</p>
          </div>
          <div className="source-route">
            <span>Источник</span>
            <ArrowRight size={18} />
            <span>
              <Database size={17} />
              PostgreSQL
            </span>
          </div>
        </div>

        <section className="controls" aria-label="Параметры сверки">
          <div className="period-field">
            <label htmlFor="period">Период начислений</label>
            <div className="month-control">
              <CalendarBlank size={20} />
              <input
                id="period"
                type="month"
                min="1900-01"
                max="9999-12"
                value={period}
                disabled={!!pending}
                onChange={(e) => {
                  setPeriod(e.target.value);
                  invalidate();
                }}
                aria-invalid={!validPeriod}
              />
            </div>
          </div>
          <p className="period-note">
            Сверяем начисления за месяц.
            <br />
            Счета и платежи входят в импорт.
          </p>
          <div className="action-buttons">
            <button
              className="button secondary"
              disabled={!!pending}
              onClick={() => void run("import")}
            >
              {pending === "import" ? (
                <CircleNotch className="spin" size={19} />
              ) : (
                <DownloadSimple size={19} />
              )}
              {pending === "import" ? "Импортируем…" : "Импортировать"}
            </button>
            <button
              className="button primary"
              disabled={!!pending || !validPeriod}
              onClick={() => void run("reconcile")}
            >
              {pending === "reconcile" ? (
                <CircleNotch className="spin" size={19} />
              ) : (
                <ArrowsLeftRight size={19} />
              )}
              {pending === "reconcile" ? "Сверяем…" : "Запустить сверку"}
            </button>
          </div>
        </section>
        {!validPeriod && (
          <p className="field-error" role="alert">
            Укажите месяц для сверки.
          </p>
        )}
        {notice && (
          <div
            className={`notice ${notice.kind}`}
            role={notice.kind === "error" ? "alert" : "status"}
          >
            {notice.kind === "error" ? (
              <WarningCircle size={21} />
            ) : (
              <CheckCircle size={21} />
            )}
            <p>{notice.text}</p>
          </div>
        )}

        <div className="work-grid">
          <section
            className="report-panel"
            aria-labelledby="report-title"
            aria-busy={!!pending}
          >
            <div className="panel-heading">
              <h2 id="report-title">Результат сверки</h2>
              <span className="report-period">{monthLabel(period)}</span>
            </div>
            <div aria-live="polite" aria-atomic="true" className="sr-only">
              {pending
                ? pending === "import"
                  ? "Импорт выполняется"
                  : "Сверка выполняется"
                : report
                  ? report.status === "FAILED"
                    ? "Сверка не завершена"
                    : report.status === "MATCH"
                      ? "Расхождений нет"
                      : `Найдено расхождений: ${report.differences.length}`
                  : "Сверка ещё не запускалась"}
            </div>
            {pending ? (
              <Loading operation={pending} />
            ) : report ? (
              <ReportView report={report} retry={() => void run("reconcile")} />
            ) : (
              <div className="empty-state">
                <div className="empty-symbol">
                  <Rows size={32} weight="light" />
                  <span>
                    <ArrowsLeftRight size={16} />
                  </span>
                </div>
                <h3>Всё готово к проверке</h3>
                <p>
                  Выберите месяц и запустите сверку.
                  <br />
                  Здесь появятся итоги и различия по каждой записи.
                </p>
                <div className="empty-checks">
                  <span>
                    <Check size={14} />
                    Наличие записей
                  </span>
                  <span>
                    <Check size={14} />
                    Точные суммы
                  </span>
                  <span>
                    <Check size={14} />
                    Общие итоги
                  </span>
                </div>
              </div>
            )}
          </section>

          <aside className="context-rail" aria-label="Порядок работы">
            <section className="how-to">
              <h2>Как провести сверку</h2>
              <ol>
                <li>
                  <span>1</span>
                  <div>
                    <h3>Импортируйте данные</h3>
                    <p>Перенесите записи источника в PostgreSQL.</p>
                  </div>
                </li>
                <li>
                  <span>2</span>
                  <div>
                    <h3>Запустите проверку</h3>
                    <p>Сравните начисления за выбранный месяц.</p>
                  </div>
                </li>
                <li>
                  <span>3</span>
                  <div>
                    <h3>Проверьте расхождения</h3>
                    <p>Найдите запись по ID и сравните суммы.</p>
                  </div>
                </li>
              </ol>
            </section>
          </aside>
        </div>
        <section className="chat-panel" aria-labelledby="chat-title">
          <div className="chat-heading">
            <span className="chat-icon"><ChatCircleText size={22} /></span>
            <div>
              <h2 id="chat-title">Помощник по сверке</h2>
              <p>Задайте вопрос о начислениях или платежах за {monthLabel(period)}.</p>
            </div>
          </div>
          <div className="chat-messages" role="log" aria-live="polite" aria-label="Сообщения чата">
            {messages.length === 0 && (
              <p className="chat-empty">Например: «Какие расхождения найдены?» или «Сколько было платежей?»</p>
            )}
            {messages.map((item, index) => (
              <div className={`chat-message ${item.role}`} key={index}>
                <span>{item.role === "user" ? "Вы" : "Помощник"}</span>
                {item.role === "assistant" ? (
                  <MarkdownMessage text={item.text} />
                ) : (
                  <p>{item.text}</p>
                )}
              </div>
            ))}
            {chatPending && <p className="chat-wait"><CircleNotch className="spin" size={16} /> Сверяем и готовим ответ…</p>}
          </div>
          {chatError && <p className="chat-error" role="alert">{chatError}</p>}
          <form className="chat-form" onSubmit={(event) => void sendQuestion(event)}>
            <label className="sr-only" htmlFor="chat-question">Вопрос по сверке</label>
            <input id="chat-question" value={question} maxLength={1000}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Спросите о результатах сверки…" />
            <button className="button primary" type="submit" disabled={!question.trim() || !validPeriod || chatPending || !!pending}>
              <PaperPlaneTilt size={18} /> Отправить
            </button>
          </form>
          <p className="chat-disclosure">Для ответа результаты сверки передаются внешней модели. Помощник только читает данные.</p>
        </section>
        <footer className="page-footer">
          <span>
            <Plug size={15} />
            {connectionLabel}
          </span>
          <span>Источник → PostgreSQL → сверка</span>
        </footer>
      </main>
    </>
  );
}

function Loading({ operation }: { operation: "import" | "reconcile" }) {
  return (
    <div className="loading-state">
      <div className="loading-header">
        <CircleNotch size={23} className="spin" />
        <div>
          <h3>
            {operation === "import"
              ? "Импортируем записи"
              : "Сравниваем начисления"}
          </h3>
          <p>
            {operation === "import"
              ? "Счета, начисления и платежи"
              : "Проверяем наличие записей, суммы и итоги"}
          </p>
        </div>
      </div>
      <div className="skeleton-grid" aria-hidden="true">
        <div />
        <div />
      </div>
      <div className="skeleton-line" />
      <div className="skeleton-line" />
      <p className="loading-note">Операция выполняется на сервере</p>
    </div>
  );
}

function differenceLabel(type: Report["differences"][number]["type"]): string {
  const labels = {
    missing_in_postgres: "Нет в PostgreSQL",
    extra_in_postgres: "Лишняя запись",
    amount_mismatch: "Отличается сумма",
    account_mismatch: "Другой лицевой счёт",
  };
  return labels[type];
}

// Компонент только отображает готовый отчёт: он не сравнивает записи источников.
function ReportView({ report, retry }: { report: Report; retry: () => void }) {
  const failed = report.status === "FAILED";
  const matched = report.status === "MATCH";
  const empty =
    matched && report.source?.count === 0 && report.postgres?.count === 0;
  return (
    <div className="report-content">
      <div
        className={`result-banner ${failed ? "error" : matched ? "success" : "warning"}`}
      >
        {failed ? (
          <WarningCircle size={24} />
        ) : matched ? (
          <CheckCircle size={24} />
        ) : (
          <ArrowsLeftRight size={24} />
        )}
        <div>
          <h3>
            {failed
              ? "Сверка не завершена"
              : matched
                ? "Расхождений нет"
                : `Найдено расхождений: ${report.differences.length}`}
          </h3>
          <p>
            {failed
              ? report.error
              : empty
                ? "В обоих источниках нет начислений за выбранный месяц."
                : matched
                  ? "Все записи и суммы за выбранный месяц совпадают."
                  : "Проверьте каждую запись в таблице ниже."}
          </p>
        </div>
        <span className="status-tag">
          {failed ? "Ошибка" : matched ? "Совпадает" : "Есть различия"}
        </span>
      </div>
      {failed ? (
        <div className="error-body">
          <div className="error-icon">
            <Plug size={32} />
          </div>
          <h3>Нет ответа от источника</h3>
          <p>
            Проверьте доступность 1С и повторите попытку. Результат сверки
            нельзя считать успешным.
          </p>
          <button className="button secondary" onClick={retry}>
            <ArrowClockwise size={18} />
            Повторить сверку
          </button>
        </div>
      ) : (
        <>
          <div className="totals" aria-label="Итоги по источникам">
            <div className="totals-source">
              <div className="source-title">
                <span className="source-monogram">1С</span>
                <div>
                  <h3>{sourceLabel(report.source_mode)}</h3>
                  <p>Исходные начисления</p>
                </div>
              </div>
              <div className="total-amount">
                {money(report.source!.total_kopecks)}
              </div>
              <p className="record-count">
                Количество записей <strong>{report.source!.count}</strong>
              </p>
            </div>
            <div className="totals-source">
              <div className="source-title">
                <span className="source-monogram pg">
                  <Database size={22} />
                </span>
                <div>
                  <h3>PostgreSQL</h3>
                  <p>Перенесённые начисления</p>
                </div>
              </div>
              <div className="total-amount">
                {money(report.postgres!.total_kopecks)}
              </div>
              <p className="record-count">
                Количество записей <strong>{report.postgres!.count}</strong>
              </p>
            </div>
          </div>
          <div className="difference-total">
            <span>
              Разница итогов <small>Источник − PostgreSQL</small>
            </span>
            <strong>
              {money(
                report.source!.total_kopecks - report.postgres!.total_kopecks,
              )}
            </strong>
          </div>
          <div className="differences-heading">
            <h3>Расхождения по записям</h3>
            <span>{report.differences.length}</span>
          </div>
          {matched ? (
            <div className="matched-state">
              <CheckCircle size={23} />
              <div>
                <strong>
                  {empty
                    ? "Нет записей для сравнения"
                    : "Все начисления совпадают"}
                </strong>
                <p>
                  {empty
                    ? "За выбранный месяц начисления отсутствуют."
                    : "Отсутствующих записей и различий в суммах не найдено."}
                </p>
              </div>
            </div>
          ) : (
            <div
              className="table-wrap"
              role="region"
              aria-label="Таблица расхождений"
              tabIndex={0}
            >
              <table>
                <caption className="sr-only">
                  Расхождения начислений за {monthLabel(report.period)}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Запись / счёт</th>
                    <th scope="col">Тип расхождения</th>
                    <th scope="col" className="numeric">
                      В источнике
                    </th>
                    <th scope="col" className="numeric">
                      В PostgreSQL
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {report.differences.map((diff) => (
                    <tr key={`${diff.record_id}:${diff.type}`}>
                      <td>
                        <code>{diff.record_id}</code>
                        <small>Счёт {diff.account_number}</small>
                      </td>
                      <td>
                        <span
                          className={`difference-type ${diff.type === "missing_in_postgres" ? "missing" : "amount"}`}
                        >
                          {differenceLabel(diff.type)}
                        </span>
                      </td>
                      <td className="numeric">
                        {differenceValue(diff.source_value)}
                      </td>
                      <td className="numeric">
                        {diff.postgres_value === null ? (
                          <span className="no-record">
                            <Minus size={14} />
                            Нет записи
                          </span>
                        ) : (
                          <strong className="changed-value">
                            {differenceValue(diff.postgres_value)}
                          </strong>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      <div className="run-meta">
        <span>ID запуска</span>
        <code>{report.run_id}</code>
        <span className="demo-report-label">Отчёт API</span>
      </div>
    </div>
  );
}
