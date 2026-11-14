from datetime import timedelta

import httpx
from fastapi import FastAPI

from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401


async def _put(client: httpx.AsyncClient, step: int, lesson_id: str = "m1_l1") -> httpx.Response:
    return await client.put(f"/api/lessons/{lesson_id}/progress", json={"step": step})


async def test_progress_requires_the_gate_and_a_token(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    assert (await _put(pclient, 0)).status_code == 402
    await subscribe(pclient)
    bare = await pclient.put(
        "/api/lessons/m1_l1/progress", json={"step": 0}, headers={"X-Session-Token": "nope"}
    )
    assert bare.status_code == 401


async def test_stored_step_comes_back_on_the_next_lesson_read(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    r = await _put(pclient, 3)
    assert r.status_code == 200, r.text
    assert r.json()["step"] == 3 and r.json()["doneAt"] is None
    body = (await pclient.get("/api/lessons/m1_l1")).json()
    assert body["progress"]["step"] == 3
    assert body["variant"] == "phone"  # saving the step keeps the variant


async def test_step_can_move_back_while_the_lesson_is_not_done(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    await _put(pclient, 5)
    assert (await _put(pclient, 2)).json()["step"] == 2


async def test_out_of_range_step_is_422(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    screens = len((await pclient.get("/api/lessons/m1_l1")).json()["screens"])
    r = await _put(pclient, screens)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_lesson_step"
    assert (await _put(pclient, -1)).status_code == 422
    assert (await _put(pclient, screens - 1)).status_code == 200


async def test_before_the_variant_only_the_setup_screen_exists(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    assert (await _put(pclient, 0)).status_code == 200
    r = await _put(pclient, 1)
    assert r.status_code == 422 and r.json()["error"]["details"]["screenCount"] == 1


async def test_locked_lesson_is_423(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await _put(pclient, 0, lesson_id="m1_l2")
    assert r.status_code == 423 and r.json()["error"]["code"] == "lesson_locked"


async def test_unknown_lesson_is_404(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    assert (await _put(pclient, 0, lesson_id="nope")).status_code == 404


async def test_negative_or_missing_step_is_a_validation_error(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    assert (await pclient.put("/api/lessons/m1_l1/progress", json={})).status_code == 422


async def test_done_lesson_keeps_its_step(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    await _put(pclient, 6)
    done = await pclient.post("/api/lessons/m1_l1/complete")
    assert done.status_code == 200, done.text
    r = await _put(pclient, 1)
    assert r.status_code == 200 and r.json()["step"] == 6 and r.json()["doneAt"] is not None
    assert (await pclient.get("/api/lessons/m1_l1")).json()["progress"]["step"] == 6
    assert (await _put(pclient, 99)).status_code == 422  # range is still validated
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=1))
    assert (await pclient.get("/api/lessons/m1_l1")).json()["progress"]["step"] == 6
