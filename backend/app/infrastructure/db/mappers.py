"""ORM row <-> domain entity mapping."""

from app.domain.quiz.entities import QuizState
from app.domain.session.entities import Session
from app.infrastructure.db.orm_models import QuizStateRow, SessionRow


def session_to_domain(row: SessionRow) -> Session:
    return Session(
        id=row.id,
        token_hash=row.token_hash,
        timezone=row.timezone,
        clock_offset=row.clock_offset,
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
        recipient_key=row.recipient_key,
        display_name=row.display_name,
    )


def session_to_row(session: Session) -> SessionRow:
    return SessionRow(
        id=session.id,
        token_hash=session.token_hash,
        timezone=session.timezone,
        clock_offset=session.clock_offset,
        created_at=session.created_at,
        last_seen_at=session.last_seen_at,
        recipient_key=session.recipient_key,
        display_name=session.display_name,
    )


def quiz_state_to_domain(row: QuizStateRow) -> QuizState:
    return QuizState(
        session_id=row.session_id,
        answers=dict(row.answers),
        tags=list(row.tags),
        branch=row.branch,
        last_question_id=row.last_question_id,
        completed_at=row.completed_at,
        locked=row.locked,
        health_answers_purged_at=row.health_answers_purged_at,
    )
