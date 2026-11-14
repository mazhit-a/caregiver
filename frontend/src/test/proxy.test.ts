import { apiProxy } from "../devProxy";

describe("dev proxy", () => {
  it("forwards /api to the backend on port 8000", () => {
    expect(apiProxy["/api"].target).toBe("http://localhost:8000");
  });
});
