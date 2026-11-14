/** Wording for /course, copied from context/design/kelper-landing/course. Checked against content/plan-rules.json in course.test.ts. */

export const COURSE_HERO = {
  title: "A course that follows Mom",
  lead: "Modules of short lessons. You finish one topic before the next, and the order fits your situation. Dementia changes over years, so the course grows with it.",
  image: { alt: "Ollie reading a book", width: 488, height: 640 },
} as const;

export interface CourseLesson {
  title: string;
  minutes: number;
}

export const MODULE_ONE = {
  badge: "Everyone starts here",
  title: "Module 1: Talking with Mom",
  intro:
    "One simple pattern for hard conversations: notice the feeling, reassure, offer something to do. Each lesson uses it in a harder moment.",
  why: "Why first: talking with Mom comes up every day, at every stage, wherever she lives.",
  lessons: [
    { title: "When Mom asks again", minutes: 8 },
    { title: "Talking so it lands", minutes: 7 },
    { title: "“You stole my purse”", minutes: 8 },
    { title: "When Mom says no", minutes: 8 },
    { title: "Your phrase book: review and practice", minutes: 6 },
  ],
} as const satisfies { lessons: readonly CourseLesson[] } & Record<string, unknown>;

export const ORDER_SECTION = {
  title: "Then, in the order that fits you",
  text: "Your answers move the most urgent topics up. Every module tells you why it’s where it is, so the plan never feels random.",
  examples: [
    {
      title: "While she can still decide",
      why: "Why now: some of Mom’s key papers are missing, and it’s easier to sort them out while she can take part.",
    },
    {
      title: "Safe home, calmer days",
      why: "Why now: Mom just came home from the hospital, and safety at home comes first.",
    },
    {
      title: "Caring for yourself",
      why: "Why now: you said you’re exhausted. Your health matters too.",
    },
  ],
} as const;

export interface CourseModule {
  id: string;
  title: string;
  /** Shown top right of the card. */
  count: string;
  note: string;
  lessons: readonly CourseLesson[];
  /** Typed fallback for what exists today (plan-rules.json lessons with built: true); a test keeps it in sync. */
  built: boolean;
  /** Badge text for modules that are not available yet. */
  badge?: string;
}

const SOON = "Coming soon";

/** Titles use "Mom" and "she" as the design does. */
export const COURSE_MODULES: readonly CourseModule[] = [
  {
    id: "m0_before",
    title: "Before the diagnosis",
    count: "3 lessons",
    note: "Only if there’s no diagnosis yet. Comes right after Module 1.",
    built: false,
    badge: SOON,
    lessons: [
      { title: "Normal aging or something more?", minutes: 7 },
      { title: "Talking to Mom about seeing a doctor", minutes: 8 },
      { title: "Preparing for the memory evaluation", minutes: 7 },
    ],
  },
  {
    id: "m2_hard_moments",
    title: "Hard moments",
    count: "4 lessons",
    note: "The same pattern, when emotions run higher.",
    built: false,
    badge: SOON,
    lessons: [
      { title: "Finding the trigger", minutes: 7 },
      { title: "Evening confusion", minutes: 8 },
      { title: "“I want to go home”", minutes: 8 },
      { title: "Anger and agitation", minutes: 8 },
    ],
  },
  {
    id: "m3_decide",
    title: "While she can still decide",
    count: "3 lessons",
    note: "Papers, money and driving, while Mom can take part.",
    built: false,
    badge: SOON,
    lessons: [
      { title: "Key papers to talk about", minutes: 8 },
      { title: "Managing Mom’s bills together", minutes: 7 },
      { title: "The driving conversation", minutes: 8 },
    ],
  },
  {
    id: "m4_safe_home",
    title: "Safe home, calmer days",
    count: "3 lessons",
    note: "Small changes that make days safer and calmer.",
    built: false,
    badge: SOON,
    lessons: [
      { title: "Home safety walk-through", minutes: 8 },
      { title: "A calming daily routine", minutes: 7 },
      { title: "Activities that bring joy", minutes: 6 },
    ],
  },
  {
    id: "m5_care_team",
    title: "Doctors and your care team",
    count: "4 lessons",
    note: "More from every visit, and help from others.",
    built: false,
    badge: SOON,
    lessons: [
      { title: "Getting the most from 15 minutes with the doctor", minutes: 7 },
      { title: "Guiding your sitter", minutes: 6 },
      { title: "Asking your siblings for specific help", minutes: 7 },
      { title: "Caring from a distance", minutes: 7 },
    ],
  },
  {
    id: "m6_you",
    title: "Caring for yourself",
    count: "3 lessons",
    note: "Because caring works better when you rest too.",
    built: false,
    badge: SOON,
    lessons: [
      { title: "The fifth time is the hardest", minutes: 6 },
      { title: "Spotting burnout early", minutes: 6 },
      { title: "A plan for your own breaks", minutes: 5 },
    ],
  },
  {
    id: "m7_more_help",
    title: "Getting more help",
    count: "Coming later",
    note: "For when Mom needs more help than you can give alone.",
    built: false,
    lessons: [
      { title: "When it’s time for more help", minutes: 7 },
      { title: "Medicare and paying for care", minutes: 8 },
      { title: "Choosing in-home help or a care community", minutes: 8 },
    ],
  },
  {
    id: "m8_later",
    title: "Later stages",
    count: "Coming later",
    note: "Comfort, connection and the conversations families need.",
    built: false,
    lessons: [
      { title: "Comfort and connection", minutes: 7 },
      { title: "Hospice and palliative care: what they are", minutes: 8 },
    ],
  },
];

export const ALL_MODULES_TITLE = "Everything in the course";

export const QUICK_GUIDES = {
  title: "Quick guides for urgent moments",
  text: "Some things can’t wait for the next module. Short how-tos sit outside the course, always one tap away.",
  items: [
    { id: "qg_hospital", title: "After a hospital stay" },
    { id: "qg_missing", title: "If Mom goes missing" },
    { id: "qg_fall", title: "After a fall" },
    { id: "qg_sudden_change", title: "A sudden change in confusion" },
    { id: "qg_limit", title: "You’re at your limit" },
  ],
} as const;

export const COURSE_CTA = {
  title: "See the order that fits your family",
} as const;
