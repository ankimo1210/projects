"""E2E acceptance check for the Quokka Wilds MVP.

Run via the webapp-testing helper (manages the vite dev server):
    python <skill>/scripts/with_server.py --server "npm run dev" --port 5173 \
        -- python e2e/verify_mvp.py

Checks (in order):
 1. page loads, R3F canvas renders, no console errors
 2. WASD keyboard input moves the player
 3. walking into a grass zone triggers a proximity encounter (battle UI opens)
 4. battle can end in win / flee / recruit via the real buttons
 5. recruited creature shows up in the collection book
 6. reloading the page keeps the save (localStorage)
"""

import sys
import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:5173"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def player_pos(page):
    return page.evaluate(
        "() => { const p = window.__qw.playerPosition; return {x: p.x, y: p.y, z: p.z}; }"
    )


def game_mode(page):
    return page.evaluate("() => window.__qw.store.getState().mode")


def nearest_spawn(page):
    return page.evaluate(
        """() => {
          const st = window.__qw.store.getState();
          const p = window.__qw.playerPosition;
          let best = null, bestD = Infinity;
          for (const s of st.wildSpawns) {
            const d = Math.hypot(s.x - p.x, s.z - p.z);
            if (d < bestD) { bestD = d; best = s; }
          }
          return best;
        }"""
    )


def walk_towards(page, tx, tz, timeout_s=40):
    """Hold WASD keys toward (tx, tz) until an encounter starts or we arrive.
    Sidesteps when stuck on an obstacle (tree / rock collider)."""
    held: set[str] = set()

    def release_all():
        for k in list(held):
            page.keyboard.up(k)
            held.discard(k)

    def hold(want):
        for k in held - want:
            page.keyboard.up(k)
        for k in want - held:
            page.keyboard.down(k)
        held.clear()
        held.update(want)

    last = player_pos(page)
    stuck_since = None
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if game_mode(page) == "battle":
            release_all()
            return True
        pos = player_pos(page)
        dx = tx - pos["x"]
        dz = tz - pos["z"]
        if abs(dx) < 1.0 and abs(dz) < 1.0:
            release_all()
            return False

        moved = abs(pos["x"] - last["x"]) + abs(pos["z"] - last["z"])
        last = pos
        if moved < 0.1:
            stuck_since = stuck_since or time.time()
        else:
            stuck_since = None
        if stuck_since and time.time() - stuck_since > 0.5:
            # blocked: sidestep perpendicular to the goal direction
            sidestep = {"a", "w"} if abs(dx) > abs(dz) else {"d", "s"}
            hold(sidestep)
            page.wait_for_timeout(600)
            stuck_since = None
            continue

        want = set()
        if dz < -0.6:
            want.add("w")
        if dz > 0.6:
            want.add("s")
        if dx < -0.6:
            want.add("a")
        if dx > 0.6:
            want.add("d")
        hold(want)
        page.wait_for_timeout(150)
    release_all()
    return game_mode(page) == "battle"


def battle_until_over(page, prefer="attack", max_turns=40):
    """Click real battle buttons until the battle ends; returns the outcome.
    Buttons are disabled while the turn animation plays — playwright's click
    auto-waits for them to re-enable."""
    for _ in range(max_turns):
        outcome = page.evaluate("() => window.__qw.store.getState().battle?.outcome")
        if outcome is None:
            return "closed"
        if outcome != "ongoing":
            return outcome
        if prefer == "link":
            wild = page.evaluate("() => window.__qw.store.getState().battle.wild")
            if wild["hp"] > wild["maxHp"] * 0.45:
                page.locator("button").first.click(timeout=15000)  # weaken first
            else:
                page.get_by_role("button", name="Friend Link").click(timeout=15000)
        elif prefer == "flee":
            page.get_by_role("button", name="Run").click(timeout=15000)
        else:
            page.locator("button").first.click(timeout=15000)
        page.wait_for_timeout(150)
    return "timeout"


def close_battle(page):
    # the Continue button appears once the turn's animation finishes
    button = page.get_by_role("button", name="Continue")
    try:
        button.wait_for(state="visible", timeout=12000)
        button.click()
    except Exception:
        pass
    page.wait_for_timeout(300)


def start_encounter_via_store(page):
    """Start a battle through the real store action (used after the first
    proximity-triggered encounter has already proven the proximity path)."""
    page.evaluate(
        """() => {
          const st = window.__qw.store.getState();
          st.startEncounter(st.wildSpawns[0].key);
        }"""
    )
    page.wait_for_timeout(200)


