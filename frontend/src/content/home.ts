/** Home page wording, copied from the design (home/index.html). Prices come from the API, never from here. */

export const HOME_SEO = {
  title: "Kelper: a calm plan for caring for a parent with dementia",
  description:
    "Short lessons that start with real moments, practice out loud before the hard conversation happens, and a plan built around your mom.",
} as const;

export const HOME_HERO = {
  eyebrow: "For adult children caring for a parent with dementia",
  title: "Mom’s diagnosis came with a brochure. Here’s the plan.",
  lead: "Short lessons that start with real moments, practice out loud before the hard conversation happens, and a plan built around your mom.",
  note: "Takes 3 minutes. No sign-up needed.",
} as const;

export const HOME_PREVIEW = {
  title: "Try it: Mom asks again",
  badge: "Practice preview",
  reset: "Try another answer",
  footnote: "In the course you type your own words, and an AI practice partner answers as Mom.",
} as const;

export const HOME_GAP = {
  /** TODO(verify): statistic and source are on the pre-launch checklist. */
  stat: "About 1 in 4 US adults cares for a family member. Most never got any training.",
  text: "Knowing what to say and do is a skill. Kelper teaches it, one calm step at a time.",
  source: "Source: AARP and the National Alliance for Caregiving, Caregiving in the US 2025",
} as const;

export const HOME_OLLIE = {
  title: "Meet Ollie, your guide",
  /** TODO(verify): first-person backstory kept as designed (decision 3). */
  quote: "“I cared for my mom for six years. I’ll walk with you through the hard moments, one calm step at a time.”",
  text: "Ollie opens every lesson and gives you feedback when you practice. She’s a guide who has been there, not a nurse or a doctor.",
  imageAlt: "Ollie, a sea otter in a lavender sweater, waving hello",
} as const;

export const HOME_STEPS = {
  title: "From “what now?” to a plan in three steps",
  link: "See how it works",
  steps: [
    {
      title: "Tell us what’s happening",
      text: "11 short questions about Mom, your family and your time. About 3 minutes, no sign-up.",
    },
    {
      title: "Get Mom’s plan",
      text: "A course in modules, in the order that fits your situation, with a reason for each step.",
    },
    {
      title: "Learn, practice, try it for real",
      text: "8-minute lessons, practice out loud, then a plan for the next real moment. The next day, a quick check-in.",
    },
  ],
} as const;

export const HOME_FEATURES = {
  practice: {
    title: "Practice the hard conversation before it happens",
    text: "Type what you’d really say. An AI practice partner answers as Mom, and Ollie shows what worked: noticing the feeling, reassuring, offering something to do.",
    link: "How practice works",
    mock: {
      heading: "Your practice",
      first: { label: "First try", score: "1 of 3" },
      last: { label: "Last try", score: "3 of 3" },
      best: "Best phrase: “You’re wondering about tomorrow. We have plenty of time.”",
    },
  },
  course: {
    title: "A course that follows Mom, not a pile of articles",
    text: "Everyone starts with how to talk with Mom. After that, your answers decide what comes next, and every module tells you why it’s there.",
    link: "See the course",
    mock: {
      startHere: "Start here",
      modules: [
        { name: "1. Talking with Mom", lessons: "5 lessons" },
        { name: "2. While she can still decide", lessons: "3 lessons" },
        { name: "3. Hard moments", lessons: "4 lessons" },
      ],
      why: "Why now: some of Mom’s key papers are missing.",
    },
  },
  tools: {
    title: "What you learn, ready to share",
    text: "Phrases that work with Mom go onto a care card for a sitter or your brother, by private link. Before a doctor visit, print a one-page sheet with your questions.",
    link: "See the care tools",
    mock: {
      caption: "Care card",
      title: "What works with Mom",
      calmsLabel: "Calms her",
      calms: "Tea together. Sinatra on low. A slow walk to the garden.",
      phrasesLabel: "Phrases that work",
      phrases: "“We have plenty of time. I’ll tell you when.”",
    },
  },
  places: {
    title: "Works wherever Mom is",
    text: "Live with her, nearby or three states away: each lesson adapts to where the hard moments actually reach you.",
    link: "How lessons adapt",
    cards: [
      { title: "In person", text: "6 pm, in the kitchen." },
      { title: "On the phone", text: "Her third call today, while you’re at work." },
      { title: "In a care home", text: "Visits and calls with the staff." },
    ],
  },
} as const;

export const HOME_SAFE = {
  title: "Calm, honest and private",
  cards: [
    {
      title: "We teach, not treat",
      text: "Communication and everyday care. For medical questions, we point you to Mom’s doctor or pharmacist.",
    },
    {
      title: "Your answers stay with you",
      text: "Saved privately to this session. No account, no name needed. No ad tracking in the quiz or the course.",
    },
    {
      title: "Clear terms",
      text: "You see the full terms and renewal date before you pay. Cancel anytime in Settings.",
    },
    {
      title: "Help is one tap away",
      text: "Need help now? sits on every screen, with 911, 988 and the Alzheimer’s Association helpline.",
    },
  ],
} as const;

export const HOME_FAQ = {
  title: "Questions",
  items: [
    {
      question: "What is Kelper?",
      answer:
        "A short online course that teaches you how to care for a parent with dementia, with a plan built around your parent and practice for real conversations.",
    },
    {
      question: "Is this medical advice?",
      answer:
        "No. We teach communication and everyday care, and help you get ready for doctor visits. For medical questions, talk to your parent’s doctor or pharmacist.",
    },
    {
      question: "Mom lives far away. Will it still help?",
      answer:
        "Yes. Lessons have a phone version for when the hard moments reach you by call, and the care card helps whoever is with her.",
    },
    {
      question: "What happens to my answers?",
      answer:
        "They are saved privately to this session, with no account and no name. We don’t sell or share them, and there’s no ad tracking in the quiz or the course.",
    },
  ],
} as const;

export const HOME_CTA = {
  title: "Start with one calm step",
  text: "Answer a few questions and see Mom’s plan before you decide anything.",
  imageAlt: "Ollie pointing the way forward",
} as const;
