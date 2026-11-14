import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const tokensCss = readFileSync(resolve(__dirname, "tokens.css"), "utf8");
const designHtml = resolve(__dirname, "../../../context/design/kelper-landing/home/index.html");

function names(css: string): string[] {
  return [...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1] as string);
}

describe("tokens.css", () => {
  it("defines --tap-min as 48px", () => {
    expect(tokensCss).toMatch(/--tap-min:\s*48px;/);
  });

  it("defines every token of the design block", () => {
    const html = readFileSync(designHtml, "utf8");
    const start = html.indexOf("data-dc-design-system-vars");
    const block = html.slice(start, html.indexOf("</style>", start));
    const expected = new Set(names(block));
    expect(expected.size).toBeGreaterThan(70);
    const have = new Set(names(tokensCss));
    expect([...expected].filter((n) => !have.has(n))).toEqual([]);
  });
});
