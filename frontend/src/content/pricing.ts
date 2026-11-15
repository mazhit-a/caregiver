// Wording for the pricing page (design: pricing-safety). No amounts here: prices come from the API.

export const PRICING_HERO = {
  title: "Simple plans, clear terms",
  lead: "You see the full price and the renewal date before you pay. Cancel anytime in Settings.",
} as const;

/** `{period}` is filled from the API (introPeriodText / renewPeriodText). */
export const introLine = (period: string): string => `for your first ${period}`;
export const renewLine = (period: string): string => `every ${period}`;

export const INCLUDED_TITLE = "Both plans include";
export const INCLUDED_ITEMS: readonly string[] = [
  "The full course, in the order that fits you",
  "Practice with an AI partner and feedback",
  "Mom’s page and the shareable care card",
  "A doctor-visit sheet for every visit",
  "Quick guides for urgent moments",
];
export const currencyItem = (currency: string): string => `Prices in ${currency}`;

export const BILLING_TITLE = "How billing works";
export const BILLING_CARDS = [
  {
    title: "Before you pay",
    text: "Today’s price, the renewal price and the renewal date sit right above the button, and the renewal terms are stated right there; tapping the button means you agree to them.",
  },
  {
    title: "Cancel anytime",
    text: "Settings, then Manage my plan, then Cancel. Two taps, no offers to talk you out of it.",
  },
  {
    title: "Close your plan any time",
    text: "One step in Settings ends the plan, the care card link and deletes your data.",
  },
] as const;

export const SAFETY_TITLE = "Safety and privacy";
export const DO_LIST = {
  title: "What we do",
  items: [
    "Teach communication and everyday care",
    "Help you get ready for doctor visits",
    "Help you organize what works with Mom",
  ],
} as const;
export const DONT_LIST = {
  title: "What we don’t do",
  items: [
    "Give medical, legal or financial advice",
    "Diagnose, or suggest medicines or doses",
    "Replace Mom’s doctor, pharmacist or a social worker",
  ],
} as const;
export const SAFETY_CARDS = [
  {
    title: "Saved privately to this session",
    text: "Your quiz answers are saved privately to this session, with no account and no name. We store a care card only when you choose to share it.",
  },
  {
    title: "No ad tracking",
    text: "No ad or tracking scripts in the quiz or the course. We never sell or share your answers.",
  },
  {
    title: "Practice isn’t recorded",
    text: "Practice conversations aren’t saved. Only the phrases you choose to keep are.",
  },
] as const;

export const HELP_TITLE = "Need help now?";
export const APS_LINE =
  "Worried someone is being harmed or neglected? Contact Adult Protective Services in your state.";

export const BILLING_FAQ_TITLE = "Billing questions";
export const BILLING_FAQ = [
  {
    question: "Can I see my plan before paying?",
    answer:
      "Yes. After the quiz you see Mom’s plan and get the free phrase sheet before any payment screen.",
  },
  {
    question: "When will I be charged again?",
    answer:
      "At the end of your first period, on the date shown above the pay button, and then every 4 or 12 weeks until you cancel.",
  },
  {
    question: "Can my brother see Mom’s plan too?",
    answer: "You can share the care card with anyone by private link, at no extra cost.",
  },
] as const;
