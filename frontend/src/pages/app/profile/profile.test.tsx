import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { savePhrase } from "../../../api/app";
import { clearToken, setToken } from "../../../api/session";
import { PROFILE_LIMITS } from "../../../content/app/profile";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import ProfilePage from "./ProfilePage";
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
afterEach(() => api.restore());

async function open() {
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter>
      <WithAppCopy><ProfilePage /></WithAppCopy>
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { level: 1, name: "Mom's page" });
  // wait for the phrases section to settle (loading and ready share the heading)
  await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
  return { user, view };
}

const putCalls = (): number => api.calls.filter((c) => c.method === "PUT" && c.path === "/profile").length;

describe("Mom's page, view mode", () => {
  it("an empty profile shows invitations, not sample data, and no raw placeholder", async () => {
    const { view } = await open();
    expect(screen.getByText("Saved privately to this session. No account, no name needed.")).toBeTruthy();
    expect(screen.getByText(/Phrases you save in a lesson will appear here/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Go to Today" }).getAttribute("href")).toBe("/today");
    expect(screen.getAllByText("Nothing here yet.").length).toBe(3);
    expect(screen.getByText(/No contacts yet/)).toBeTruthy();
    expect(screen.getByText(/No visit planned yet/)).toBeTruthy();
    expect(view.container.textContent).not.toMatch(/[{}]/);
  });

  it("lists saved phrases with a typed source line, copies one and removes one after a confirm", async () => {
    await savePhrase({ text: "You sound worried. I'm here.", source: "roleplay", lessonId: "m1_l1" });
    await savePhrase({ text: "Let's sit down together.", source: "scenario" });
    const { user } = await open();
    expect(await screen.findByText("You sound worried. I'm here.")).toBeTruthy();
    expect(screen.getByText("From practice")).toBeTruthy();
    expect(screen.getByText("From a lesson")).toBeTruthy();

    await user.click(screen.getAllByRole("button", { name: "Copy" }).at(0) as HTMLElement);
    expect(await navigator.clipboard.readText()).toBe("You sound worried. I'm here.");
    expect(screen.getAllByText("Copied").length).toBeGreaterThan(0);

    // cancel is safe
    await user.click(screen.getByRole("button", { name: /Remove: Let's sit down together\./ }));
    await user.click(screen.getByRole("button", { name: "Keep it" }));
    expect(screen.getByText("Let's sit down together.")).toBeTruthy();
    expect(api.calls.some((c) => c.method === "DELETE")).toBe(false);

    // confirm deletes (204 handled)
    await user.click(screen.getByRole("button", { name: /Remove: Let's sit down together\./ }));
    await user.click(screen.getByRole("button", { name: "Remove phrase" }));
    await waitFor(() => expect(screen.queryByText("Let's sit down together.")).toBeNull());
    expect(screen.getByText("You sound worried. I'm here.")).toBeTruthy();
  });

  it("has no axe violations", async () => {
    await savePhrase({ text: "I'm here.", source: "gift" });
    const { view } = await open();
    await screen.findByText("I'm here.");
    expect(await axe(view.container)).toHaveNoViolations();
  });
});

describe("Mom's page, edit mode", () => {
  it("saves a round trip and shows the new values", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.type(screen.getByLabelText("Name or nickname"), "Margaret");
    await user.type(screen.getByLabelText("Add to Enjoys"), "gardening{Enter}");
    await user.type(screen.getByLabelText("Add to Calms"), "tea");
    await user.click(screen.getByRole("button", { name: "Calms: Add" }));
    await user.type(screen.getByLabelText("Daily rhythm"), "Tea at 10.");
    await user.click(screen.getByRole("button", { name: "Add a contact" }));
    await user.type(screen.getByLabelText("Name"), "Sam");
    await user.type(screen.getByLabelText("Phone"), "555-0100");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("button", { name: "Edit" });
    expect(screen.getByText("gardening")).toBeTruthy();
    expect(screen.getByText("tea")).toBeTruthy();
    expect(screen.getByText("Tea at 10.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "555-0100" })).toBeTruthy();
    expect(putCalls()).toBe(1);
  });

  it("enforces the limits in the browser before any request", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    const enjoys = screen.getByLabelText("Add to Enjoys");
    await user.click(enjoys);
    await user.paste("x".repeat(PROFILE_LIMITS.itemLength + 1));
    await user.click(screen.getByRole("button", { name: "Enjoys: Add" }));
    expect(screen.getByRole("alert").textContent).toMatch(/shorten/);
    await user.clear(enjoys);
    for (let i = 0; i < PROFILE_LIMITS.listItems; i += 1) {
      await user.type(enjoys, `item${i}{Enter}`);
    }
    await user.type(enjoys, "one more{Enter}");
    expect(screen.getByText("That is the most this list can hold.")).toBeTruthy();
    expect(screen.queryByText("one more")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Add a contact" }));
    await user.type(screen.getByLabelText("Name"), "Sam");
    await user.type(screen.getByLabelText("Phone"), "12");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/doesn't look right/)).toBeTruthy();
    expect(putCalls()).toBe(0);
  });

  it("shows the server's message for a 422 invalid_profile and stays in edit mode", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.type(screen.getByLabelText("Daily rhythm"), "Tea.");
    api.injectError("PUT", "/profile", 422, "invalid_profile", { field: "rhythm" });
    await user.click(screen.getByRole("button", { name: "Save" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Injected failure.");
    expect(screen.getByRole("button", { name: "Save" })).toBeTruthy();
  });

  it("removes a chip with the keyboard", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.type(screen.getByLabelText("Add to Try to avoid"), "loud TV{Enter}");
    const remove = screen.getByRole("button", { name: "Remove loud TV from Try to avoid" });
    remove.focus();
    await user.keyboard("{Enter}");
    expect(screen.queryByRole("button", { name: /Remove loud TV/ })).toBeNull();
  });

  it("warns before Cancel throws edits away, and Keep editing keeps them", async () => {
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.type(screen.getByLabelText("Daily rhythm"), "Quiet mornings.");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    expect((screen.getByLabelText("Daily rhythm") as HTMLTextAreaElement).value).toBe("Quiet mornings.");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("button", { name: "Leave without saving" }));
    expect(screen.getByRole("button", { name: "Edit" })).toBeTruthy();
    expect(screen.queryByText("Quiet mornings.")).toBeNull();
    expect(putCalls()).toBe(0);
  });

  it("Cancel with no changes leaves at once, and the form has no axe violations", async () => {
    const { user, view } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByText(/Please don't add diagnoses or medicines/)).toBeTruthy();
    expect(await axe(view.container)).toHaveNoViolations();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Edit" })).toBeTruthy();
  });

  it("never logs what was typed", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) =>
      vi.spyOn(console, m).mockImplementation(() => undefined),
    );
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.type(screen.getByLabelText("Daily rhythm"), "private-rhythm-text");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("button", { name: "Edit" });
    for (const spy of spies) {
      expect(JSON.stringify(spy.mock.calls)).not.toContain("private-rhythm-text");
      spy.mockRestore();
    }
  });
});

describe("profile limits contract", () => {
  it("mirror backend/app/domain/profile/entities.py", () => {
    const py = readFileSync(resolve(process.cwd(), "../backend/app/domain/profile/entities.py"), "utf-8");
    const num = (name: string): number => Number(new RegExp(`^${name}\\s*=\\s*(\\d+)`, "m").exec(py)?.[1]);
    expect(PROFILE_LIMITS).toEqual({
      displayName: num("MAX_DISPLAY_NAME"),
      caregiverName: num("MAX_CAREGIVER_NAME"),
      listItems: num("MAX_LIST_ITEMS"),
      itemLength: num("MAX_ITEM_LENGTH"),
      rhythmLength: num("MAX_RHYTHM_LENGTH"),
      contacts: num("MAX_CONTACTS"),
      contactName: num("MAX_CONTACT_NAME"),
      contactRole: num("MAX_CONTACT_ROLE"),
      phoneLength: num("MAX_PHONE_LENGTH"),
      phoneMinDigits: num("MIN_PHONE_DIGITS"),
      phoneMaxDigits: num("MAX_PHONE_DIGITS"),
    });
  });
});
