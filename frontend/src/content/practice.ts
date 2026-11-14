/** Copy for the /practice page, from the design. Round data lives in practiceScript.ts. */

export const PRACTICE_COPY = {
  seoTitle: "Practice with Ollie | Kelper",
  seoDescription: "Practice what to say in a hard moment with Ollie, a friendly AI practice partner.",
  hero: {
    title: "Practice the hard conversation before it happens",
    lead: "Knowing what to say is easy to read and hard to do at 6 pm on a long day. So you rehearse it: Mom asks, you answer, Ollie shows what worked.",
    imageAlt: "Ollie giving a thumbs-up with a wink",
  },
  demo: {
    title: "Try a practice session",
    toggleLabel: "Where the moment happens",
    footnote:
      "Preview with set answers. In the course you type your own words, and an AI practice partner answers as Mom.",
    savedNote: "In the course, your best phrase is saved to Mom’s page and her care card.",
  },
  pattern: {
    title: "One simple pattern for hard conversations",
    steps: [
      {
        title: "Notice the feeling",
        example: "“You’re wondering about tomorrow.”",
        why: "The question often comes from worry, not missing facts.",
      },
      {
        title: "Reassure",
        example: "“We have plenty of time. I’ll tell you when.”",
        why: "Take the job of remembering off her.",
      },
      {
        title: "Offer something to do",
        example: "“Want to help me with the tea?”",
        why: "Busy hands quiet a worried loop.",
      },
    ],
  },
  real: {
    title: "In the course, practice gets real",
    items: [
      "You type what you’d really say, in your own words.",
      "Rounds get harder, the way real moments do.",
      "Ollie scores every reply and suggests a better phrase.",
      "Your best phrase becomes your plan for next time.",
    ],
  },
  not: {
    title: "What practice is not",
    items: [
      "Not a chatbot for anything you like: it stays on the conversation you’re practicing.",
      "Not medical advice: medical questions go to Mom’s doctor or pharmacist.",
      "Not stored: the conversation isn’t saved. Only phrases you choose to keep are.",
    ],
  },
  cta: { title: "Your first practice is in lesson 1" },
} as const;
