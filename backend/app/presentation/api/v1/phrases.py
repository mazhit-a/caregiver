"""Saved phrase routes (behind the access gate)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.application.phrases.use_cases import DeletePhrase, ListPhrases, SavePhrase
from app.application.ports import Clock, IdGenerator, UnitOfWork
from app.domain.phrases.entities import SavedPhrase
from app.presentation.api.deps import SubscribedSession, get_clock, get_id_generator, get_uow
from app.presentation.api.schemas.phrases import PhraseOut, PhrasesResponse, SavePhraseRequest

router = APIRouter(tags=["phrases"])


def _save(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SavePhrase:
    return SavePhrase(uow, ids, clock)


def _list(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> ListPhrases:
    return ListPhrases(uow)


def _delete(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> DeletePhrase:
    return DeletePhrase(uow)


def _out(phrase: SavedPhrase) -> PhraseOut:
    return PhraseOut(
        id=phrase.id,
        text=phrase.text,
        source=phrase.source,
        lesson_id=phrase.lesson_id,
        saved_at=phrase.saved_at,
    )


@router.get("/phrases", response_model=PhrasesResponse)
async def list_phrases(
    session: SubscribedSession, use_case: Annotated[ListPhrases, Depends(_list)]
) -> PhrasesResponse:
    return PhrasesResponse(phrases=[_out(p) for p in await use_case.execute(session)])


@router.post("/phrases", response_model=PhraseOut, status_code=status.HTTP_201_CREATED)
async def save_phrase(
    body: SavePhraseRequest,
    session: SubscribedSession,
    use_case: Annotated[SavePhrase, Depends(_save)],
) -> PhraseOut:
    return _out(await use_case.execute(session, body.text, body.source, body.lesson_id))


@router.delete("/phrases/{phrase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phrase(
    phrase_id: UUID,
    session: SubscribedSession,
    use_case: Annotated[DeletePhrase, Depends(_delete)],
) -> Response:
    await use_case.execute(session, phrase_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
