import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch, small_pool, small_questions):
    # point the app at a temp DB and the fixture pool before importing
    import app.config as config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    import app.main as main_mod
    monkeypatch.setattr(
        main_mod, "ENTITY_SERVICE",
        main_mod.EntityService(small_pool, small_questions), raising=False,
    )
    main_mod.GAME_SERVICE = main_mod.GameService(main_mod.ENTITY_SERVICE)
    main_mod.SESSIONS.clear()
    main_mod.db.init_db(config.DB_PATH)
    return TestClient(main_mod.app)


def test_start_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "アキネーター" in r.text


def test_full_game_flow_to_guess(client):
    # start a game
    r = client.post("/game/new", follow_redirects=False)
    assert r.status_code in (302, 303)
    location = r.headers["location"]
    game_id = int(location.rstrip("/").split("/")[-1].split("?")[0]) if location[-1].isdigit() else None
    # walk: fetch question page, answer 'yes' repeatedly until guess
    gid = location.split("/")[2]
    for _ in range(25):
        page = client.get(f"/game/{gid}")
        if "推測" in page.text or page.url.path.endswith("/guess"):
            break
        r = client.post(f"/game/{gid}/answer", data={"answer": "yes"},
                        follow_redirects=True)
        assert r.status_code == 200
    guess = client.get(f"/game/{gid}/guess")
    assert guess.status_code == 200


def test_debug_page_shows_candidates(client):
    r = client.post("/game/new", follow_redirects=True)
    gid = r.url.path.split("/")[2]
    dbg = client.get(f"/debug/{gid}")
    assert dbg.status_code == 200
    # shows at least one candidate id from the fixture
    assert any(name in dbg.text for name in ["アクターA", "シンガーB", "悟空", "セーラーD"])
