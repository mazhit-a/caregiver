import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { putProfile, publishCareCard, revokeCareCard, savePhrase } from "../../../api/app";
import { CARD_SNAPSHOT_KEYS } from "../../../api/appTypes";
import { clearToken, setToken } from "../../../api/session";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import { registerFakeArea, unregisterFakeArea } from "../../../test/fakeApp/registry";
import CareCardPage from "./CareCardPage";
import { WithAppCopy } from "../../../test/withAppCopy";

let api: FakeApi;
function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => void data.delete(k),
    setItem: (k, v) => void data.set(k, v),
  };
}

beforeEach(() => {
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  clearToken();
  api = installFakeApi();
  setToken(signIn(api));
});
afterEach(() => {
  unregisterFakeArea("careCardTest");
  vi.restoreAllMocks();
  api.restore();
});

async function open() {
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter>
      <WithAppCopy><CareCardPage /></WithAppCopy>
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { level: 1, name: "Mom's care card" });
  await screen.findByText(/^Status:/);
  return { user, view };
}

const status = (): string => screen.getByText(/^(Not shared yet|Shared by link|New phrases to add|No longer shared)$/).textContent ?? "";
const callCount = (method: string): number => api.calls.filter((c) => c.method === method && c.path === "/care-card").length;

describe("care card, not shared yet", () => {
  it("shows the status, the preview, the sharing sentence and Create private link", async () => {
    const { view } = await open();
    expect(status()).toBe("Not shared yet");
    expect(screen.getByRole("heading", { level: 3, name: "Mom" })).toBeTruthy();
    expect(screen.getByText(/Anyone who has the link can open it until you stop sharing/)).toBeTruthy();
    expect(screen.getByText(/You have no saved phrases yet/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Create private link" })).toBeTruthy();
    expect(screen.queryByLabelText("Private link")).toBeNull();
    expect(screen.queryByRole("button", { name: "Stop sharing" })).toBeNull();
    expect(view.container.textContent).not.toMatch(/[{}]/);
  });

  it("publishing with no phrases is allowed, then the link appears and copies", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Create private link" }));
    const link = (await screen.findByLabelText("Private link")) as HTMLInputElement;
    expect(status()).toBe("Shared by link");
    expect(link.readOnly).toBe(true);
    expect(link.value).toMatch(/\/card\//);
    expect(screen.getByText("Not opened yet")).toBeTruthy();
    expect(callCount("POST")).toBe(1);

    const write = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
    await user.click(screen.getByRole("button", { name: "Copy link" }));
    expect(write).toHaveBeenCalledWith(link.value);
    expect(await screen.findByText("Link copied")).toBeTruthy();
  });

  it("copy falls back to selecting the text when the Clipboard API fails", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Create private link" }));
    await screen.findByLabelText("Private link");
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
    await user.click(screen.getByRole("button", { name: "Copy link" }));
    expect(await screen.findByText("Press Ctrl+C or Cmd+C to copy.")).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByLabelText("Private link"));
  });

  it("sends the chosen phrases, counts them live and shows no link in title, URL, history or console", async () => {
    const phrase = await savePhrase({ text: "No rush. Take my arm?", source: "scenario" });
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) => vi.spyOn(console, m));
    const { user } = await open();
    expect(screen.getByText("0 of 10 chosen")).toBeTruthy();
    await user.click(screen.getByRole("checkbox", { name: "No rush. Take my arm?" }));
    expect(screen.getByText("1 of 10 chosen")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Create private link" }));
    const link = (await screen.findByLabelText("Private link")) as HTMLInputElement;
    const body = api.calls.find((c) => c.method === "POST" && c.path === "/care-card");
    expect(body).toBeTruthy();
    expect((screen.getByRole("checkbox", { name: "No rush. Take my arm?" }) as HTMLInputElement).checked).toBe(true);
    expect(phrase.id).toBeTruthy();
    const id = link.value.split("/card/")[1] ?? "";
    expect(id.length).toBeGreaterThan(0);
    expect(document.title).not.toContain(id);
    expect(window.location.href).not.toContain(id);
    expect(JSON.stringify(window.history.state)).not.toContain(id);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("limits the picker to 10 phrases", async () => {
    for (let i = 0; i < 11; i++) await savePhrase({ text: `Phrase ${i}`, source: "scenario" });
    const { user } = await open();
    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes.length).toBe(11);
    for (const box of boxes.slice(0, 10)) await user.click(box);
    expect(screen.getByText(/10 of 10 chosen/)).toBeTruthy();
    expect(boxes[10]?.disabled).toBe(true);
  });
});

