# content/

Content and rules for the funnel. No code here: the app reads these files.

| File | What it is | Used by |
| --- | --- | --- |
| quiz.json | 11 questions, 2 reassurance cards, tags, "What we heard" fragments | QuizStep component, tag collector |
| plan-rules.json | Modules and lessons; turns tags into the module order with reasons, plus summary, before/after, loader lines, quick guides, gift phrases | planBuilder (pure function, unit-tested) |
| funnel-copy.json | All funnel texts: landing, quiz intro, loader, plan preview, paywall, save plan | Funnel screens |
| app-copy.json | App strings after the paywall that carry the recipient label (nav, page titles, care-card and gentle-exit wording, welcome card) | `GET /api/app-copy` |
| pricing.json | Demo plans (4-week default, 12-week), Stripe test-mode price ids | Paywall, checkout route |
| phrases.json | Phrase bank for the free gift sheet | Gift sheet (H0), lessons |
| lessons/m1_l1.json | Lesson 1 "When Mom asks again": setup question and 3 variants, scenario, 4 learn screens, AI practice rounds, if-then plan, wrap-up, Day 2 check-in and practice round, recap for lesson 2 | Lesson player (A3–A5), Today (Day 2) |
| prompts/roleplay-turn.md | System prompt, input and output JSON for one AI practice turn (parent + coach), local safety check | Server route for the role-play |
| evals/roleplay-evals.json | 14 test cases for the coach prompt | Run before the demo and after prompt changes |
| state-contract.md | What is stored in the browser and who writes / reads it | Funnel and app |
| funnel-qa.md | Test personas, checklist, local events | QA before every submission |

Build order (funnel): state helpers → QuizStep from quiz.json → tags → planBuilder + tests (3 personas in state-contract.md) → loader → plan preview → paywall (test mode + demo button) → save plan → hand-off to onboarding.

Build order (lesson 1): lesson player reading m1_l1.json with the variant from screen 1 → scenario and learn screens → server route with roleplay-turn.md + local safety check → run evals → plan screen with .ics reminder → wrap-up → Day 2 check-in and practice round on Today.
