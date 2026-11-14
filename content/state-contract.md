# State contract (funnel ↔ app)

Everything the user enters lives in the browser, in one localStorage key. The funnel writes the first part; the app reads it and adds the rest. This file is the agreement between the two.

## Storage

- **Key:** `pcn_state_v1`
- **Format:** one JSON object (shape below).
- **Where:** localStorage only. Never in the URL, never in cookies, never sent to our server.
- **The only exception:** a care card the user chooses to publish (stored on the server under a random id; see "Published care card").
- **Stripe:** receives only the plan id and the amount. No quiz answers, no names.

## Shape

```json
{
  "version": 1,
  "createdAt": "ISO date",
  "updatedAt": "ISO date",

  "quiz": {
    "answers": { "q1_recipient": "mom", "q5_changes": ["repeats", "evenings"], "q10_documents": { "healthcare_proxy": "have" }, "q11_confidence": 2 },
    "tags": ["recipient:mom", "branch:recent"],
    "branch": "noticing | recent | changing",
    "completedAt": "ISO date | null",
    "lastQuestionId": "string (to resume)"
  },

  "recipient": {
    "key": "mom | dad | both | in_law | other",
    "displayName": "Mom (or the name typed in onboarding)",
    "labels": { "recipient": "Mom", "possessive": "Mom's", "pronoun": "she", "object": "her", "was": "was", "is": "is", "has": "has", "lives": "lives" }
  },

  "plan": {
    "builtAt": "ISO date",
    "rulesVersion": 2,
    "intro": "string",
    "whatWeHeard": ["sentence", "sentence"],
    "beforeAfter": { "before": "string", "after": "string" },
    "modules": [
      {
        "id": "m1_talking",
        "title": "Talking with Mom",
        "reason": "string",
        "status": "current | next | later | done",
        "inFirst30Days": true,
        "lessons": [ { "id": "m1_l1", "title": "When Mom asks again", "built": true, "status": "todo | in_progress | done" } ]
      }
    ],
    "quickGuides": [ { "id": "qg_hospital", "title": "After a hospital stay", "highlight": true } ],
    "firstLessonId": "m1_l1",
    "giftPhraseIds": ["p01"]
  },

  "subscription": {
    "status": "none | demo | test_paid",
    "planId": "four_week | twelve_week | null",
    "startedAt": "ISO date | null",
    "renewsAt": "ISO date | null",
    "autoRenewConsentAt": "ISO date | null",
    "canceledAt": "ISO date | null"
  },

  "profile": {
    "enjoys": ["string"],
    "calms": ["string"],
    "avoid": ["string"],
    "rhythm": { "wake": "", "meals": "", "rest": "", "bed": "" },
    "contacts": [ { "label": "string", "phone": "string" } ]
  },

  "confidence": {
    "day0": 2,
    "skills": { "first": { "repeat": 2, "accusations": 1, "evenings": 1, "refusal": 2, "visits": 2 }, "latest": {} }
  },

  "progress": {
    "lessons": { "m1_l1": { "variant": "in_person | phone | both | not_yet", "step": "scenario | learn | practice | plan | done", "startedAt": "ISO", "doneAt": "ISO | null" } },
    "ifThenPlans": [ { "lessonId": "m1_l1", "cue": "string", "response": "string", "reset": "string", "createdAt": "ISO" } ],
    "observations": [ { "text": "string", "at": "ISO", "addToVisitSheet": true } ],
    "scenarios": [ { "lessonId": "string", "scenarioId": "string", "answerId": "string", "verdict": "best | okay | try_again", "at": "ISO" } ],
    "roleplay": [ { "lessonId": "string", "firstScore": 1, "latestScore": 3, "sessions": 2, "at": "ISO" } ],
    "savedPhrases": [ { "id": "string", "text": "string", "source": "scenario | roleplay | gift", "savedAt": "ISO" } ],
    "tasks": [ { "id": "string", "lessonId": "string", "text": "string", "createdAt": "ISO", "doneAt": "ISO | null", "reminderDownloaded": false } ],
    "reflections": [ { "taskId": "string", "answer": "helped | not_yet | didnt_help", "at": "ISO" } ],
    "activeDays": ["YYYY-MM-DD"]
  },

  "careCard": {
    "publishedId": "string | null",
    "publishedAt": "ISO | null",
    "lastPublishedPhraseIds": ["string"],
    "revokedAt": "ISO | null"
  },

  "visitSheet": { "doctor": "", "date": "", "notes": "", "questionIds": ["string"], "customQuestions": ["string"] },

  "demo": { "dayOffset": 0 },

  "events": [ { "name": "string", "at": "ISO", "props": {} } ]
}
```

## Who writes, who reads

