import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";
import { expect } from "vitest";
import * as axeMatchers from "vitest-axe/matchers";

expect.extend(axeMatchers);

// Lazy route chunks load slowly when the whole suite runs in parallel: give async queries headroom.
configure({ asyncUtilTimeout: 5000 });

// jsdom does not implement the modal <dialog> API.
if (typeof HTMLDialogElement !== "undefined") {
  HTMLDialogElement.prototype.showModal ??= function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function close(this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
}
