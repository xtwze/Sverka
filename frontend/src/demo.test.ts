import { describe, expect, it } from "vitest";
import { demoReport, money } from "./demo";

describe("Демо-ответы соответствуют тестовым данным", () => {
  it("показывает оба расхождения и точные итоги августа", () => {
    const result = demoReport("2026-08", "differences");
    expect(result.source).toEqual({ count: 3, total_kopecks: 1140000 });
    expect(result.postgres).toEqual({ count: 2, total_kopecks: 1015050 });
    expect(result.differences.map((d) => d.record_id)).toEqual([
      "charge-1",
      "charge-2",
    ]);
    expect(result.differences[0].postgres_value).toBeNull();
  });
  it("не переносит августовские расхождения в сентябрь", () => {
    const result = demoReport("2026-09", "differences");
    expect(result.status).toBe("MATCH");
    expect(result.source).toEqual({ count: 1, total_kopecks: 5000 });
    expect(result.differences).toEqual([]);
  });
  it("при ошибке источника не выдаёт совпадение и нулевые итоги", () => {
    const result = demoReport("2026-08", "unavailable");
    expect(result.status).toBe("FAILED");
    expect(result.source).toBeNull();
    expect(result.postgres).toBeNull();
  });
  it("возвращает пустые итоги за месяц без записей", () => {
    expect(demoReport("2026-10", "match").source).toEqual({
      count: 0,
      total_kopecks: 0,
    });
  });
  it("форматирует целые копейки, включая ведущий ноль", () => {
    expect(money(25050)).toBe("250,50 ₽");
    expect(money(1)).toBe("0,01 ₽");
    expect(money(-100)).toBe("−1,00 ₽");
  });
});