| Part | Written by | Read by |
| --- | --- | --- |
| `quiz` | Funnel (after every answer) | Funnel (resume, back button), app (Plan reasons) |
| `recipient` | Funnel (Q1); app onboarding updates `displayName` | Everywhere |
| `plan` | Funnel (planBuilder, after the last question) | Funnel (M3, M4, M5), app (Today, Plan) |
| `subscription` | Funnel (M5: demo button or Stripe return) | App (Settings, cancel flows) |
| `profile` | App (onboarding, lessons, Mom's page) | App, care card |
| `confidence.day0` | Funnel (Q11) | App (Skills) |
| `confidence.skills` | App (end of lesson 1, later checks) | App (Skills) |
| `progress` | App | App (Today, Skills, Reflect) |
| `careCard`, `visitSheet` | App | App |
| `demo.dayOffset` | App ("Simulate next day") | App (all date logic uses `now + dayOffset`) |
| `events` | Funnel and app | Local only (see funnel-events in funnel-qa.md); keep the last 500 |

## Rules

1. **Resume:** if `quiz.completedAt` is null, the funnel reopens at `quiz.lastQuestionId` with answers filled in.
2. **Back button** keeps answers. Changing Q3 after later answers recalculates tags and the branch; the plan is rebuilt only after the last question.
3. **Rebuild the plan** whenever quiz answers change. Keep `progress` as it is.
4. **Paywall gate:** the app opens only if `subscription.status` is `demo` or `test_paid`. Otherwise redirect to M5 (or to the quiz if `plan` is missing).
5. **Auto-renew consent:** `autoRenewConsentAt` must be set before `status` changes, in both demo and test mode.
6. **Dates:** all "today / tomorrow / last night" logic uses `now + demo.dayOffset` days, so "Simulate next day" works everywhere.
7. **Broken or old state:** if JSON can't be parsed or `version` is unknown, keep a copy under `pcn_state_backup` and start fresh (show "We couldn't restore your plan" once).
8. **Clear my data:** remove `pcn_state_v1` and `pcn_state_backup`, unpublish the care card if published, return to the landing page.
9. **Nothing medical** leaves the quiz part: `profile`, the care card and the visit sheet never include Q3 or Q5 answers.
10. **Lesson variants never change the path.** `progress.lessons[id].variant` changes examples and tasks inside a lesson only; the next lesson always comes from the module order.

## Published care card

- On "Publish", the app sends only this to the server: `displayName`, `profile.enjoys`, `profile.calms`, `profile.avoid`, `profile.rhythm`, `profile.contacts`, the saved phrases chosen for the card, the "updated" date and the caregiver's first name if entered.
- The server returns a random id (at least 16 characters). Link: `/card/{id}`.
- "Update" sends the same fields again under the same id. "Revoke" deletes it on the server and sets `revokedAt`.
- The card page never shows a diagnosis, medications or quiz answers.

## Example: state right after the quiz

```json
{
  "version": 1,
  "createdAt": "2026-11-15T03:10:00Z",
  "updatedAt": "2026-11-15T03:14:00Z",
  "quiz": {
    "answers": {
      "q1_recipient": "mom",
      "q2_age": "75_84",
      "q3_situation": "recent",
      "q5_changes": ["repeats", "evenings"],
      "q6_living": "far",
      "q7_helpers": "just_me",
      "q8_work": "full_time",
      "q9_worries": ["what_to_say", "legal_money"],
      "q10_documents": { "healthcare_proxy": "have", "financial_poa": "missing", "hipaa_release": "not_sure" },
      "q11_confidence": 2,
      "q12_time": "10"
    },
    "tags": ["recipient:mom", "age:75_84", "age:65plus", "age:75plus", "branch:recent", "stage:early", "new_diagnosis", "need:repeated_questions", "need:evening_confusion", "living:far", "need:distance", "help:alone", "need:support_team", "work:full_time", "worry:communication", "worry:legal", "need:documents", "confidence:low", "pace:10"],
    "branch": "recent",
    "completedAt": "2026-11-15T03:14:00Z",
    "lastQuestionId": "q12_time"
  },
  "recipient": { "key": "mom", "displayName": "Mom", "labels": { "recipient": "Mom", "possessive": "Mom's", "pronoun": "she", "object": "her", "was": "was", "is": "is", "has": "has", "lives": "lives" } },
  "subscription": { "status": "none", "planId": null, "startedAt": null, "renewsAt": null, "autoRenewConsentAt": null, "canceledAt": null },
  "confidence": { "day0": 2, "skills": { "first": {}, "latest": {} } },
  "demo": { "dayOffset": 0 },
  "events": []
}
```

With these tags, planBuilder should produce (check this in a unit test):

- **What we heard:** "Mom was diagnosed in the last few months. Mom lives far away. You're handling most of it alone, and you work full-time. What worries you most: knowing what to say and legal papers and money."
- **Module order:** 1. Talking with Mom → 2. While she can still decide (reason: key papers missing) → 3. Hard moments (reason: evenings are hard) → 4. Doctors and your care team (reason: Mom lives far away) → 5. Caring for yourself → 6. Safe home, calmer days → later: Getting more help, Later stages.
- **First 30 days:** Modules 1–3.
- **Intro:** the `confidence:low` line.

Two more test cases for unit tests (answers as in funnel-qa.md):

- **A, Noticing (Dad):** 1. Talking with Dad → 2. Before the diagnosis (fixed second for the noticing branch) → 3. Hard moments → 4. While he can still decide → 5. Safe home → 6. Doctors and your care team → 7. Caring for yourself → later modules. All reasons are the module defaults except Module 2.
- **C, Changing (just home from the hospital):** 1. Talking with Mom → 2. Safe home, calmer days (reason: just came home from the hospital) → 3. Hard moments → 4. While she can still decide (ties with Caring for yourself; list order wins) → 5. Caring for yourself → 6. Doctors and your care team → later modules. Highlighted quick guides: After a hospital stay, If Mom goes missing, After a fall, You're at your limit.
