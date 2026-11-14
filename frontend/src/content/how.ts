/** Copy for /how-it-works, from the design (how-it-works/index.html) with the plan's privacy change. */

export const HOW_SEO = {
  title: "How it works | Kelper",
  description:
    "Three minutes of questions, then short lessons that fit around your day. Every step, from the first question to the next morning.",
} as const;

export const HOW_HERO = {
  title: "How Kelper works",
  lead: "Three minutes of questions, then short lessons that fit around your day. Here’s every step, from the first question to the next morning.",
} as const;

export const HOW_STEP1 = {
  eyebrow: "Step 1",
  title: "Tell us what’s happening",
  // Privacy sentence replaced per plan ("stay in your browser" is not true: progress is saved on the server).
  lead: "11 short questions, about 3 minutes. Saved privately to this session. No account, no name needed.",
  topics: [
    "Who you care for",
    "What’s happening now",
    "Where she lives",
    "Who else helps",
    "What worries you most",
    "Key papers",
    "Time you have each day",
  ],
  note: "We never ask for a diagnosis or medicines. Every answer changes something in your plan.",
  imageAlt: "The Kelper quiz on a phone: a question with large answer cards",
} as const;

export const HOW_STEP2 = {
  eyebrow: "Step 2",
  title: "See Mom’s plan before you pay",
  lead: "First, what we understood about your situation. Then your course, module by module, in the order that fits you, with a reason for every step.",
  exampleLabel: "Example plan",
  heardTitle: "What we heard",
  heardText:
    "Mom was diagnosed in the last few months. Mom lives far away. You’re handling most of it alone, and you work full-time.",
  courseTitle: "Your course",
  course: [
    { title: "Talking with Mom", why: "Everyone starts here." },
    { title: "While she can still decide", why: "Why now: some of Mom’s key papers are missing." },
    { title: "Hard moments", why: "Why now: you said evenings are hard." },
  ],
} as const;

export const HOW_STEP3 = {
  eyebrow: "Step 3",
  title: "A lesson takes about 8 minutes",
  lead: "Every lesson starts with a real moment, not a lecture, and ends with something you can do.",
  steps: [
    { title: "A real moment", text: "“For the fifth time today, she asks…” What would you say?" },
    { title: "Short and clear", text: "Four short screens with one idea each, and quick checks along the way." },
    {
      title: "Practice out loud",
      text: "Three rounds with an AI practice partner, with feedback from Ollie after each reply.",
    },
    {
      title: "Your plan for next time",
      text: "“If Mom asks again, I’ll say…” in your own words, plus one thing to do now.",
    },
  ],
} as const;

export const HOW_STEP4 = {
  eyebrow: "Step 4",
  title: "Lessons adapt to where the hard moments reach you",
  lead: "One tap at the start of a lesson. The examples and your task change; the course stays the same, so you never fall behind.",
  tableCaption: "How a lesson adapts",
  columns: ["Where it happens", "The moment you practice", "Your one thing to do now"],
  rows: [
    ["In person", "6 pm in the kitchen, the same question again", "Write the answer on a note for the fridge"],
    [
      "On the phone",
      "Her third call today, while you’re at work",
      "Save your phrase where you’ll see it when she calls",
    ],
    ["In a care home", "Calls and visits", "Ask the staff to keep your visit days on a calendar"],
    [
      "Not noticed yet",
      "What it often looks like",
      "Watch for it on your next call or visit, and note it for the doctor",
    ],
  ],
} as const;

export const HOW_STEP5 = {
  eyebrow: "Step 5",
  title: "The next day, a quick check-in",
  lead: "Did the moment come up? If it did, tell us how your plan went. If not, it’s ready for when it does. Either way, a 2-minute practice round and the next lesson are waiting.",
  note: "No streaks, no guilt. Three short sessions a week is plenty.",
  imageAlt: "The Today screen: the next lesson and a check-in asking whether the moment came up",
} as const;

export const HOW_CTA = {
  title: "Ready to see Mom’s plan?",
} as const;
