import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError } from "../../api/client";
import {
  cancelFakeCheckout,
  type FakeCardInput,
  type FakeCheckoutSummary,
  getFakeCheckout,
  payFakeCheckout,
} from "../../api/fakeStripe";
import { useRequest } from "../../api/useRequest";
import { FAKE_CHECKOUT_TEXT as T, TEST_CARDS } from "../../content/fakeStripe";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import styles from "./FakeCheckoutPage.module.css";

const money = (amount: number, currency: string): string => {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(amount);
  } catch {
    return `${amount} ${currency}`;
  }
};

/** "12/34", "1 / 2034", "12-34" -> month and year, or null. */
function parseExpiry(text: string): { expMonth: number; expYear: number } | null {
  const m = /^\s*(\d{1,2})\s*[/-]?\s*(\d{2}|\d{4})\s*$/.exec(text);
  if (!m?.[1] || !m[2]) return null;
  return { expMonth: Number(m[1]), expYear: Number(m[2]) };
}

function describeError(error: unknown): { message: string; closed: boolean } {
  if (error instanceof ApiError) {
    if (error.code === "checkout_closed") return { message: T.closed, closed: true };
    // The backend's Stripe-like messages are shown as they are (never the card details).
    if (error.status === 402 || error.status === 409 || error.status === 422) {
      return { message: error.message, closed: false };
    }
  }
  return { message: T.genericError, closed: false };
}

/** The simulated Stripe card page. Card details live in component state only, never stored or logged. */
export default function FakeCheckoutPage() {
  const { checkoutId = "" } = useParams();
  const summary = useRequest((signal) => getFakeCheckout(checkoutId, signal), [checkoutId]);
  const navigate = useNavigate();
  const [number, setNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvc, setCvc] = useState("");
  const [busy, setBusy] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const goBack = async () => {
    setBusy(true);
    try {
      await cancelFakeCheckout(checkoutId);
    } catch {
      // Already closed or unknown: the paywall is the right place either way.
    }
    navigate(`${ROUTES.paywall}?checkout=canceled`);
  };

  const submit = async (authenticated: boolean) => {
    if (busy) return;
    const exp = parseExpiry(expiry);
    if (number.replace(/\D/g, "") === "") return setError(T.badNumber);
    if (!exp) return setError(T.badExpiry);
    if (!/^\d{3,4}$/.test(cvc)) return setError(T.badCvc);
    setBusy(true);
    setError(null);
    const body: FakeCardInput = { cardNumber: number, ...exp, cvc };
    if (authenticated) body.authenticated = true;
    try {
      const result = await payFakeCheckout(checkoutId, body);
      if (result.status === "requires_action") {
        setNeedsAuth(true);
        setBusy(false);
        return;
      }
      navigate(`${ROUTES.checkoutReturn}?checkout_id=${encodeURIComponent(checkoutId)}`);
    } catch (e) {
      setError(describeError(e).message);
      setNeedsAuth(false);
      setBusy(false);
    }
  };

  const useCard = (card: string) => {
    setNumber(card);
    setExpiry("12/34");
    setCvc("123");
    setNeedsAuth(false);
    setError(null);
  };

  return (
    <FunnelScreen back={{ onClick: () => void goBack() }}>
      <Seo title={pageTitle("Simulated checkout")} description="Simulated checkout. No real payment." />
      <meta name="robots" content="noindex" />
      <p className={styles.banner} data-testid="fake-banner">
        {T.banner}
      </p>
      {summary.status === "loading" && (
        <h1 data-funnel-heading tabIndex={-1} role="status" className={styles.title}>
          {T.loading}
        </h1>
      )}
      {summary.status === "error" && (
        <div role="alert" className={styles.stack}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            {summary.error.kind === "unknown" ? T.notFound : T.loadFailed}
          </h1>
          {summary.error.kind !== "unknown" && (
            <button type="button" className={styles.secondary} onClick={summary.retry}>
              {T.retry}
            </button>
          )}
          <Link to={ROUTES.paywall} className={styles.link}>
            {T.toPaywall}
          </Link>
        </div>
      )}
      {summary.status === "ready" && (
        <Form
          data={summary.data}
          number={number}
          expiry={expiry}
          cvc={cvc}
          busy={busy}
          needsAuth={needsAuth}
          error={error}
          onNumber={setNumber}
          onExpiry={setExpiry}
          onCvc={setCvc}
          onSubmit={submit}
          onUseCard={useCard}
        />
      )}
    </FunnelScreen>
  );
}

