import httpx
from fastapi import FastAPI


async def test_crisis_resources_public_camel_case(app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        r = await client.get("/api/resources/crisis")  # no session header
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"resources", "verifyBeforeLaunch"}
    assert body["verifyBeforeLaunch"] is True
    assert {x["phone"] for x in body["resources"]} >= {"911", "988"}
    assert set(body["resources"][0]) == {"id", "name", "phone", "description"}
