"""Maps the validated content models to the plain domain rules used by the plan builder."""

from app.domain.plan.entities import (
    BeforeAfterRule,
    BoostRule,
    HeardSentenceRule,
    LessonRule,
    LoaderLineRule,
    ModuleRule,
    PaceRules,
    PhraseRule,
    PlanRules,
    QuickGuideRule,
)
from app.infrastructure.content.schemas import PhrasesFile, PlanRulesFile


def to_plan_rules(rules: PlanRulesFile, phrases: PhrasesFile) -> PlanRules:
    return PlanRules(
        version=rules.version,
        first_module_id=rules.first_module.id,
        first_module_reason_by_branch=dict(rules.first_module.reason_by_branch),
        first_lesson_id=rules.first_lesson_id,
        modules=tuple(
            ModuleRule(
                id=m.id,
                title=m.title,
                order=m.order,
                reason=m.reason,
                base_score=m.base_score,
                lessons=tuple(LessonRule(x.id, x.title, x.minutes, x.built) for x in m.lessons),
                skill=m.skill,
            )
            for m in rules.modules
        ),
        boosts=tuple(
            BoostRule(
                module=b.module,
                points=b.points,
                reason=b.reason,
                all=tuple(b.all),
                any=None if b.any is None else tuple(b.any),
                none=None if b.none is None else tuple(b.none),
            )
            for b in rules.boosts
        ),
        quick_guides=tuple(
            QuickGuideRule(g.id, g.title, tuple(g.highlight_if)) for g in rules.quick_guides
        ),
        pace=PaceRules(
            dict(rules.pace.lessons_per_week),
            rules.pace.label,
            rules.pace.unlock_rule.days_per_week,
            rules.pace.unlock_rule.first_lesson_offset_days,
        ),
        plan_intro=dict(rules.plan_intro),
        heard_sentences=tuple(
            HeardSentenceRule(
                slots=tuple(s.slots),
                prefix=s.prefix,
                join=s.join,
                list_join=s.list_join,
                last_join=s.last_join,
                end=s.end,
            )
            for s in rules.what_we_heard.sentences
        ),
        before_after={k: BeforeAfterRule(v.before, v.after) for k, v in rules.before_after.items()},
        loader_lines=tuple(
            LoaderLineRule(
                text=line.text,
                always=bool(line.always),
                any=None if line.any is None else tuple(line.any),
            )
            for line in rules.loader_lines
        ),
        phrases=tuple(PhraseRule(p.id, tuple(p.tags)) for p in phrases.phrases),
        gift_phrase_count=rules.gift_phrases.count,
        skills=dict(rules.skills),
    )
