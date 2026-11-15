import { useCallback, useRef, useState } from "react";
import { ApiError } from "../../../api/client";
import { demoFailNextPayment, demoJumpToRenewal, demoNextDay, getDemo } from "../../../api/app";
import type { Demo } from "../../../api/appTypes";
import { useAppAction, useAppRequest } from "../../../api/useAppRequest";
import { DemoPanel } from "../../../components/app/DemoPanel";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { DEMO_DONE_TEXT } from "../../../content/app/demo";
import { DEMO_CONTROL_LABELS, SETTINGS } from "../../../content/app/settings";
import { formatDate } from "../../../format/date";

const ACTIONS: Record<string, () => Promise<Demo>> = {
  nextDay: () => demoNextDay(),
  jumpToRenewal: () => demoJumpToRenewal(),
  failNextPayment: () => demoFailNextPayment(),
};
const CONTROLS = Object.keys(ACTIONS).map((id) => ({ id, label: DEMO_CONTROL_LABELS[id] ?? id }));

/**
 * The demo panel of Settings. `GET /demo` is the probe: 404 (or any failure) means the server has
 * the controls off and nothing renders. `fail-next-payment` shows the server's own 409 message
 * when the session is not a Stripe one.
 */
export function SettingsDemo({ onChanged }: { onChanged: () => void }) {
  const probe = useAppRequest((signal) => getDemo(signal), []);
  const runAction = useAppAction();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [today, setToday] = useState<string | null>(null);
  const lastId = useRef<string | null>(null);
  const pressing = useRef(false);

  const press = useCallback(
    async (id: string) => {
      const action = ACTIONS[id];
      if (!action || pressing.current) return;
      pressing.current = true;
      lastId.current = id;
      setBusyId(id);
      setError(null);
      setStatus(null);
      let serverMessage: string | null = null;
      const result = await runAction(async () => {
        try {
          return await action();
        } catch (failure) {
          if (failure instanceof ApiError) serverMessage = failure.message;
          throw failure;
        }
      });
      pressing.current = false;
      setBusyId(null);
      if (!result.ok) {
        if (!result.handled) {
          setError(result.failure.kind === "conflict" && serverMessage ? serverMessage : APP_ERROR_MESSAGES[result.failure.kind]);
        }
        return;
      }
      setToday(result.data.appToday);
      setStatus(DEMO_DONE_TEXT[id] ?? SETTINGS.demoDone);
      onChanged();
    },
    [runAction, onChanged],
  );

  if (probe.status !== "ready") return null;
  const date = today ?? probe.data.appToday;
  return (
    <DemoPanel
      label={probe.data.label}
      controls={CONTROLS}
      busyId={busyId}
      status={status}
      error={error}
      retryLabel={SETTINGS.retry}
      detail={`${SETTINGS.demoDetail}: ${formatDate(date, { year: true })}`}
      onPress={(id) => void press(id)}
      onRetry={() => lastId.current && void press(lastId.current)}
    />
  );
}
