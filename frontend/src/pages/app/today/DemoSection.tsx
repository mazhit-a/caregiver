import { useCallback, useEffect, useRef, useState } from "react";
import { getSubscription } from "../../../api/app";
import type { Today } from "../../../api/appTypes";
import { useAppAction } from "../../../api/useAppRequest";
import { DemoPanel } from "../../../components/app/DemoPanel";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { DEMO, DEMO_DONE_TEXT, SYNC_MAX_POLLS, SYNC_POLL_MS } from "../../../content/app/demo";
import { formatDate } from "../../../format/date";
import { DEMO_ACTIONS } from "./demoActions";

interface Props {
  today: Today;
  /** Called after a control (and again when a Stripe clock sync ends): the page refetches Today. */
  onChanged?: () => void;
}

/** Container for the demo block of Today: runs the controls, polls the Stripe clock sync. */
export function DemoSection({ today, onChanged }: Props) {
  const demo = today.demo;
  const runAction = useAppAction();
  const runRef = useRef(runAction);
  runRef.current = runAction;
  const [busyId, setBusyId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [appToday, setAppToday] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const lastId = useRef<string | null>(null);
  const pressing = useRef(false);
  const changed = useRef(onChanged);
  changed.current = onChanged;

  const press = useCallback(
    async (id: string) => {
      const action = DEMO_ACTIONS[id];
      if (!action || pressing.current) return;
      pressing.current = true;
      lastId.current = id;
      setBusyId(id);
      setError(null);
      setStatus(null);
      const result = await runRef.current(() => action());
      pressing.current = false;
      setBusyId(null);
      if (!result.ok) {
        if (!result.handled) setError(APP_ERROR_MESSAGES[result.failure.kind]);
        return;
      }
      setAppToday(result.data.appToday);
      setStatus(result.data.billingSync === "pending" ? DEMO.syncing : (DEMO_DONE_TEXT[id] ?? null));
      setSyncing(result.data.billingSync === "pending");
      changed.current?.();
    },
    [],
  );

  useEffect(() => {
    if (!syncing) return;
    let cancelled = false;
    let polls = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      polls += 1;
      const result = await runRef.current(() => getSubscription());
      if (cancelled) return;
      if (result.ok && result.data.billingSync !== "pending") {
        setSyncing(false);
        setStatus(DEMO.syncDone);
        changed.current?.();
        return;
      }
      if (polls >= SYNC_MAX_POLLS) {
        setSyncing(false);
        setStatus(DEMO.syncStalled);
        return;
      }
      timer = setTimeout(() => void tick(), SYNC_POLL_MS);
    };
    timer = setTimeout(() => void tick(), SYNC_POLL_MS);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [syncing]);

  if (!demo) return null;
  const controls = demo.controls.filter((c) => c.id in DEMO_ACTIONS);
  const date = appToday ?? demo.appToday;
  return (
    <DemoPanel
      label={demo.label}
      controls={controls}
      busyId={busyId}
      status={status}
      error={error}
      retryLabel={DEMO.retry}
      detail={`${DEMO.appDateLabel}: ${formatDate(date, { year: true })}`}
      onPress={(id) => void press(id)}
      onRetry={() => lastId.current && void press(lastId.current)}
    />
  );
}
