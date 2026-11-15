# Funnel QA checklist

> **Superseded by TASK.md section 6.2 (server-side session).** This file still describes the old `pcn_state_v1` localStorage design and "nothing sent to our server". The persona tables and rules stay valid as logic reference; the storage description does not.

Run this before every submission, in an incognito window, on a phone and on a laptop, against the production URL.

## 1. Three test personas (one per branch)

Answer the quiz exactly like this and check the result.

| | A: Noticing | B: Recent diagnosis | C: Changing |
| --- | --- | --- | --- |
| Q1 | My dad | My mom | My mom |
| Q2 | 65–74 | 75–84 | 85 or older |
| Q3 | Noticing changes, no diagnosis | Diagnosed in the last 6 months | Just came home from the hospital |
| Q5 | Skip | Repeats questions, evenings | Says no to help, gets lost |
| Q6 | Nearby | Far away | With me |
| Q7 | My brother or sister | Just me | A paid caregiver |
| Q8 | Part-time | Full-time | Not right now |
| Q9 | Not knowing what comes next | Knowing what to say, legal papers and money | Safety at home, my own exhaustion |
| Q10 | All "Have" | Proxy: Have, POA: Missing, HIPAA: Not sure | All "Missing" |
| Q11 | 3 | 2 | 4 |
| Q12 | 5 minutes | 10 minutes | 15 minutes or more |

**Expected**

- **All personas:** the course starts with Module 1 "Talking with Mom/Dad", lesson 1 "When Mom/Dad asks again". Every module shown has a reason.
- **A:** texts say "Dad", "he", "his". Module 2 is "Before the diagnosis". Before/after uses the "noticing" text. Pace line says 3 lessons a week.
- **B:** "What we heard" reads: "Mom was diagnosed in the last few months. Mom lives far away. You're handling most of it alone, and you work full-time. What worries you most: knowing what to say and legal papers and money." Module order: Talking with Mom → While she can still decide → Hard moments → Doctors and your care team → Caring for yourself → Safe home. Intro is the low-confidence line. Gift sheet starts with the repeated-questions and evening phrases.
- **C:** Module 2 is "Safe home, calmer days" with the hospital reason; quick guide "After a hospital stay" shown first. "What we heard" has no work part. Diagnosis and changes never appear in the summary.

Full expected results: see state-contract.md.

## 2. Funnel checks

- [ ] Landing opens fast on a phone; one main button; "No sign-up needed" visible.
- [ ] Quiz shows progress and question count; back keeps answers.
- [ ] Changing Q1 on the way back updates names and pronouns everywhere.
- [ ] Changing Q3 on the way back changes the branch, the before/after text and the plan.
- [ ] Q5 "None of these yet" clears the other choices; max 3 choices on Q5 and Q9.
- [ ] Q3 to Q5 screens (situation, changes) load no trackers; the quiz never asks for a diagnosis.
- [ ] Reassurance cards appear after Q5 and Q9.
- [ ] Refreshing the page mid-quiz resumes at the same question.
- [ ] Loader shows up to 4 lines that match the answers.
- [ ] Plan preview: "What we heard", before/after, modules in order with a reason on each, the first 30 days (Module 1 + next two) in full and the rest as a short map, quick guides, proof with sources, gift download, "Get Mom's plan" button.
- [ ] Gift sheet prints on one US Letter page, works in black and white, has 5 phrases.
- [ ] Paywall: 4-week selected by default; no weekly plan; no price per day.
- [ ] Disclosure above the button shows today's price, renewal price, period and the renewal date.
- [ ] Pay and demo buttons stay blocked until the renewal checkbox is ticked.
- [ ] Stripe test card 4242 4242 4242 4242 completes; a declined test card shows the card error.
- [ ] Canceling at Stripe returns to the paywall with "No payment was made".
- [ ] "Continue in demo mode" sets status `demo` and opens onboarding.
- [ ] "Save your plan" can be skipped.
- [ ] Opening /app directly without a plan sends you to the quiz; with a plan but no subscription, to the paywall.

## 3. Privacy and safety checks

- [ ] No quiz answers in any URL (check the address bar on every step).
- [ ] No ad or analytics scripts on any page (check the browser's network tab).
- [ ] Nothing sent to our server during the quiz, the plan preview or the paywall, except the Stripe checkout request with plan id only.
- [ ] "Need help now?" opens the crisis sheet from every funnel screen after the quiz starts.
- [ ] API keys are not in the repo or in the page source.

## 4. Accessibility checks

- [ ] Every screen works with the keyboard only; focus ring visible.
- [ ] Tap targets at least 48 × 48 px.
- [ ] Text contrast at least 4.5:1.
- [ ] Screen-reader labels on options, chips and the progress bar.
- [ ] Page still works at 200% zoom.

## 5. Local events (no trackers)

Events are saved only in the browser (`events` in the state, last 500). They exist so the team can check the funnel on test devices and show the metrics plan in the pitch.

| Event | When | Props |
| --- | --- | --- |
| `landing_view` | Landing opens | `source` (utm_source only, if present) |
| `quiz_start` | First question shown | — |
| `quiz_answer` | Each answer saved | `questionId` (never the answer for Q3–Q5) |
| `quiz_back` | Back pressed | `questionId` |
| `quiz_complete` | Last answer saved | `branch` |
| `plan_built` | planBuilder finished | `itemsCount`, `rulesVersion` |
| `plan_preview_view` | Plan preview shown | — |
| `gift_download` | Gift sheet downloaded or printed | — |
| `paywall_view` | Paywall shown | `defaultPlanId` |
| `plan_selected` | Plan changed | `planId` |
| `consent_checked` | Renewal checkbox ticked | — |
| `checkout_start` | Stripe checkout opened | `planId` |
| `checkout_success` | Returned from Stripe, paid | `planId` |
| `checkout_canceled` | Returned from Stripe, not paid | `planId` |
| `demo_mode` | Demo button used | — |
| `save_plan` | Email saved or skipped | `skipped` (true/false) |
| `lesson_start` | First lesson opens | `lessonId` |