def wait_ready(page, timeout_ms=90_000):
    """Wait until the canvas exists and the game store is reachable.
    (networkidle is unreliable against the vite dev server)"""
    page.wait_for_selector("canvas", timeout=timeout_ms)
    page.wait_for_function("() => !!window.__qw", timeout=timeout_ms)
    page.wait_for_timeout(2500)  # rapier WASM + first physics frames


def main() -> int:
    console_errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
        )

        # -- 1. load --------------------------------------------------------
        page.goto(URL)
        wait_ready(page)
        canvas = page.locator("canvas")
        check("page loads with canvas", canvas.count() == 1)
        box = canvas.bounding_box()
        check("canvas has size", bool(box and box["width"] > 300 and box["height"] > 300))
        has_handle = page.evaluate("() => !!window.__qw")
        check("debug handle exposed", has_handle)
        spawns = page.evaluate("() => window.__qw.store.getState().wildSpawns.length")
        check("at least 5 wild creatures spawned", spawns >= 5, f"{spawns} spawns")
        page.screenshot(path="/tmp/qw_field.png")

        # -- 2. movement ----------------------------------------------------
        before = player_pos(page)
        page.keyboard.down("w")
        page.wait_for_timeout(900)
        page.keyboard.up("w")
        page.wait_for_timeout(200)
        after = player_pos(page)
        moved = abs(after["z"] - before["z"]) > 1.0
        check("WASD moves the player", moved, f"dz={after['z'] - before['z']:.2f}")

        # -- 3. proximity encounter ----------------------------------------
        entered = False
        for _ in range(3):
            spawn = nearest_spawn(page)
            entered = walk_towards(page, spawn["x"], spawn["z"])
            if entered:
                break
        check("proximity encounter opens battle", entered and game_mode(page) == "battle")
        try:
            # the intro line is typed out character by character
            page.get_by_text("A wild").first.wait_for(timeout=8000)
            battle_visible = True
        except Exception:
            battle_visible = False
        check("battle UI visible", battle_visible)
        page.wait_for_timeout(1200)  # let the intro transition finish
        page.screenshot(path="/tmp/qw_battle.png")

        # -- 4a. flee -------------------------------------------------------
        outcome = battle_until_over(page, prefer="flee")
        check("battle can end by running", outcome == "fled", f"outcome={outcome}")
        close_battle(page)

        # -- 4b. win --------------------------------------------------------
        start_encounter_via_store(page)
        outcome = battle_until_over(page, prefer="attack")
        check("battle can end in win/lose", outcome in ("win", "lose"), f"outcome={outcome}")
        close_battle(page)

        # -- 4c. recruit (retry a few encounters; link can fail) ------------
        recruited_species = None
        for _ in range(6):
            start_encounter_via_store(page)
            wild_id = page.evaluate(
                "() => window.__qw.store.getState().battle.wild.speciesId"
            )
            outcome = battle_until_over(page, prefer="link")
            close_battle(page)
            if outcome == "recruited":
                recruited_species = wild_id
                break
        check(
            "battle can end in recruit (Friend Link)",
            recruited_species is not None,
            f"recruited={recruited_species}",
        )
        party = page.evaluate(
            """() => window.__qw.store.getState().party.map(
                  (m) => `${m.speciesId} Lv.${m.level} ${m.hp}hp`)"""
        )
        check("recruit adds a party member", len(party) >= 2, "; ".join(party))
        starter_xp = page.evaluate(
            "() => window.__qw.store.getState().party[0].xp + window.__qw.store.getState().party[0].level"
        )
        check("fighter gained xp/levels from battles", starter_xp > 5, f"xp+level={starter_xp}")

        # -- 5. collection book ---------------------------------------------
        page.keyboard.press("c")
        page.wait_for_timeout(300)
        book_open = page.get_by_text("Collection Book").count() > 0
        check("collection book opens with C", book_open)
        friend_badges = page.get_by_text("friend", exact=True).count()
        check("recruited creatures listed as friends", friend_badges >= 2,
              f"{friend_badges} badges (incl. starter)")
        page.screenshot(path="/tmp/qw_collection.png")
        page.keyboard.press("c")

        # -- 6. save survives reload -----------------------------------------
        saved = page.evaluate("() => localStorage.getItem('quokka-wilds-save')")
        check("save written to localStorage", bool(saved))
        page.reload()
        wait_ready(page)
        recruited_after = page.evaluate(
            """() => Object.entries(window.__qw.store.getState().collection)
                  .filter(([, e]) => e.recruited).map(([id]) => id)"""
        )
        keeps = recruited_species in recruited_after if recruited_species else False
        check("save survives page reload", keeps, f"recruited after reload: {recruited_after}")

        browser.close()

    real_errors = [e for e in console_errors if "favicon" not in e]
    check("no console errors", len(real_errors) == 0,
          "; ".join(real_errors[:3]) if real_errors else "")

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
