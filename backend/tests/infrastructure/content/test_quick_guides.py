import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.guides.render import render_guide
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.content.schemas import QuickGuidesFile

CONTENT_DIR = Path(__file__).resolve().parents[4] / "content"
PROVIDER = JsonContentProvider.from_directory(CONTENT_DIR)
KEYS = PROVIDER.recipient_keys()


def _raw() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((CONTENT_DIR / "quick-guides.json").read_text())
    return data


def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def test_the_five_guide_ids_and_titles_equal_plan_rules() -> None:
    rules = json.loads((CONTENT_DIR / "plan-rules.json").read_text())["quickGuides"]
    guides = _raw()["guides"]
    assert {g["id"] for g in guides} == {g["id"] for g in rules}
    assert {g["id"]: g["title"] for g in guides} == {g["id"]: g["title"] for g in rules}


def test_every_shared_phone_number_matches_crisis_resources() -> None:
    crisis = json.loads((CONTENT_DIR / "crisis-resources.json").read_text())["resources"]
    known = {_digits(r["phone"]) for r in crisis}
    for res in _raw()["resources"].values():
        assert _digits(res["tel"]) == _digits(res["number"])
        if _digits(res["number"]) in known:
            assert any(
                r["phone"] == res["number"]
                for r in crisis
                if _digits(r["phone"]) == _digits(res["number"])
            )
    # Every guide number is one of the verified crisis numbers.
    assert {_digits(r["number"]) for r in _raw()["resources"].values()} <= known


def test_footer_has_no_medical_advice_sentence() -> None:
    assert _raw()["common"]["footer"] == "In an emergency, call 911."


@pytest.mark.parametrize("key", KEYS)
def test_every_guide_renders_for_every_recipient_key_without_braces(key: str) -> None:
    book = PROVIDER.quick_guides()
    labels = PROVIDER.lesson_recipient_labels(key)
    assert len(book.guides) == 5
    for guide in book.guides:
        r = render_guide(book, guide, labels)
        texts = [
            r.title, r.summary, r.footer, *r.call_now, *r.then, *r.dont,
            *(t for s in r.steps for t in (s.title, s.text)),
        ]  # fmt: skip
        assert texts and r.steps and r.resources
        assert not any("{" in t or "}" in t for t in texts)
        # Subject is always the label, never a bare pronoun: "they is / they talks" reads wrongly
        # for the neutral labels (in_law, other), where the pronoun is plural but the verb is not.
        joined = " ".join(texts)
        assert not re.search(r"\b[Tt]hey (is|was|has|talks|needs|takes|seems|hit|goes)\b", joined)


def _with(mutate: Any) -> dict[str, Any]:
    data = _raw()
    mutate(data)
    return data


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["guides"][1].update(id=d["guides"][0]["id"]),
        lambda d: d["guides"][0].update(urgency="whenever"),
        lambda d: d["guides"][0]["resources"].append("nope"),
        lambda d: d["guides"][0]["steps"].clear(),
        lambda d: d["guides"][0].update(title="If {nickname} goes missing"),
        lambda d: d["guides"][0].update(summary="Call {Object}"),
    ],
    ids=["dup_id", "urgency", "resource", "no_steps", "placeholder", "capital_object"],
)
def test_invalid_guide_files_are_rejected(mutate: Any) -> None:
    with pytest.raises(ValidationError):
        QuickGuidesFile.model_validate(_with(mutate))


def test_the_file_has_a_version_and_notes() -> None:
    assert _raw()["version"] == 1 and _raw()["notes"]