interface FormProps {
  data: FakeCheckoutSummary;
  number: string;
  expiry: string;
  cvc: string;
  busy: boolean;
  needsAuth: boolean;
  error: string | null;
  onNumber: (v: string) => void;
  onExpiry: (v: string) => void;
  onCvc: (v: string) => void;
  onSubmit: (authenticated: boolean) => void;
  onUseCard: (number: string) => void;
}

function Form(p: FormProps) {
  const { data } = p;
  return (
    <div className={styles.stack}>
      <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
        {T.title}
      </h1>
      <section className={styles.summary} aria-label="Order summary">
        <p className={styles.plan}>{data.planLabel}</p>
        {data.displayLabel && <p className={styles.muted}>{data.displayLabel}</p>}
        <p className={styles.amount}>
          {money(data.amountToday, data.currency)} <span className={styles.muted}>today</span>
        </p>
        <p className={styles.muted}>{data.introPeriodText}</p>
        <p className={styles.muted}>
          Then {money(data.renewalPrice, data.currency)} {data.renewPeriodText}, first renewal on{" "}
          {data.firstRenewalDate}.
        </p>
      </section>
      <form
        className={styles.stack}
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          p.onSubmit(false);
        }}
      >
        <label className={styles.field}>
          <span>{T.numberLabel}</span>
          <input
            className={styles.input}
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={p.number}
            onChange={(e) => p.onNumber(e.target.value)}
          />
        </label>
        <div className={styles.row}>
          <label className={styles.field}>
            <span>{T.expiryLabel}</span>
            <input
              className={styles.input}
              type="text"
              inputMode="numeric"
              autoComplete="off"
              placeholder="MM/YY"
              value={p.expiry}
              onChange={(e) => p.onExpiry(e.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span>{T.cvcLabel}</span>
            <input
              className={styles.input}
              type="text"
              inputMode="numeric"
              autoComplete="off"
              maxLength={4}
              value={p.cvc}
              onChange={(e) => p.onCvc(e.target.value)}
            />
          </label>
        </div>
        <div role="alert" className={styles.error}>
          {p.error}
        </div>
        {p.needsAuth && (
          <div className={styles.stack} role="status">
            <p className={styles.muted}>{T.authenticateHint}</p>
            <button type="button" className={styles.primary} disabled={p.busy} onClick={() => p.onSubmit(true)}>
              {T.authenticate}
            </button>
          </div>
        )}
        {!p.needsAuth && (
          <button type="submit" className={styles.primary} disabled={p.busy}>
            {p.busy ? T.paying : `${T.pay} ${money(data.amountToday, data.currency)}`}
          </button>
        )}
      </form>
      <details className={styles.cards}>
        <summary className={styles.cardsSummary}>{T.testCards}</summary>
        <p className={styles.muted}>{T.testCardsHint}</p>
        <ul className={styles.cardList}>
          {TEST_CARDS.map((card) => (
            <li key={card.number} className={styles.cardItem}>
              <span>
                <code>{card.number}</code>
                <br />
                <span className={styles.muted}>{card.outcome}</span>
              </span>
              <button
                type="button"
                className={styles.secondary}
                aria-label={`${T.useCard} ${card.number}`}
                onClick={() => p.onUseCard(card.number)}
              >
                {T.useCard}
              </button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
