from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from app.domain.care_card.entities import SNAPSHOT_KEYS, CardSnapshot, CareCard, build_snapshot
from app.domain.care_card.policies import card_status, new_phrase_count
from app.domain.phrases.entities import SavedPhrase
from app.domain.profile.entities import Contact, Profile
from app.domain.safety.resources import CrisisResource

T0 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
SID = uuid4()
HELP = [CrisisResource("h1", "Helpline", "988", "Call any time.")]


def profile(updated_at: datetime = T0) -> Profile:
    return Profile.create(
        SID, ["songs"], ["tea"], ["crowds"], "Up at 7", [Contact("Sam", "555 123 4567")], "Alex",
        updated_at,
    )  # fmt: skip


def snapshot(p: Profile | None = None) -> CardSnapshot:
    return build_snapshot("Mom", p or profile(), HELP, ["I'm here."], date(2026, 1, 5))


def card(at: datetime = T0, phrase_ids: tuple[UUID, ...] = ()) -> CareCard:
    return CareCard.publish("t" * 43, SID, snapshot(), phrase_ids, at)


def phrase(saved_at: datetime = T0, id: UUID | None = None) -> SavedPhrase:
    return SavedPhrase(id or uuid4(), SID, "x", "scenario", None, saved_at)


def test_snapshot_contains_only_whitelisted_keys() -> None:
    assert set(snapshot().to_json()) == SNAPSHOT_KEYS
    assert set(build_snapshot("Mom", None, [], [], date(2026, 1, 5)).to_json()) == SNAPSHOT_KEYS


def test_snapshot_never_contains_quiz_answers_diagnosis_or_medications() -> None:
    """Extra data in the stored JSON or a profile never reaches the public shape."""
    stored = snapshot().to_json() | {
        "diagnosis": "DIAG-SECRET",
        "medications": ["MED-SECRET"],
        "quizAnswers": {"q3": "QUIZ-SECRET"},
        "visitSheet": "VISIT-SECRET",
    }
    rebuilt = CardSnapshot.from_json(stored).to_json()
    assert set(rebuilt) == SNAPSHOT_KEYS
    assert "SECRET" not in repr(rebuilt)


def test_snapshot_round_trips_through_json() -> None:
    s = snapshot()
    assert CardSnapshot.from_json(s.to_json()) == s


def test_revoke_makes_a_tombstone_without_data() -> None:
    revoked = card(phrase_ids=(uuid4(),)).revoke(T0 + timedelta(days=1))
    assert revoked.is_revoked and revoked.snapshot is None and revoked.phrase_ids == ()
    assert revoked.id == "t" * 43 and revoked.session_id == SID


def test_status_not_published_published_revoked() -> None:
    assert card_status(None, None, []) == "not_published"
    assert card_status(card(), profile(), []) == "published"
    assert card_status(card().revoke(T0), profile(), []) == "revoked"


def test_status_update_available_when_profile_saved_after_publishing() -> None:
    assert card_status(card(), profile(T0 + timedelta(seconds=1)), []) == "update_available"
    assert card_status(card(), profile(T0), []) == "published"  # equal is not newer
    assert card_status(card(), None, []) == "published"


def test_status_update_available_when_a_chosen_phrase_was_deleted() -> None:
    chosen = phrase()
    c = card(phrase_ids=(chosen.id,))
    assert card_status(c, None, [chosen]) == "published"
    assert card_status(c, None, []) == "update_available"


def test_new_phrases_count_only_unchosen_phrases_saved_after_publishing() -> None:
    chosen = phrase(T0 - timedelta(days=1))
    c = card(phrase_ids=(chosen.id,))
    older_unchosen = phrase(T0 - timedelta(days=1))
    newer = [phrase(T0 + timedelta(hours=1)), phrase(T0 + timedelta(hours=2))]
    assert new_phrase_count(c, [chosen, older_unchosen, *newer]) == 2
    assert card_status(c, None, [chosen, older_unchosen, *newer]) == "published"
    assert new_phrase_count(None, newer) == 0 and new_phrase_count(c.revoke(T0), newer) == 0
