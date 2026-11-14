"""PlanBuilder: pure function following plan-rules.json algorithm steps 1-9."""

from collections.abc import Sequence

from app.domain.plan.entities import (
    BeforeAfterRule,
    BoostRule,
    BuiltPlan,
    HeardFragment,
    HeardSentenceRule,
    LoaderLineRule,
    ModuleRule,
    ModuleStatus,
    Pace,
    PlanLesson,
    PlanModule,
    PlanQuickGuide,
    PlanRules,
    Readiness,
)
from app.domain.shared.errors import DomainError
from app.domain.shared.labels import RecipientLabels, render_text

_FIRST_30_DAYS_MODULES = 3
_MAX_MATCHING_LOADER_LINES = 2
_MAX_GIFT_PHRASES_PER_TAG = 2
_GENERAL_TAG = "general"
_DEFAULT_KEY = "default"


class PlanRulesError(DomainError):
    """The rules cannot produce a valid plan (e.g. a module without a reason)."""

    code = "plan_rules_invalid"


class PlanBuilder:
    """Builds a personal plan from quiz tags and the rules. No I/O, no clock, no randomness."""

    @staticmethod
    def build(
        tags: Sequence[str],
        branch: str,
        labels: RecipientLabels,
        q5_order: Sequence[str],
        rules: PlanRules,
        heard: Sequence[HeardFragment] = (),
    ) -> BuiltPlan:
        """Build the plan.

        `q5_order` is the tags of the Q5 answers in the order chosen (used only for gift
        phrases); `heard` is the "What we heard" fragments in answer order (never Q5).
        """
        tag_set = frozenset(tags)
        modules = tuple(
            _plan_module(module, reason, index, labels)
            for index, (module, reason) in enumerate(_ordered_modules(tag_set, branch, rules))
        )
        first_30 = modules[:_FIRST_30_DAYS_MODULES]
        return BuiltPlan(
            rules_version=rules.version,
            plan_intro=_plan_intro(tag_set, rules, labels),
            what_we_heard=_what_we_heard(heard, rules.heard_sentences, labels),
            before_after=_before_after(branch, rules, labels),
            modules=modules,
            first_30_days=tuple(m.id for m in first_30),
            first_lesson_id=rules.first_lesson_id,
            quick_guides=_quick_guides(tag_set, rules, labels),
            loader_lines=_loader_lines(tag_set, rules.loader_lines, labels),
            pace=_pace(tag_set, rules, labels),
            readiness=Readiness(
                modules_total=len(first_30),
                lessons_total=sum(len(m.lessons) for m in first_30),
            ),
            gift_phrase_ids=_gift_phrase_ids(q5_order, rules),
        )


# ---------------------------------------------------------------- modules (steps 1-7, 9)


def _boost_matches(boost: BoostRule, tags: frozenset[str]) -> bool:
    if not all(tag in tags for tag in boost.all):
        return False
    if boost.any is not None and not any(tag in tags for tag in boost.any):
        return False
    return not any(tag in tags for tag in boost.none or ())


def _ordered_modules(
    tags: frozenset[str], branch: str, rules: PlanRules
) -> list[tuple[ModuleRule, str]]:
    """Modules in plan order with their (unrendered) reasons."""
    by_id = {m.id: m for m in rules.modules}
    first_reason = rules.first_module_reason_by_branch.get(branch)
    if first_reason is None or rules.first_module_id not in by_id:
        raise PlanRulesError("No first module or reason for the branch", {"branch": branch})
    result = [(by_id[rules.first_module_id], first_reason)]
    if branch == "noticing":
        result.extend((m, m.reason or "") for m in rules.modules if m.order == "noticing_second")
    result.extend(_scored_modules(tags, rules))
    result.extend((m, m.reason or "") for m in rules.modules if m.order == "later")
    for module, reason in result:
        if not reason.strip():
            raise PlanRulesError(f"Module '{module.id}' has no reason", {"module": module.id})
    return result


def _scored_modules(tags: frozenset[str], rules: PlanRules) -> list[tuple[ModuleRule, str]]:
    scored = [m for m in rules.modules if m.order == "scored"]
    score = {m.id: m.base_score or 0 for m in scored}
    reason = {m.id: m.reason or "" for m in scored}
    best_points: dict[str, int] = {}
    for boost in rules.boosts:
        if boost.module not in score or not _boost_matches(boost, tags):
            continue
        score[boost.module] += boost.points
        if boost.module not in best_points or boost.points > best_points[boost.module]:
            best_points[boost.module] = boost.points
            reason[boost.module] = boost.reason
    ranked = sorted(scored, key=lambda m: -score[m.id])  # stable: ties keep list order
    return [(m, reason[m.id]) for m in ranked]


