/** Canned practice-preview data, copied from the design. Display only: no network, no coach. */

export type Goals = readonly [boolean, boolean, boolean];

export interface PracticeOption {
  text: string;
  /** Notice the feeling, Reassure, Offer something to do. */
  goals: Goals;
  tip: string;
  mom: string;
}

export interface PracticeRoundData {
  stage: string;
  line: string;
  options: readonly PracticeOption[];
}

export type PracticeVariant = "in_person" | "phone";

export const GOAL_LABELS = ["Notice the feeling", "Reassure", "Offer something to do"] as const;

/** Display arithmetic over canned data; the real coach scores in the backend. */
export function scoreOf(option: Pick<PracticeOption, "goals">): number {
  return option.goals.filter(Boolean).length;
}

const T = true;
const F = false;

export const HOME_ROUND: PracticeRoundData = {
  stage: "It’s 6 pm. Her appointment is tomorrow. For the fifth time today, she asks:",
  line: "When are we going to the doctor?",
  options: [
    {
      text: "Mom, I told you already. It’s tomorrow.",
      goals: [F, F, F],
      tip: "Almost everyone says this, and it’s true. But it reminds her she forgot, so the worry stays.",
      mom: "Oh. I’m sorry. I don’t know why I keep asking.",
    },
    {
      text: "It’s tomorrow at 2. I wrote it on the calendar for you.",
      goals: [F, T, F],
      tip: "Kind and clear. Try naming the worry first, so the question doesn’t come back.",
      mom: "Tomorrow at 2. Okay.",
    },
    {
      text: "You’re wondering about tomorrow. We have plenty of time, I’ll tell you when. Want to help me with the tea?",
      goals: [T, T, T],
      tip: "All three steps: you noticed the feeling, reassured her, and gave her something to do.",
      mom: "Tea sounds nice. I’ll get the cups.",
    },
  ],
};

export const PRACTICE_SCRIPT: Record<PracticeVariant, readonly PracticeRoundData[]> = {
  in_person: [
    {
      stage: "It’s 6 pm. Her appointment is tomorrow.",
      line: "When are we going to the doctor?",
      options: [
        {
          text: "Mom, I told you already. It’s tomorrow.",
          goals: [F, F, F],
          tip: "Almost everyone says this, and it’s true. But it reminds her she forgot.",
          mom: "Oh. I’m sorry. I don’t know why I keep asking.",
        },
        {
          text: "It’s tomorrow at 2. I wrote it on the calendar for you.",
          goals: [F, T, F],
          tip: "Kind and clear. Try naming the worry first.",
          mom: "Tomorrow at 2. Okay.",
        },
        {
          text: "You’re wondering about tomorrow. We have plenty of time, I’ll tell you when. Want to help me with the tea?",
          goals: [T, T, T],
          tip: "All three steps: feeling, reassurance, something to do.",
          mom: "Tea sounds nice. I’ll get the cups.",
        },
      ],
    },
    {
      stage: "Ten minutes later.",
      line: "Something’s wrong, isn’t it? Why are we going to the doctor?",
      options: [
        {
          text: "Nothing’s wrong, I already told you. It’s just a checkup.",
          goals: [F, T, F],
          tip: "Calm, but “I already told you” points at the forgetting.",
          mom: "Then why won’t anyone tell me anything?",
        },
        {
          text: "You sound worried. I’m right here, and everything’s taken care of. Want to sit in the garden with me?",
          goals: [T, T, T],
          tip: "You noticed the worry and gave her a calm place to go.",
          mom: "The garden sounds nice.",
        },
        {
          text: "Mom, please, we’ve talked about this five times.",
          goals: [F, F, F],
          tip: "Understandable after five times. A slow breath first helps.",
          mom: "I’m sorry. I don’t remember.",
        },
      ],
    },
    {
      stage: "Later that evening.",
      line: "Why won’t you just tell me? You’re hiding something.",
      options: [
        {
          text: "I’m not hiding anything! I’ve told you five times.",
          goals: [F, F, F],
          tip: "Defending yourself is natural, but it turns into an argument.",
          mom: "You’re shouting at me.",
        },
        {
          text: "It sounds like you feel left out. I’ll tell you everything as it happens. Want to look at the calendar together?",
          goals: [T, T, T],
          tip: "You named the feeling and gave her a shared next step.",
          mom: "All right. Show me.",
        },
        {
          text: "Okay, okay. It’s at 2 tomorrow.",
          goals: [F, T, F],
          tip: "It answers the question, but not the feeling of being left out.",
          mom: "Fine.",
        },
      ],
    },
  ],
  phone: [
    {
      stage: "You’re at work. Mom calls for the third time today.",
      line: "When are you coming on Saturday?",
      options: [
        {
          text: "Mom, I told you already. Saturday. I’m at work.",
          goals: [F, F, F],
          tip: "Almost everyone says this mid-workday. But it reminds her she forgot.",
          mom: "Oh. I’m sorry to bother you.",
        },
        {
          text: "Saturday morning, around ten.",
          goals: [F, T, F],
          tip: "Clear and kind. Try naming the feeling behind the call too.",
          mom: "Saturday. Okay.",
        },
        {
          text: "You’re wondering when I’ll come. I’ll call before I leave, so you don’t have to keep track. What are you doing right now?",
          goals: [T, T, T],
          tip: "All three steps. You took the job of remembering off her.",
          mom: "I’m just having my coffee by the window.",
        },
      ],
    },
    {
      stage: "Twenty minutes later, she calls again.",
      line: "Are you still coming? Nobody tells me anything.",
      options: [
        {
          text: "Yes, Mom, like I said an hour ago.",
          goals: [F, T, F],
          tip: "“Like I said” points at the forgetting. The feeling is being left out.",
          mom: "You never said that.",
        },
        {
          text: "It’s hard when you don’t know the plan. I’m coming Saturday, and I’ll call before I leave. Tell me about your morning?",
          goals: [T, T, T],
          tip: "You named the feeling and gave her something new to talk about.",
          mom: "Well, the mailman came early today.",
        },
        {
          text: "I can’t talk now, I’m at work.",
          goals: [F, F, F],
          tip: "Fair, and sometimes true. A short warm line first helps the call end well.",
          mom: "Oh. All right then.",
        },
      ],
    },
    {
      stage: "Another call, later that afternoon.",
      line: "You forgot about me, didn’t you?",
      options: [
        {
          text: "Of course not, don’t be silly.",
          goals: [F, T, F],
          tip: "Reassuring, but “silly” can sting. Name the feeling instead.",
          mom: "I’m not being silly.",
        },
        {
          text: "You’re missing me. I could never forget you. I’ll call you tonight. What should we do together on Saturday?",
          goals: [T, T, T],
          tip: "Warm, clear, and it gives her something to look forward to.",
          mom: "We could go to the bakery.",
        },
        {
          text: "Mom, I call you every day!",
          goals: [F, F, F],
          tip: "True, and frustrating. But arguing with the feeling makes it grow.",
          mom: "Do you? It doesn’t feel like it.",
        },
      ],
    },
  ],
};
