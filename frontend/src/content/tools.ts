/** Copy for /care-tools, from context/design/kelper-landing/care-tools (privacy line changed per the plan). */

export const TOOLS_SEO = {
  title: "Care tools | Kelper",
  description: "Printable and shareable tools: a page for Mom, a care card and a visit sheet.",
};

export const TOOLS_HERO = {
  title: "What you learn, ready to share",
  lead: "Every lesson adds to Mom’s page. From there, one tap makes a care card for whoever is with her, or a one-page sheet for her next doctor visit.",
  image: { alt: "Ollie writing in a small notebook", width: 482, height: 640 },
};

export const MOMS_PAGE = {
  title: "Mom’s page",
  lead: "What she enjoys, what calms her, what to avoid, her daily rhythm, and the phrases that work with her. About Mom as a person, not her illness.",
  privacy: "No diagnosis, no medicines. Saved privately to this session.",
  caption: "Example page",
  fields: [
    { label: "She loves", value: "Her garden, Sinatra, stories about teaching", tone: "butter" },
    { label: "Calms her", value: "Tea together, a slow walk", tone: "iris" },
    { label: "Try to avoid", value: "Correcting her, rushing, loud rooms", tone: "muted" },
    { label: "Daily rhythm", value: "Up at 7, lunch at 12, rest after 3", tone: "muted" },
  ],
  phrasesLabel: "Phrases that work",
  phrases: ["“We have plenty of time. I’ll tell you when.”", "“That sounds upsetting. Let’s look for it together.”"],
} as const;

export const CARE_CARD = {
  title: "A care card for whoever is with her",
  lead: "Send a private link to a sitter, a neighbor or your brother. It opens on any phone, no account needed, and reads in seconds.",
  bullets: ["Update it when you save a new phrase.", "Print it for the fridge.", "Turn the link off anytime."],
  caption: "Example care card",
  mock: {
    updated: "Example: updated Nov 15",
    title: "What works with Mom",
    sections: [
      { label: "Calms her", value: "Tea together. Sinatra on low. A slow walk to the garden." },
      { label: "If she asks the same thing again", value: "“We have plenty of time. I’ll tell you when.” Then offer tea." },
      { label: "Try to avoid", value: "Correcting her. Saying “you already asked.”" },
    ],
    contactsLabel: "Contacts",
    contacts: "Jessica: (555) 014-2290. Emergency: 911.",
  },
};

export const VISIT_SHEET = {
  title: "One page for the doctor",
  lead: "A visit is about 15 minutes. Bring your notes and your top questions on one printed page, with space for the answers.",
  note: "Family observations, not a medical assessment.",
  caption: "Example visit sheet",
  mock: {
    title: "Visit prep: Mom",
    when: "Thu, 2 pm",
    notesLabel: "Notes from family",
    notes: "Asks about plans many times a day, mostly in the evening. Calmer with a note on the fridge.",
    questionsLabel: "Our questions",
    questions: [
      "What changes should we expect in the next months?",
      "Who can we call between visits?",
      "Is there anything at home we should change?",
    ],
    answersLabel: "Doctor’s answers",
  },
};

export const PHRASE_SHEET = {
  title: "Free: phrases that calm Mom",
  lead: "After the quiz, you get 5 phrases picked for your situation, ready to print or keep on your phone. Yours to keep, whether or not you continue.",
  samples: ["“You’re safe. I’m here with you.”", "“That’s okay. Let’s try again a little later.”", "“Tell me about home. What do you miss most?”"],
};

export const TOOLS_CTA = { title: "Get your free phrase sheet", label: "Get Mom’s plan" };
