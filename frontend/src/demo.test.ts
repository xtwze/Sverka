import { describe, expect, it } from "vitest";
import { differenceValue, money, monthLabel, sourceLabel } from "./demo";

describe("Форматирование данных отчёта", () => {
  it("отличает счёт от суммы и пропущенной записи", () => {
    expect(differenceValue("acc-bob")).toBe("Счёт acc-bob");
    expect(differenceValue(101)).toBe("1,01 ₽");
    expect(differenceValue(null)).toBe("Нет записи");
  });

  it("не выдаёт mock и неизвестный режим за настоящую 1С", () => {
    expect(sourceLabel("mock")).toContain("mock");
    expect(sourceLabel()).toContain("неизвестен");
  });
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
