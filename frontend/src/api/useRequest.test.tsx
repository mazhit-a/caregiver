import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "./client";
import { useRequest } from "./useRequest";

describe("useRequest", () => {
  it("goes loading, then ready with data", async () => {
    const { result } = renderHook(() => useRequest(() => Promise.resolve(42), []));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current.data).toBe(42);
  });

  it("maps a failure to a kind and retries on demand", async () => {
    let attempts = 0;
    const { result } = renderHook(() =>
      useRequest(() => {
        attempts += 1;
        return attempts === 1
          ? Promise.reject(new ApiError(429, "rate_limited", "m"))
          : Promise.resolve("ok");
      }, []),
    );
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toEqual({ kind: "rate_limited" });
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current.data).toBe("ok");
  });

  it("runs again when deps change and aborts the previous run", async () => {
    const signals: AbortSignal[] = [];
    const { result, rerender } = renderHook(
      ({ id }) =>
        useRequest(
          (signal) => {
            signals.push(signal);
            return Promise.resolve(id);
          },
          [id],
        ),
      { initialProps: { id: 1 } },
    );
    await waitFor(() => expect(result.current.data).toBe(1));
    rerender({ id: 2 });
    await waitFor(() => expect(result.current.data).toBe(2));
    expect(signals[0]?.aborted).toBe(true);
  });

  it("aborts on unmount", async () => {
    let signal: AbortSignal | undefined;
    const { unmount } = renderHook(() =>
      useRequest((s) => {
        signal = s;
        return new Promise<never>(() => undefined);
      }, []),
    );
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
