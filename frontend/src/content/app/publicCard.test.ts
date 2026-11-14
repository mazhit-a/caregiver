import { describe, expect, it } from "vitest";
import { PUBLIC_CARD, cardTitle } from "./publicCard";

describe("public card copy", () => {
  it("has no unfilled placeholders and the neutral section labels", () => {
    expect(JSON.stringify(PUBLIC_CARD)).not.toMatch(/\{[A-Za-z]+\}/);
    expect(Object.values(PUBLIC_CARD.sections)).toEqual([
      "Enjoys", "Calms", "Try to avoid", "Daily rhythm", "Phrases that work", "Contacts", "Helplines",
    ]);
    expect(PUBLIC_CARD.notFound.title).toBe("We can't find this card");
    expect(PUBLIC_CARD.revoked.title).toBe("This card is no longer shared");
  });
  it("composes the title from the display name only", () => {
    expect(cardTitle("Margaret")).toBe("What works with Margaret");
    expect(cardTitle("")).toBe("Care card");
  });
});
