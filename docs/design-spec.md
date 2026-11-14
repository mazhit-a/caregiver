# Parent Care Navigator — Design Spec (MVP)

Nov 14, 2026 · @Ali · v3

## Changelog

**v3.1 (this version)**

- The course is now built from modules. Module 1 "Talking with Mom" is the same for everyone; lessons inside a module are fixed; the quiz decides the order of the other modules, with a reason for each. This replaces the week-by-week item list.
- Lesson variants (in person / phone / not noticed yet) change only examples and tasks, never which lesson comes next.
- Lesson 1 is now "When Mom asks again": one question at the start sets the variant; the real-life task is an if-then plan in the user's own words; Day 2 always has a check-in and a 2-minute practice round, so the return works even if the moment didn't happen.
- Quick guides for urgent moments sit outside the modules.
- The diagnosis question was removed from the quiz (11 questions). The situation question already places the family, and the diagnosis added sensitive data without changing the plan.
- Second lesson to build if time allows: "Talking so it lands" (the same for everyone).

**v3**

- New section "Retention: why Jessica comes back": the core loop, return triggers that work without email or login, stored value, and retention metrics. Retention is 20% of the judging score, so it must be visible in the demo.
- New section "Design decisions and why": the reasoning behind the funnel, onboarding and lesson choices.
- Example phrases are now neutral everyday situations (Mom repeats a question about an appointment). Heavier moments, such as asking for a parent who has died, are kept for later lessons and never used as default examples.
- Quiz: every question now changes the plan (no "warm-up" questions), answers use the user's own words, and the branch point is Q3 (noticing changes / recent diagnosis / things are changing).
- M4 plan preview now opens with "What we heard" (a personal summary) and follows a 4-step selling story: pain → before / after → how → honest proof.
- One phrase from ad to button: "Mom's plan" everywhere; the main button is "Get Mom's plan".
- New free gift before the paywall: a printable "Phrases that calm Mom" sheet built from the quiz.
- Paywall: 4-week plan selected by default, 12-week as an option, no weekly plan, price and period in bold above the button, no price per day, short disclaimer, no fortune wheel, fake timers or invented social proof.
- After payment: onboarding cut to 2 screens with no repeated quiz questions, then straight into lesson 1, which continues the promise of the ad.
- Lesson structure is now "task first": every lesson opens with a scenario, then short Learn screens, with a small interaction every 2–3 screens and warm feedback even on a wrong answer.
- New guide narrator: Rosa, who cared for her own mom (not a nurse, so she doesn't read as a medical authority).
- Normal cancellation shows what the user would lose (Mom's care card, saved phrases, plan progress). No discount. The gentle exit path stays free of any retention message.
- Plan tab shows the full curriculum as modules, so the long journey is visible.
- New P0 retention items: tonight's task, "Remind me tomorrow" calendar file (.ics, no email needed), next-lesson teaser, care-card update nudge. Add to Home Screen moved to P1.
- New section "Metrics" with behavioural metrics (D0 lesson start, L1 → L2 start, active days in week 1).
- New "Build notes" section, including a small evaluation set for the AI coach in the repo.

**v2**

- Added "Hackathon constraints": 24-hour build, judges use the live URL without logging in, B2C only, web only.
- Target age is now 30–45 (was 30–50), to match the hackathon audience.
- Guest mode by default; M6 is now an optional "Save your plan" step, because judges must not need to register.
- Sibling invites and code sign-in moved to Roadmap: not needed for a guest demo.
- Paywall runs in Stripe test mode with a "Continue in demo mode (no charge)" button, so judges can pass through.
- Trust row reworded and reviewer placeholder removed, to avoid implying affiliation with licensed programs.
- Data minimization: no medications or diagnosis on handouts or Mom's page; data stays in the browser.
- Visit prep sheet now uses family notes + lesson questions, because the journal is out of the MVP.
- Journal, voice input, emails and reminders, family roles and monthly check-ins moved to Roadmap (24-hour scope).
- Today shows the return state, plus a "Simulate next day" demo control, to make retention visible.
- New "Safe by design" section, to make safety visible to judges.
- Deliverables replaced with P0 / P1 / Roadmap priorities focused on the demo path.

## Overview

Parent Care Navigator is a web course that teaches adult children how to care for a parent with dementia, with a plan built around their specific parent. Other apps organize care; we teach people how to give it. Design every screen to serve that difference.

**Product in one line:** quiz → personal course plan in modules → short lessons that start with a real scenario, with an AI role-play coach → an if-then plan for the next real moment → handouts for the sitter and the doctor.

**What we sell:** the AI role-play ("rehearse the hard conversation before it happens") plus a plan built around Mom. The role-play is the feature people come for; the course and the plan keep them.

**Target user (buyer and user):** an adult child aged 30–45 in the US whose parent (65–85) was diagnosed with dementia in the last 0–6 months. Persona: Jessica, 39, manager, two kids, mom lives alone 40 minutes away, brother in another state. She is in shock, feels guilty, has 10 minutes at a time, mostly on her phone.

**Platform:** web only, mobile-first responsive (no native app). Most sessions happen on a phone browser; handouts are also printed.

**Design principles**

1. **Calm first.** The person arrives frightened. The first screen lowers anxiety before it asks for anything.
2. **Practice, not reading.** Every lesson starts with a scenario; explanations come after and stay short.
3. **About her mom, not about dementia.** Use the parent's name and details everywhere ("Margaret", "Mom"), never generic "patient".
4. **One step at a time.** One clear next action per screen. No guilt, no "you're behind".
5. **Show progress in skills.** Progress is "what I can now handle", not streaks or time in app.
6. **Honest boundaries.** We teach and organize; we never give medical or legal advice, and the UI says so plainly.
7. **Same promise from ad to app.** The words in the ad, the quiz, the paywall and lesson 1 match.

**What we deliberately do not design for the MVP:** medication reminders, sitter alerts, refill tracking, visit-rotation calendars, open AI chat, document uploads, journal with AI field extraction, voice input, scheduled emails, family invites and roles, monthly check-in. These live in the Roadmap section.

## Hackathon constraints

The build has 24 hours from idea to a working product in production, and judges must be able to use it end to end without signing up.

- **Audience:** US adults 25–45 with jobs and families. B2C only, sold to individuals. No B2B or employer channels anywhere.
- **Platform:** web only, mobile-first, no native app.
- **Judging:** judges open the live URL and use it end to end **without mandatory registration or login**. They also read the public GitHub repo.
- **Real core value, not mocked:** the plan is built by rules from quiz answers; the AI role-play uses a real LLM call; the care card, the phrase sheet and the visit sheet are built from what the user entered. Static lesson content is fine.
- **Sensitive topic, handled carefully:** depth of pain is a plus, but no medical advice and no unnecessary sensitive data.
- **Judging weights to design for:** works end to end (40%), what we sell and why they come back (20%), who we sell to (15%), business potential (15%), originality (10%).

## Safe by design

Safety is visible in the product, not only in the policy.

- **No medical advice:** lessons teach communication and daily care. The line "We teach and organize. We don't give medical advice." appears on lessons, the role-play and handouts.
- **AI guardrails:** AI-Mom and the coach refuse medical questions and return to practice ("For medical questions, ask Mom's doctor or pharmacist."). Crisis words stop the session and open A11.
- **Minimal data:** everything stays in the user's browser; the server stores only a care card the user chooses to publish. Role-play transcripts are not stored. No diagnosis or medications on Mom's page or handouts. No ad trackers on any app screen.
- **Honest selling:** no invented reviews, no fake countdowns, no price per day, full renewal terms next to the button.
- **Help and a gentle exit:** crisis help (A11) on every screen; gentle exit (A10) with no retention offers.

## Design decisions and why

Each decision below follows a common pattern in subscription learning products and web funnels. Use the reasoning in the pitch; we will confirm the effect of each one with our own tests after launch.

| Decision in this spec | Why |
| --- | --- |
| Quiz answers written in the user's words | People finish a quiz that sounds like their own life; clinical terms feel cold and lose them |
| Every quiz question changes the plan; "What we heard" summary | The quiz is part of the product, not a warm-up. It's more honest and makes the plan feel personal |
| Branch the quiz early by situation | Someone noticing early changes and someone after a diagnosis need different first steps |
| Modules: finish one topic before the next | It feels like a course with clear progress, not a feed of articles |
| Module 1 is the same for everyone; the quiz orders the rest | Communication is needed every day at every stage; urgent topics still move up for those who need them |
| Lesson variants change examples, not the path | Lesson 2 never depends on which version of lesson 1 the user saw |
| If-then plan in the user's own words, rehearsed in practice | Specific "if this happens, then I'll…" plans are followed through far more often than general intentions |
| Don't ask the user to pick a level | Most people in this situation are complete beginners and can't judge their own level |
| Same words from ad to button ("Mom's plan") | A consistent promise builds trust; a change in wording feels like a bait-and-switch |
| Free gift before the paywall | The user gets something real before paying and sees the quality of the product |
| Personalized paywall headline | It shows the plan is really built for this person |
| Disclosure above the button, bold price and period; no price per day; short disclaimer | Honest and clear terms reduce confusion, complaints and refunds |
| No weekly plan, 4-week default, 12-week option | The journey lasts months; very short plans attract people who leave early |
| No fortune wheel, fake timers or invented reviews | Pressure tactics clash with a calm product for people in a hard moment |
| Straight from onboarding into lesson 1, which continues the ad | People who start learning on day one stay much more often than those who don't |
| Scenario first, theory second | People learn faster by trying first; it also delivers the "practice" promise in the first minute |
| Concept → example → small task inside Learn screens | Short structured screens make it clear what to do |
| Lesson → practice → real action | Learning sticks when it ends with something to do in real life |
| No open AI chat | A focused practice room is clearer and safer than a free chat |
| Cancel screen reminds of value already gained | Reminding people what they built works better than discounts, and it stays honest |

## Tone, voice and visual direction

The product should feel like a calm, experienced friend who has been through this, not like a hospital portal or a fitness app.

**Guide narrator: Rosa**

- Rosa cared for her own mom with dementia for six years. She is warm, practical and a little funny.
- She opens lessons, introduces scenarios and gives feedback. She is never presented as a nurse or doctor.
- One illustrated character, used consistently from onboarding through every lesson.

**Voice**

- Warm and practical: "Here's what helps", not "You must".
- Short sentences, plain words, grade 6–8 reading level.
- Speak to the caregiver as "you" and about the parent by name.
- Never blame, never alarm. No fear-based copy, no countdowns, no red urgency except real safety.
- Acknowledge feelings once, then move to action: "This is hard. Here's one thing you can do today."
- Feedback is warm even when the answer is not the best one: "Good instinct. Here's a gentler way."

**Visual direction**

| Element | Direction | Avoid |
| --- | --- | --- |
| Colour | Soft warm neutrals + one calm accent (e.g. deep teal or muted blue); a gentle positive colour for "done" | Clinical white-and-blue hospital look, alarm red as decoration |
| Type | Highly readable sans-serif; body 17–18 px on mobile; generous line height | Small grey text, all-caps blocks |
| Imagery | Warm illustration of everyday family moments (kitchen table, phone call, walk) and Rosa | Stock photos of sad elderly people, brains, pills |
| Layout | Single column, lots of space, one primary button per screen | Dashboards packed with widgets |
| Motion | Subtle, reassuring (a check fills in, a card slides) | Confetti, streak fireworks |
| Iconography | Simple line icons with labels | Icons without text |

**Safety and legal language** must be visible but quiet: a short line under relevant screens ("We teach and organize. We don't give medical advice.") and a persistent "Need help now?" entry point.

## Information architecture and navigation

The product has two domains plus shareable links; inside the app, four tabs carry everything, and practice is one tap from Today.

&#91;embedded content: sitemap · 3 areas, 4 app tabs\]

Bottom navigation on mobile (side bar on desktop): Today · Plan · Mom's page · Skills. The lesson player and practice open full-screen; Settings and the crisis sheet sit in the header menu and are reachable from every screen.

## Key user flows

Six flows cover the MVP, all as a guest with no login; F1 and F2 are the demo backbone.

**F1. First visit to first practice (no login; target: first scenario within 6 minutes of the landing page)**

1. Ad or search → landing (M1)
2. Quiz, 11 questions with 2 reassurance cards (M2) → building Mom's plan (M3)
3. Plan preview with "What we heard", the 4-step story and the free phrase sheet (M4)
4. Paywall in Stripe test mode, or "Continue in demo mode (no charge)" (M5)
5. Optional: "Save your plan" by email (M6) — the user can skip it
6. Onboarding, 2 screens (A0)
7. Lesson 1 opens on its first scenario (A3, A4)

**F2. Daily loop and the return state**

1. Today (A1) → today's step with the reason it was chosen
2. Scenario first → short Learn screens → AI role-play → save the best phrase
3. Your plan: an if-then plan for the next time the moment happens + one thing to do now → optional "Remind me tomorrow" (calendar file)
4. Return visit (in the demo: "Simulate next day") → check-in ("Did the moment come up?"), a 2-minute practice round, care-card update nudge if a new phrase was saved, the next lesson with its reason; skills progress updates (A7)

**F3. Visit prep sheet**

1. Today or Mom's page → "Prepare for a doctor visit"
2. Type notes from family (free text) → choose and reorder questions from the lesson
3. Print or save as PDF from the browser

**F4. Sharing with a sitter**

1. Care card preview, built from Mom's page and saved phrases
2. Publish → private link (only now is anything stored on the server) → copy or send
3. Sitter opens it on a phone, no account; the caregiver can revoke it anytime
4. When a new phrase is saved later, Today shows "Your care card has 1 new phrase. Update it?"

**F5. Normal cancellation**

1. Settings → Cancel subscription
2. One screen: "If you cancel, you'll lose access to Mom's plan, 4 saved phrases and her care card link on [date]." Buttons: "Keep my plan" / "Cancel anyway"
3. Confirmation with the end date. No discount offers, no extra steps

**F6. Gentle exit**

1. Settings → "Mom has passed away or moved to a care facility"
2. One condolence screen → cancel the (test) subscription, unpublish the care card, clear data from this browser
3. Grief-support resources; no retention message of any kind

## Screen specs: marketing funnel

The funnel must take a stressed visitor from an ad to a started plan in about 4 minutes, with no login required. No screen loads ad trackers, and quiz answers stay in the browser.

**M1. Landing page**

- Hero: "Mom's diagnosis came with a brochure. Here's the plan." + one button "Get Mom's plan (3 min)".
- Three short blocks: Learn what to say · Practice before it happens · Get a plan for your mom.
- A 10-second visual of the role-play (AI-Mom message → your reply → coach tip). This is the feature people come for; show it above the fold on desktop and right after the hero on mobile.
- Trust row: "Inspired by research on caregiver training programs" + "Not medical advice". No reviewer placeholder unless a real, named reviewer exists.
- FAQ: price and cancel, what it is and isn't, privacy ("Your answers stay in your browser").

**M2. Quiz (11 questions, one per screen)**

- Progress bar with question count; back button; large tap targets (min 48 px).
- Question types: single choice cards, multi-select chips, a 3-state grid (documents), a 1–5 scale (confidence).
- First screen note: "No sign-up needed. Your answers stay in this browser."
- Q3 is the branch point (noticing changes / diagnosed in the last 6 months / diagnosed a while ago and things are changing / just home from the hospital). Copy after Q3 adapts to the branch.
- No diagnosis question. Screens with health-related answers (situation, changes noticed) show the note "This page has no ad tracking. Your answers stay private."
- After Q5 and Q9 show a short reassurance card.
- **Rule: every question must change something the user gets** (the plan, the lesson order, the phrase sheet, Today's reasons). If a question changes nothing, remove it.
- Answer options use the user's words ("Asks the same questions again and again"), not clinical terms ("repetitive behaviour").
- Questions, options and tags: see quiz.json.

**M3. Building Mom's plan (loading moment, 3–5 s)**

Animated checklist reflecting the answers: "Starting with how to talk with Mom… Moving papers up, while Mom can take part… Setting the pace to fit your day…" Each line comes from a real rule in plan-rules.json.

**M4. Plan preview (the selling page)**

Four blocks in this order, then the gift and the button:

1. **What we heard** (personal summary): "Mom was diagnosed recently. You're handling most of it alone, while working full-time. What worries you most: knowing what to say, and paperwork." Built from quiz answers.
2. **Before / after:** "Today: you don't know what to say when Mom repeats herself. In 30 days: you have phrases that work, practiced out loud, and a plan your brother can see."
3. **How:** "Your course, module by module": Module 1 "Talking with Mom" (everyone starts here) and the next two modules in full, each with "Why now: …" and its lessons; the first lesson fully visible, the rest partly blurred. The remaining modules as a short "Coming later" map, plus quick guides for urgent moments. Pace line: "About 8 minutes a lesson, 4 lessons a week".
4. **Honest proof:** "1 in 4 US adults cares for a family member, and most never got any training" (AARP) + "Caregiver training programs that include practice lower stress more than reading alone" (REACH research). No invented testimonials.

- **Free gift:** "Phrases that calm Mom", a printable sheet with 5 phrases matched to the quiz answers. Free, real, downloadable before the paywall.
- Sticky button: **"Get Mom's plan"**.

**M5. Paywall**

- Headline personalized from the quiz: "Mom's 30-day plan is ready" + one line from "What we heard".
- Plans: 4-week (selected by default, labelled "Most chosen" only if true in tests; otherwise no label), 12-week (better price per period). No weekly plan. Intro price clearly labelled. Prices TBD by test.
- **Above the button, in bold:** price today, price after the intro, renewal period, first renewal date. "Cancel anytime in Settings → Subscription."
- No price per day. Disclaimer short and plain.
- Separate unchecked checkbox for auto-renewal consent (required to continue).
- Stripe Checkout in **test mode**, with a visible hint: "Test mode: use card 4242 4242 4242 4242, any future date, any CVC."
- A clearly labelled secondary button: "Continue in demo mode (no charge)", so judges can pass through.
- No fortune wheel, no fake timers, no "X people are viewing this".
- States: loading, card error, success, returned from Stripe.

**M6. Save your plan (optional)**

An optional step after payment: "Save your plan to come back on another device" with an email field and a prominent "Skip for now". Not required anywhere in the demo path; the plan works as a guest in this browser.

## Screen specs: app

The practice screens (A3, A4, A5) are the hero of the product and get the most design time.

**A0. Onboarding (2 screens, then straight into lesson 1)**

1. Rosa welcomes: "I'm Rosa. I cared for my mom for six years. Let's start with the moment that comes up most." Shows the first item of Mom's plan from the quiz.
2. Mom's profile, minimal: name or nickname (prefilled from Q1 label), what calms her (optional). Everything else is collected later inside lessons.
3. Lesson 1 opens immediately on its first scenario. No empty dashboard, no repeated quiz questions.

The 5 confidence sliders move to the end of lesson 1 ("Before we go on: how ready do you feel for these?"), so the user reaches practice first.

**A1. Today (home)**

- Greeting with the parent's name: "Today with Mom".
- Hero card: today's step (lesson title, time estimate, skill chip, "Start" button) with the reason it was chosen. Only one hero.
- **On return, Today shows (in this order):**
  1. Check-in on the plan: "Did Mom ask the same question again since yesterday?" → Yes: "How did your plan go? ('You're wondering about tomorrow. We have plenty of time…')" → It helped / Partly / It didn't help · Not yet: "Your plan is ready for when it does." The quote is always the user's own plan. Then a 2-minute practice round.
  2. Care-card nudge, if a new phrase was saved: "Your care card has 1 new phrase. Update it?"
  3. The next lesson with its reason: "Because Mom gets upset in the evenings."
- Secondary links: "Prepare for a doctor visit" (H2), sitter care card (H1).
- Weekly rhythm (not a streak): "This week: 2 of 3 practice sessions." Missing a day is never shown as failure.
- Small readiness ring ("Mom's plan: 6 of 12 done").
- Demo control: a small, clearly labelled "Simulate next day (demo)" link so judges can see the return state.
- Persistent "Need help now?" link.
- Empty/edge states: all done for today ("You're done for today. Rest counts too."), returning after 7+ days (welcome-back screen: what this is, where you stopped, one next step; no guilt copy).

**A2. Plan**

- The course as modules, in the order built from the quiz. Current module expanded with its lessons as a vertical path; completed lessons checked; next lesson highlighted.
- Every module explains why it is in this place: "Why now: because some of Mom's key papers are missing."
- Lessons inside a module are fixed and the same for everyone. Module 1 "Talking with Mom" always comes first.
- Later modules shown as "Coming later", not as locked padlocks.
- Quick guides (after a hospital stay, if Mom goes missing, after a fall, a sudden change, you're at your limit) in their own section; the ones that match the quiz are marked "For now".
- Each module ends with a review lesson (e.g. "Your phrase book"): all saved phrases, one mixed practice round, "what you can handle now".
- Source: plan-rules.json (modules, lessons, order rules). One lesson fully built in the MVP.

**A3. Lesson player (Scenario → Learn → Practice → Your plan → Check-in)**

- Step indicator with named steps.
- **One question, then the scenario:** lesson 1 opens with "Where do Mom's repeated questions usually reach you?" (in person / on the phone / both / I haven't noticed it yet). The answer picks the variant of the scenario, the practice and the "do now" task. Variants never change which lesson comes next. Then the scenario with a quick choice: "What would you say?" No explanation before it.
- **Learn:** 3–5 short screens (swipe or Next), max ~80 words each, one key idea in bold, concept → example → small task. A small interaction every 2–3 screens (tap the better phrase, sort two replies).
- **Practice:** AI role-play (A5); scenarios (A4) as the fallback.
- **Your plan:** an if-then plan in the user's own words ("If Mom asks again, then I'll say…", plus a reset like one slow breath), pre-filled with their best phrase. Plus one thing to do now that works for everyone (a note for the fridge, a phrase saved on the phone, or noting repeats on the next call or visit), and "Remind me tomorrow" (downloads a calendar file; nothing is sent to a server).
- **Check-in:** on the next visit, Today asks "Did the moment come up?" first; then "How did your plan go?" if yes. A 2-minute practice round follows either way.
- End of lesson: what you can now handle (skill chip filled), the saved phrase, and what comes next in the module. The ending is the same for every variant, so the next lesson never depends on which variant the user saw. The next lesson opens with a short recap of the shared pattern and the user's saved phrase.
- Exit anytime; progress saved; "Continue where you left off".

**A4. Scenario practice (multiple choice)**

- Situation card: short story with the parent's name, time of day, a simple illustration; quote bubble from Mom.
- 3–4 answer cards. After choosing: feedback panel with a verdict (Best / Okay / Try again, never "Wrong!" in red), what Mom might feel, why. Feedback is warm on every answer.
- Best answer: "Save this phrase to What works with Mom" button.
- Allow trying another answer to compare.

**A5. AI role-play coach (the signature screen)**

- Chat-like layout but clearly a practice room: header "Practice: Mom asks the same question again" + goal of the exercise (3 coach criteria shown as chips: Name the feeling · Don't argue · Redirect).
- AI-Mom messages on the left (warm avatar, not a photo); the caregiver types on the right (text only in the MVP).
- After each reply: coach panel slides up with the 3 criteria ticked or not, one sentence of feedback, and a suggested better phrase ("Try: We have plenty of time. I'll let you know. Want to help me with the tea?").
- Session length: 3–5 exchanges, then a summary card (score per criterion, first try vs this try, best phrase, "Save", "Practice again").
- Required states: AI thinking, AI unavailable (fallback to multiple-choice scenario), medical question ("For medical questions, ask Mom's doctor or pharmacist." then back to practice), crisis words detected (stop the session, open A11).
- Labels: "AI practice partner. We teach and organize. We don't give medical advice." and "This conversation isn't saved. Only phrases you save are kept."

**A6. Practice your real moment** — moved to Roadmap (depends on the journal).

**A7. Skills progress**

- Per practiced skill: role-play score first try vs latest (e.g. "1 of 3 → 3 of 3") and scenarios answered best.
- Confidence: first check vs latest (5 sliders).
- Counts: scenarios practiced, phrases saved, real tasks tried, tasks that helped (from the check-in).
- "Next" recommendation with its reason.

**A8. Mom's page**

- Minimal and non-medical only: profile (name, what she enjoys, what calms her, things to avoid, daily rhythm), saved phrases ("What works with Mom"), contacts for the care card.
- Grows through lessons: Apply steps add to it ("Add 'garden' to what calms Mom?").
- No diagnosis, medications, documents or journal on this page.
- Entry points: "Preview care card" (H1) and "Prepare for a doctor visit" (H2).
- Note at the top: "Saved in this browser only."

**A9. Sharing**

- Sitter care-card link only: publish, copy, revoke, last opened.
- Family invites by email, roles and code sign-in are in the Roadmap.

**A10. Settings, subscription and exits**

- Subscription: plan, test-mode or demo status, "Cancel subscription" (F5: one value reminder, no discounts, 2 clicks total).
- Gentle exit (F6): "Mom has passed away or moved to a care facility" → condolence → cancel, unpublish the care card, clear data from this browser → grief-support resources. No retention message on this path.
- Privacy: "Clear my data from this browser" and "Unpublish care card".

**A11. Need help now? (crisis sheet)**

Bottom sheet reachable from every screen: 911 for emergencies, 988 Suicide & Crisis Lifeline, Alzheimer's Association 24/7 Helpline, Adult Protective Services. Large tap-to-call buttons. Numbers verified before launch.

## Retention: why Jessica comes back

Retention comes from three things: an open loop every day (a real task and a check-in about it), value that keeps growing (Mom's page, the care card, skills), and a journey that changes with Mom's stage. All of it works without email or login in the MVP.

**1. The core loop (every session)**

Scenario → practice with AI-Mom → an if-then plan for the next real moment → next visit: "Did it come up? How did it go?" → a 2-minute practice round → the next lesson in the module.

The if-then plan is the hook: the user leaves with a concrete plan for the next time the moment happens, rehearsed in the AI practice. The return does not depend on the moment happening that night: "Not yet" still leads to a short practice round and the next lesson. "It didn't help" routes to short follow-ups (look for a pattern, shorter answer and a written note, a small task to give her), so a bad night becomes a next step, not a reason to quit.

**2. Return triggers in the MVP (no email, no login)**

| Trigger | How it works | Priority |
| --- | --- | --- |
| If-then plan + check-in | The plan step sets it; Today asks "Did the moment come up?" on return, then offers a 2-minute practice round | P0 |
| "Remind me tomorrow" | Downloads a calendar file (.ics) with a check-in for the next evening and a link back to the app; nothing is stored on a server | P0 |
| Next-lesson teaser | End of each lesson shows the next lesson and why it's next ("Because Mom gets upset in the evenings") | P0 |
| Care-card update nudge | A new saved phrase → "Update the sitter's card?" on Today; the sitter link becomes more useful over time | P0 |
| Add to Home Screen | Prompt after the first lesson so the web app opens like an app from the phone's home screen | P1 |
| Welcome-back screen | After 7+ days away: what this is, where you stopped, one next step | P1 |

**3. Value that grows (a reason not to leave)**

- **Mom's page and saved phrases:** every lesson adds something about Mom. After a month it is a record no other app has.
- **The care card:** shared with the sitter or a sibling, so other people rely on it too.
- **Skills progress:** first try vs latest makes progress visible ("1 of 3 → 3 of 3").
- The normal cancel screen (F5) reminds the user of exactly this value, without discounts.

**4. A journey that follows Mom (why a subscription, not a one-time course)**

- Dementia often lasts years, and each stage brings new situations: repeated questions, then evening confusion, then refusing help, then decisions about more care.
- The Plan tab shows the whole course as modules in Mom's order; each module has a reason ("Why now").
- In the Roadmap: a "Something new is happening" check on Today and a monthly check-in that unlock units when they become relevant, plus short crisis guides.
- The AI role-play never runs out: every new behaviour is a new conversation to rehearse.

**5. What we don't do**

- No streak fire, no guilt messages, no "you're falling behind". The weekly rhythm (3 short sessions a week) fits a caregiver's real life.
- No retention offers on the gentle exit. Ending because Mom passed away or moved to a facility is a natural end of the journey, not churn to fight.

**6. What the demo must show (for the 20% "why they come back")**

1. Finish lesson 1 → if-then plan → "Remind me tomorrow".
2. Tap "Simulate next day (demo)".
3. Today shows the check-in, a 2-minute practice round, the care-card nudge and the next lesson in Module 1.
4. Skills progress shows first try vs latest.

## Handouts

Three handouts turn what the caregiver learned and entered into something another person can use. All are non-medical and print on one US Letter page (black-and-white friendly); the care card can also be shared by link.

**H0. Phrases that calm Mom (free gift in the funnel)**

5 phrases matched to the quiz answers, each with one line on when to use it. Uses the H1 print layout. Footer: "We teach and organize. We don't give medical advice."

**H1. Sitter care card — "What works with Mom"**

Audience: a paid sitter, a sibling, a neighbor. Opened by a private link, no account, read on a phone in seconds.

| Block | Content | Source in app |
| --- | --- | --- |
| Header | Parent's name, "Updated [date] by Jessica" | Mom's page |
| She loves | 3–5 things (garden, Sinatra, teaching stories) | Mom's page |
| Calms her | 2–4 things | Mom's page |
| Phrases that work | 3–5 saved phrases | Saved from practice |
| Try to avoid | 2–4 items | Mom's page |
| Daily rhythm | Wake, meals, rest, bed | Mom's page |
| Contacts | Caregiver, 911, Alzheimer's Association 24/7 Helpline | Mom's page + defaults |

States: preview (in the browser only), published (private link; the server stores only this card), update available (new phrases saved since publishing), revoked ("This card is no longer shared"). No diagnosis or medications ever appear on the card. Actions: copy link, print, update, revoke.

**H2. Visit prep sheet**

Audience: the parent's doctor. Built from what the caregiver types and the lesson questions; printed or saved as PDF from the browser. Nothing is sent to the server.

| Block | Content | Rule |
| --- | --- | --- |
| Header | Parent's name, visit date and doctor, prepared by | — |
| Notes from family | Free text the caregiver types (what they've noticed, in their own words) | Caregiver's words, no app interpretation |
| Our questions | Questions from the lesson "Getting the most from 15 minutes" plus the caregiver's own; top 3 first, editable, reorderable | From lesson + caregiver |
| Doctor's answers | Empty lines for notes | — |
| Footer | "Family observations, not a medical assessment." | Always shown |

In-app flow: open from Today or Mom's page → type notes → choose and drag to reorder questions → preview → print / save as PDF.

## Components, states and rules

Build a small component library first; every screen above is assembled from it.

**Core components**

| Component | Variants / states |
| --- | --- |
| Button | Primary, secondary, text; loading, disabled |
| Quiz option card | Single, multi-select chip, 3-state grid row, 1–5 scale; selected, focus |
| Reassurance card | Text + Rosa illustration + Continue |
| Summary block | "What we heard" lines built from answers |
| Lesson card | Not started, in progress, done, with "why you're seeing this" |
| Learn screen | Text + optional illustration; key idea highlight; inline mini-interaction |
| Scenario answer card | Default, selected, Best / Okay / Try again feedback |
| Feedback panel | Verdict, what Mom may feel, why, save-phrase action |
| Role-play bubbles | AI-Mom, caregiver, coach panel (3 criteria chips, tip, suggested phrase) |
| Rosa bubble | Narrator line with avatar |
| Skill chip and progress row | First try vs latest score; confidence first vs latest |
| Readiness ring | 0–100%, with "x of y done" label |
| Weekly rhythm | "2 of 3 this week", no streak styling |
| Check-in card | Did the moment come up? Yes / Not yet; then It helped / Partly / It didn't help |
| Plan card | If-then plan, "do now" task, "Remind me tomorrow" (.ics), done state |
| Nudge card | Care-card update, welcome back |
| Handout preview | Preview, published, update available, revoked; print view |
| Banner | Info, success, safety (crisis), test-mode / demo-mode notice |
| Demo control | "Simulate next day (demo)": small, clearly labelled |
| Bottom sheet | Crisis resources, confirmations |
| Empty state | Friendly illustration + one action |

**Every data screen needs:** loading (skeletons), empty, error (with retry), offline notice, and success states.

**Accessibility (WCAG 2.2 AA)**

- Contrast at least 4.5:1 for text; never colour alone for meaning (feedback uses icon + word).
- Tap targets at least 48 × 48 px; body text 17–18 px on mobile; supports 200% zoom.
- Full keyboard navigation and visible focus; screen-reader labels for chips, rings and role-play messages.
- Plain language; avoid jargon or explain it inline ("healthcare proxy: the person who can make medical decisions if Mom can't").

**Responsive**

Design mobile first at 375 px, then tablet 768 px and desktop 1280 px (single centered column, max ~680 px for reading; handouts at print size).

**Content rules for examples and scenarios**

- Default examples use neutral, everyday moments (a repeated question about an appointment, a lost item, a refused shower), not the most painful ones.
- Heavier moments (asking for a parent who has died, not being recognized) live in later lessons, are introduced gently, and are never used on the landing page, the paywall or as default examples.
- Don't assume the family structure: the other parent may be alive, divorced or not part of the story. Use "Mom" or "Dad" from Q1 and avoid naming other relatives unless the user added them.
- Check-in cards and handouts quote the user's own plan and saved phrases, not a fixed example.

**Safety UI rules**

- "We teach and organize. We don't give medical advice." on lessons, the role-play screen and handouts.
- Crisis entry point on every app screen.
- No ad trackers on any screen.
- No medical fields anywhere: no medications and no diagnosis question.
- Data stays in the browser; only a published care card is stored on the server. Role-play transcripts are never stored.
- AI-generated text is always labelled.
- No invented reviews, fake timers or price per day anywhere.

## Metrics

We track behaviour, not only cancellations: cancellations react slowly to product changes, while lesson starts and active days show quickly whether the product works.

| Stage | Metric | Why |
| --- | --- | --- |
| Funnel | Landing → quiz start → quiz complete → plan preview → paywall → subscribe | Find the step that leaks |
| Funnel | Gift download rate | Is the gift valued? |
| Activation | Started lesson 1 on day 0 | People who start learning on day one are much less likely to cancel early |
| Activation | First role-play completed in session 1 | The feature people come for |
| Engagement | Lesson 1 → lesson 2 start; active days in week 1; practice sessions per week | They react quickly to changes in content |
| Return | Check-in answered on return; practice round done; D1 and D7 return | The core loop works |
| Value | Tasks that "helped" (from the check-in); phrases saved; care cards published and updated | Real-life value, not time in app |
| Outcome | Confidence first vs after 30 days; role-play score first try vs latest | We actually build the skill |
| Business | D0 / D7 unsub, refund rate, cancellation reasons (gentle exit counted separately) | Health of the subscription |

In the MVP these are logged in the browser only (no trackers); the pitch shows how they will be measured after launch.

## Priorities

Design P0 first: it is exactly what judges click through in production, without logging in.

| Priority | Screens |
| --- | --- |
| P0 (must work in production for the demo) | M2 quiz, M3 loader, M4 plan preview (incl. "What we heard" and the module order), M5 paywall (test mode + demo mode), A0 onboarding (2 screens), A1 Today (incl. return state, check-in, 2-minute practice round, care-card nudge, "Simulate next day"), A3 lesson player for ONE lesson ("When Mom asks again", with its 3 variants), A4 scenarios, A5 AI role-play, if-then plan + "Remind me tomorrow" (.ics), A8 Mom's page (minimal: profile + saved phrases), H1 care card (link + print + update), H2 visit sheet (print), A7 skills progress (simple), A11 crisis sheet, A10 gentle exit and normal cancel (one screen each) |
| P1 | M1 landing, H0 free phrase sheet, A2 plan view with all modules, M6 save your plan, Add to Home Screen, welcome-back screen, a second lesson ("Talking so it lands", the same for everyone) |
| Roadmap | See below |

**Demo path:** quiz → "What we heard" → paywall (test mode) → lesson "When Mom asks again" (scenario first) → AI role-play → save phrase → if-then plan → "Simulate next day" → check-in + practice round + care-card nudge → care card → visit prep sheet → skills progress.

**Hand-off package:** component library with tokens (colour, type, spacing), mobile + desktop frames for P0, all states listed above, clickable prototype of the demo path, print layouts for H0, H1 and H2, illustration set (6–8 scenes + Rosa).

## Build notes

- Next.js on Vercel; production URL deployed in the first hour.
- LLM called from a server route; API key in environment variables, never in the repo.
- Small KV/DB (Supabase or Vercel KV) only for published care card links.
- Handouts via print CSS (@media print), US Letter; no PDF library needed.
- "Remind me tomorrow" builds the .ics file in the browser.
- Role-play fallback: if the LLM fails or is slow, switch to multiple-choice scenarios.
- Content and rules live in JSON files: quiz.json, plan-rules.json (modules and order rules), lesson files, role-play prompts.
- **evals/** folder: about 10 sample caregiver replies (strong, weak, arguing, a medical question, crisis words) with the expected coach result, run before the demo to check the coach prompt.
- README: what the product is, architecture, what is real vs test mode, how to run locally, how to run the evals.

## Roadmap

Not in the MVP; designed later.

- Journal with AI field extraction and "Practice your real moment" (A6)
- Voice input in the role-play
- Plan-based emails with consent (check-in, next lesson), not marketing blasts
- Family invites, roles and code sign-in
- "Something new is happening" check and monthly check-in that unlock units
- Short crisis guides (she's missing, after a fall, hospital admission, you're at your limit)
- More lessons across all 14 units
- Short video explainers (around 1.5 minutes)
- Annual Medicare open-enrollment module

## Open questions

- [ ] Product name and logo final, or keep "Parent Care Navigator" for the competition?
- [ ] Accent colour, illustration style and Rosa's look: who approves?
- [ ] Number of paywall tiers and prices (from the fake-door test).
- [ ] Do we build the second lesson ("Talking so it lands") if P0 is done early?
- [ ] Gift sheet (H0): P1 as planned, or P0 if the print layout from H1 is ready early?
