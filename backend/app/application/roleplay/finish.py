"""`FinishRoleplay`: close the run and return the summary. Skills progress reads the stored run."""

import logging
from collections.abc import Sequence
from uuid import UUID

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.roleplay.dto import FinishView, TurnPhrase
from app.application.roleplay.lesson_source import render, roleplay_screen
from app.application.roleplay.runs import load_run, save_run
from app.domain.roleplay.errors import TurnsMismatch
from app.domain.roleplay.run import RunContext, RunRecord, TurnPhrases, best_phrase, validate_reply
from app.domain.session.entities import Session

logger = logging.getLogger(__name__)


class FinishRoleplay:
    """Scores and goals come from the stored run. The reply and better phrase of each turn are
    sent back by the client (we never stored them), one per scored turn, only to pick the best
    phrase; they are returned, never persisted or logged."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock

    async def execute(
        self, session: Session, run_id: UUID, phrases: Sequence[TurnPhrase] = ()
    ) -> FinishView:
        record = await load_run(self._uow, session, run_id)
        scores = tuple(record.run.turn_scores)
        if len(phrases) != len(scores):
            raise TurnsMismatch(len(scores), len(phrases))
        turns = [
            TurnPhrases(score, validate_reply(p.reply), p.better_phrase.strip())
            for score, p in zip(scores, phrases, strict=True)
        ]
        if record.finished_at is None:
            record.finished_at = session.app_now(self._clock.now())
            await save_run(self._uow, record)
        summary = record.run.summary()
        logger.info("roleplay finish run=%s turns=%s", record.id, len(scores))
        return FinishView(
            run_id=record.id,
            mode=record.run.mode,
            finished_at=record.finished_at,
            summary=summary,
            scores=scores,
            first_vs_last=self._first_vs_last(session, record),
            best_phrase=best_phrase(turns),
        )

    def _first_vs_last(self, session: Session, record: RunRecord) -> str | None:
        """The lesson's `summary.firstVsLast`, filled here (lesson context, at least one score)."""
        summary = record.run.summary()
        if record.context is not RunContext.LESSON or summary.first_score is None:
            return None
        lesson = render(
            self._content,
            session,
            record.lesson_id,
            record.variant,
            {"firstScore": str(summary.first_score), "lastScore": str(summary.last_score)},
        )
        text: str = roleplay_screen(lesson)["summary"]["firstVsLast"]
        return text
