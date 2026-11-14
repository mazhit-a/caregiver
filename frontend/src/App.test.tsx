import { render } from "@testing-library/react";
import { axe } from "vitest-axe";
import { App } from "./App";

describe("App", () => {
  it("renders the root and has no axe violations", async () => {
    const { container, getByRole } = render(<App />);
    expect(getByRole("heading", { level: 1, name: "Kelper" })).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});
