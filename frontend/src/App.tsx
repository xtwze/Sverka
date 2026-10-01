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
  Info,
  CalendarBlank,
  Rows,
  Flask,
  CircleNotch,
  Plug,
  Minus,
} from "@phosphor-icons/react";
import { demoGateway, DEMO_PERIOD, money, monthLabel } from "./demo";
import type { Report, Scenario } from "./types";

const scenarios: { id: Scenario; title: string; detail: string }[] = [
  {
    id: "differences",
    title: "Два расхождения",
    detail: "Пропуск записи и изменение суммы",
  },
  {
    id: "match",
    title: "Данные совпадают",
    detail: "Одинаковые начисления в источниках",
  },
  {
    id: "unavailable",
    title: "1С недоступна",
    detail: "Ошибка получения данных",
  },
];

export default function App() {
  // На странице хранится выбранный период, сценарий демонстрации и последний ответ.
  const [period, setPeriod] = useState(DEMO_PERIOD);
  const [scenario, setScenario] = useState<Scenario>("differences");
  const [report, setReport] = useState<Report | null>(null);
  const [pending, setPending] = useState<"import" | "reconcile" | null>(null);
  const [notice, setNotice] = useState<{
    kind: "success" | "error";
    text: string;
  } | null>(null);
  const request = useRef<AbortController | null>(null);
  const validPeriod = /^\d{4}-(0[1-9]|1[0-2])$/.test(period);
  // Отменяем незавершённый запрос, если пользователь закрыл страницу.
  useEffect(() => () => request.current?.abort(), []);

  // Старый отчёт нельзя показывать как результат для нового периода или сценария.
  function invalidate() {
    setReport(null);
    setNotice(null);
  }
  // Обе кнопки используют один обработчик, чтобы одинаково показывать загрузку и ошибки.
  async function run(operation: "import" | "reconcile") {
    if (pending || (operation === "reconcile" && !validPeriod)) return;
    const controller = new AbortController();
    request.current = controller;
    setPending(operation);
    setNotice(null);
    setReport(null);
    try {
      if (operation === "import") {
        const result = await demoGateway.importData(
          scenario,
          controller.signal,
        );
        // В демонстрации импорт восстанавливает исходные данные и убирает расхождения.
        setScenario("match");
        setNotice({
          kind: "success",
          text: `Демо-импорт завершён: ${result.accounts} счёта, ${result.charges} начисления, ${result.payments} платёж. Данные восстановлены. Теперь запустите сверку.`,
        });
      } else {
        setReport(
          await demoGateway.reconcile(period, scenario, controller.signal),
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
            <Flask size={15} />
            Демо-режим
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
            <span>1С</span>
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
                      : "Найдено два расхождения"
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

          <aside
            className="context-rail"
            aria-label="Демонстрация и порядок работы"
          >
            <section className="demo-panel">
              <div className="aside-heading">
                <Flask size={19} />
                <h2>Демонстрационный стенд</h2>
              </div>
              <p>
                Backend ещё не подключён. Все операции выполняются на примерах
                данных.
              </p>
              <fieldset disabled={!!pending}>
                <legend>Сценарий для проверки</legend>
                {scenarios.map((item) => (
                  <label
                    className={`scenario ${scenario === item.id ? "selected" : ""}`}
                    key={item.id}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value={item.id}
                      checked={scenario === item.id}
                      onChange={() => {
                        setScenario(item.id);
                        invalidate();
                      }}
                    />
                    <span>
                      <strong>{item.title}</strong>
                      <small>{item.detail}</small>
                    </span>
                  </label>
                ))}
              </fieldset>
              <div className="demo-footnote">
                <Info size={16} />
                <span>
                  Расхождения заданы за август 2026. В сентябре — одна запись
                  без различий.
                </span>
              </div>
            </section>
            <section className="how-to">
              <h2>Как провести сверку</h2>
              <ol>
                <li>
                  <span>1</span>
                  <div>
                    <h3>Импортируйте данные</h3>
                    <p>Перенесите записи из 1С в PostgreSQL.</p>
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
        <footer className="page-footer">
          <span>
            <Plug size={15} />
            Интерфейс работает на демо-данных
          </span>
          <span>1С и PostgreSQL пока не подключены</span>
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
      <p className="loading-note">Демонстрация выполнения операции</p>
    </div>
  );
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
                : "Найдено 2 расхождения"}
          </h3>
          <p>
            {failed
              ? report.error
              : empty
                ? "В обоих источниках нет начислений за выбранный месяц."
                : matched
                  ? "Все записи и суммы за выбранный месяц совпадают."
                  : "Одна запись отсутствует, у другой отличается сумма."}
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
          <small>
            В демо выберите другой сценарий, чтобы восстановить доступ.
          </small>
        </div>
      ) : (
        <>
          <div className="totals" aria-label="Итоги по источникам">
            <div className="totals-source">
              <div className="source-title">
                <span className="source-monogram">1С</span>
                <div>
                  <h3>Источник 1С</h3>
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
              Разница итогов <small>1С − PostgreSQL</small>
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
                    ? "В демо данные есть за август и сентябрь 2026 года."
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
                      В 1С
                    </th>
                    <th scope="col" className="numeric">
                      В PostgreSQL
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {report.differences.map((diff) => (
                    <tr key={diff.record_id}>
                      <td>
                        <code>{diff.record_id}</code>
                        <small>Счёт {diff.account_number}</small>
                      </td>
                      <td>
                        <span
                          className={`difference-type ${diff.type === "missing_in_postgres" ? "missing" : "amount"}`}
                        >
                          {diff.type === "missing_in_postgres"
                            ? "Нет в PostgreSQL"
                            : "Отличается сумма"}
                        </span>
                      </td>
                      <td className="numeric">
                        {diff.source_value === null
                          ? "Нет записи"
                          : money(diff.source_value)}
                      </td>
                      <td className="numeric">
                        {diff.postgres_value === null ? (
                          <span className="no-record">
                            <Minus size={14} />
                            Нет записи
                          </span>
                        ) : (
                          <strong className="changed-value">
                            {money(diff.postgres_value)}
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
        <span className="demo-report-label">Демо-отчёт</span>
      </div>
    </div>
  );
}
