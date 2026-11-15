import { describe, expect, it } from "vitest";
import { CARD_STATUS_LABEL, CARE_CARD_LIMITS, CARE_CARD_TEXT } from "./careCard";

describe("care card strings", () => {
  it("has a status word for every status", () => {
    expect(Object.keys(CARD_STATUS_LABEL).sort()).toEqual(
      ["not_published", "published", "revoked", "update_available"].sort(),
    );
    expect(CARD_STATUS_LABEL.not_published).toBe("Not shared yet");
    expect(CARD_STATUS_LABEL.published).toBe("Shared by link");
    expect(CARD_STATUS_LABEL.update_available).toBe("New phrases to add");
    expect(CARD_STATUS_LABEL.revoked).toBe("No longer shared");
  });

  it("holds no placeholder, countdown or sales wording", () => {
    const all = [
      ...Object.values(CARD_STATUS_LABEL),
      ...Object.values(CARE_CARD_TEXT).map(String).filter((v) => !v.includes("=>")),
      CARE_CARD_TEXT.pickerCount(3),
      CARE_CARD_TEXT.newPhrasesMany(2),
      CARE_CARD_TEXT.lastOpened("Nov 3"),
    ].join(" ");
    expect(all).not.toMatch(/[{}]/);
    expect(all.toLowerCase()).not.toMatch(/per day|limited time|hurry|discount|special offer/);
  });

  it("limit is 10", () => {
    expect(CARE_CARD_LIMITS.phrases).toBe(10);
  });
});
