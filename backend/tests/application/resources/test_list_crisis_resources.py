from pathlib import Path

from app.application.resources.list_crisis_resources import ListCrisisResources
from app.infrastructure.content.provider import JsonContentProvider

REAL_CONTENT = Path(__file__).resolve().parents[4] / "content"


def test_list_crisis_resources_returns_all_four_in_order() -> None:
    use_case = ListCrisisResources(JsonContentProvider.from_directory(REAL_CONTENT))
    result = use_case.execute()
    assert [r.id for r in result.resources] == [
        "emergency_911",
        "lifeline_988",
        "alz_helpline",
        "adult_protective_services",
    ]
    assert result.verify_before_launch is True
