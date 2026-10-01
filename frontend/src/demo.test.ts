import { describe, expect, it } from "vitest";
import { money, monthLabel } from "./demo";

describe("Форматирование данных отчёта", () => {
  it("не теряет копейки", () => {
    expect(money(125050)).toContain("50 ₽");
  });

  it("показывает отрицательную разницу", () => {
    expect(money(-1)).toBe("−0,01 ₽");
  });

  it("форматирует корректный месяц", () => {
    expect(monthLabel("2026-08")).toContain("2026");
  });

  it("отклоняет некорректный месяц", () => {
    expect(monthLabel("2026-13")).toBe("Выберите месяц");
  });
});