def _plan_module(
    module: ModuleRule, reason: str, index: int, labels: RecipientLabels
) -> PlanModule:
    status: ModuleStatus = "next"
    if module.order == "later":
        status = "later"
    elif index == 0:
        status = "current"
    return PlanModule(
        id=module.id,
        title=render_text(module.title, labels),
        reason=render_text(reason, labels),
        status=status,
        in_first_30_days=index < _FIRST_30_DAYS_MODULES,
        lessons=tuple(
            PlanLesson(lsn.id, render_text(lsn.title, labels), lsn.minutes, lsn.built)
            for lsn in module.lessons
        ),
    )


# ---------------------------------------------------------------- texts


def _plan_intro(tags: frozenset[str], rules: PlanRules, labels: RecipientLabels) -> str:
    for key, text in rules.plan_intro.items():
        if key != _DEFAULT_KEY and key in tags:
            return render_text(text, labels)
    return render_text(rules.plan_intro[_DEFAULT_KEY], labels)


def _before_after(branch: str, rules: PlanRules, labels: RecipientLabels) -> BeforeAfterRule:
    if branch not in rules.before_after:
        raise PlanRulesError(f"No before/after text for branch '{branch}'", {"branch": branch})
    text = rules.before_after[branch]
    return BeforeAfterRule(render_text(text.before, labels), render_text(text.after, labels))


def _join_list(items: Sequence[str], sep: str, last_sep: str) -> str:
    if len(items) <= 1:
        return "".join(items)
    return sep.join(items[:-1]) + last_sep + items[-1]


def _heard_sentence(
    rule: HeardSentenceRule, heard: Sequence[HeardFragment], labels: RecipientLabels
) -> str | None:
    parts: list[str] = []
    for slot in rule.slots:
        texts = [render_text(f.text, labels) for f in heard if f.slot == slot]
        if texts:
            sep = rule.list_join or ", "
            parts.append(_join_list(texts, sep, rule.last_join or sep))
    if not parts:  # skip a sentence when none of its slots has an answer
        return None
    return (rule.prefix or "") + (rule.join or " ").join(parts) + (rule.end or "")


def _what_we_heard(
    heard: Sequence[HeardFragment], sentences: Sequence[HeardSentenceRule], labels: RecipientLabels
) -> tuple[str, ...]:
    built = (_heard_sentence(rule, heard, labels) for rule in sentences)
    return tuple(s for s in built if s is not None)


# ---------------------------------------------------------------- quick guides, loader, pace


def _quick_guides(
    tags: frozenset[str], rules: PlanRules, labels: RecipientLabels
) -> tuple[PlanQuickGuide, ...]:
    guides = [
        PlanQuickGuide(g.id, render_text(g.title, labels), any(t in tags for t in g.highlight_if))
        for g in rules.quick_guides
    ]
    # Highlighted first ("For now"), each group in list order.
    return tuple([g for g in guides if g.highlight] + [g for g in guides if not g.highlight])


def _loader_lines(
    tags: frozenset[str], lines: Sequence[LoaderLineRule], labels: RecipientLabels
) -> tuple[str, ...]:
    always = [line for line in lines if line.always]
    matching = [
        line
        for line in lines
        if not line.always and line.any is not None and any(t in tags for t in line.any)
    ]
    chosen = always[:1] + matching[:_MAX_MATCHING_LOADER_LINES] + always[1:][-1:]
    return tuple(render_text(line.text, labels) for line in chosen)


def _pace(tags: frozenset[str], rules: PlanRules, labels: RecipientLabels) -> Pace:
    per_week = rules.pace.lessons_per_week
    keys = [key for key in per_week if key != _DEFAULT_KEY]
    chosen = next((key for key in keys if key in tags), None)
    if chosen is None:  # no pace answer: use the key that matches the default
        chosen = next((k for k in keys if per_week[k] == per_week[_DEFAULT_KEY]), keys[0])
    lessons = per_week[chosen] if chosen in tags else per_week[_DEFAULT_KEY]
    minutes = int(chosen.split(":", 1)[1])
    label = render_text(
        rules.pace.label, labels, {"minutes": str(minutes), "perWeek": str(lessons)}
    )
    return Pace(lessons_per_week=lessons, minutes_per_lesson=minutes, label=label)


# ---------------------------------------------------------------- gift phrases


def _gift_phrase_ids(q5_order: Sequence[str], rules: PlanRules) -> tuple[str, ...]:
    """Q5-matched phrases first (Q5 order, max 2 per tag), then `general`, up to the count."""
    chosen: list[str] = []

    def add(phrase_id: str) -> None:
        if phrase_id not in chosen and len(chosen) < rules.gift_phrase_count:
            chosen.append(phrase_id)

    for tag in q5_order:
        matched = [p.id for p in rules.phrases if tag in p.tags and p.id not in chosen]
        for phrase_id in matched[:_MAX_GIFT_PHRASES_PER_TAG]:
            add(phrase_id)
    for phrase in rules.phrases:
        if _GENERAL_TAG in phrase.tags:
            add(phrase.id)
    for phrase in rules.phrases:  # content has too few `general` phrases: fill in list order
        add(phrase.id)
    return tuple(chosen)
