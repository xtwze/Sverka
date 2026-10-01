import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MarkdownMessage } from "./MarkdownMessage";

describe("MarkdownMessage", () => {
  it("renders formatting, lists and GFM tables", () => {
    const html = renderToStaticMarkup(
      <MarkdownMessage text={"**Итог**\n\n- Один платёж\n\n| Источник | Сумма |\n| --- | ---: |\n| 1С | 100 |"} />,
    );

    expect(html).toContain("<strong>Итог</strong>");
    expect(html).toContain("<li>Один платёж</li>");
    expect(html).toContain("<table>");
    expect(html).toContain('<td style="text-align:right">100</td>');
  });

  it("does not render HTML, images or unsafe links from a model answer", () => {
    const html = renderToStaticMarkup(
      <MarkdownMessage text={"<script>alert(1)</script>\n\n![image](https://example.com/x.png)\n\n[link](javascript:alert(1))"} />,
    );

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("javascript:");
  });
});