describe("care card, shared", () => {
  beforeEach(async () => {
    await publishCareCard([]);
  });

  it("published: link, last opened, update and stop sharing", async () => {
    await open();
    expect(status()).toBe("Shared by link");
    expect(screen.getByLabelText("Private link")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Update the card" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Stop sharing" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Create private link" })).toBeNull();
  });

  it("update_available: shows the nudge and Update re-snapshots", async () => {
    await putProfile({ calms: ["tea", "music"] });
    const { user } = await open();
    expect(status()).toBe("New phrases to add");
    await user.click(screen.getByRole("button", { name: "Update the card" }));
    await waitFor(() => expect(status()).toBe("Shared by link"));
    expect(callCount("PUT")).toBe(1);
  });

  it("revoke asks first, Keep sharing changes nothing, confirming ends the link and offers a new one", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Stop sharing" }));
    expect(screen.getByRole("alertdialog", { name: "Stop sharing this card?" })).toBeTruthy();
    expect(screen.getByText(/The link stops working right away/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Keep sharing" }));
    expect(callCount("DELETE")).toBe(0);
    expect(status()).toBe("Shared by link");

    await user.click(screen.getByRole("button", { name: "Stop sharing" }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(dialog.querySelector("button:last-of-type") as HTMLElement);
    await waitFor(() => expect(status()).toBe("No longer shared"));
    expect(screen.getByText("This link no longer works.")).toBeTruthy();
    expect(screen.queryByLabelText("Private link")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Create a new private link" }));
    await waitFor(() => expect(status()).toBe("Shared by link"));
  });

  it("a 409 card_already_published refreshes the page with a plain message", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Stop sharing" }));
    registerFakeArea("careCardTest", [
      (req) =>
        req.method === "DELETE" && req.path === "/care-card"
          ? { status: 409, body: { error: { code: "card_not_published", message: "x", details: {} } } }
          : undefined,
    ]);
    await user.click(screen.getByRole("alertdialog").querySelector("button:last-of-type") as HTMLElement);
    expect(await screen.findByText(/This card is not shared right now/)).toBeTruthy();
  });
});

describe("care card, errors and states", () => {
  it("shows a 422 message from the server and keeps the page usable", async () => {
    registerFakeArea("careCardTest", [
      (req) =>
        req.method === "POST" && req.path === "/care-card"
          ? { status: 422, body: { error: { code: "invalid_card", message: "Choose up to 10 phrases.", details: {} } } }
          : undefined,
    ]);
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Create private link" }));
    expect(await screen.findByText("Choose up to 10 phrases.")).toBeTruthy();
    expect(status()).toBe("Not shared yet");
  });

  it("a failed load shows a retry", async () => {
    api.scenario.networkDown = true;
    render(
      <MemoryRouter>
        <WithAppCopy><CareCardPage /></WithAppCopy>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("button", { name: /try again/i })).toBeTruthy();
  });

  it("the preview renders only whitelisted snapshot fields, never diagnosis or medicines", async () => {
    await publishCareCard([]);
    await open();
    const preview = screen.getByRole("article", { name: "Preview" });
    expect(preview.textContent).toContain("gardening");
    expect(preview.textContent).toContain("Up at 7. Tea at 10.");
    expect(preview.textContent?.toLowerCase()).not.toMatch(/diagnos|medic|dementia|alzheimer's disease/);
    expect([...CARD_SNAPSHOT_KEYS].sort()).toEqual(
      ["avoid", "calms", "caregiverFirstName", "contacts", "displayName", "enjoys", "helplines", "phrases", "rhythm", "updatedOn"].sort(),
    );
    expect(screen.queryByLabelText(/diagnos|medic/i)).toBeNull();
  });

  it("Print calls window.print", async () => {
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Print" }));
    expect(print).toHaveBeenCalledTimes(1);
  });
});

describe("care card, accessibility and print CSS", () => {
  it.each(["not_published", "published", "update_available", "revoked"] as const)("axe is clean (%s)", async (state) => {
    if (state !== "not_published") await publishCareCard([]);
    if (state === "update_available") await putProfile({ calms: ["x"] });
    if (state === "revoked") {
      await revokeCareCard();
    }
    const { view } = await open();
    expect(status()).toBe(
      { not_published: "Not shared yet", published: "Shared by link", update_available: "New phrases to add", revoked: "No longer shared" }[state],
    );
    expect(await axe(view.container)).toHaveNoViolations();
  });

  it("the print stylesheet uses Letter, hides everything but the card and is black and white", () => {
    const css = readFileSync(resolve(__dirname, "careCard.module.css"), "utf8");
    expect(css).toMatch(/@page \{[^}]*size: Letter/);
    expect(css).toMatch(/@media print \{[\s\S]*\.noPrint \{[^}]*display: none/);
    expect(css).toMatch(/@media print[\s\S]*#000/);
    const layout = readFileSync(resolve(__dirname, "../../../layout/app/AppLayout.module.css"), "utf8");
    expect(layout).toMatch(/@media print \{[^}]*\[data-app-chrome\] \{[^}]*display: none/);
  });
});
