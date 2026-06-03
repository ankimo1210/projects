"""FastAPI web layer. Thin glue: load services, keep in-memory session states,
render Jinja2 templates, persist history to SQLite."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config, db
from app.inference.question_selection import split_score
from app.inference.scoring import posteriors
from app.models import Answer
from app.services.entity_service import EntityService
from app.services.game_service import GameService, GameState


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db(config.DB_PATH)
    yield


app = FastAPI(title="akinator", lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

ENTITY_SERVICE = EntityService.from_disk()
GAME_SERVICE = GameService(ENTITY_SERVICE)
SESSIONS: dict[int, GameState] = {}


@app.get("/", response_class=HTMLResponse)
def start(request: Request):
    return templates.TemplateResponse(request, "start.html")


@app.post("/game/new")
def new_game():
    gid = db.create_game(config.DB_PATH)
    SESSIONS[gid] = GAME_SERVICE.new_game()
    return RedirectResponse(f"/game/{gid}", status_code=303)


@app.get("/game/{gid}", response_class=HTMLResponse)
def game(request: Request, gid: int):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    if GAME_SERVICE.should_guess(state):
        return RedirectResponse(f"/game/{gid}/guess", status_code=303)
    q = GAME_SERVICE.next_question(state)
    if q is None:
        return RedirectResponse(f"/game/{gid}/guess", status_code=303)
    return templates.TemplateResponse(
        request,
        "question.html",
        {"game_id": gid, "question": q, "asked_count": len(state.asked_ids)},
    )


@app.post("/game/{gid}/answer")
def answer(gid: int, answer: str = Form(...)):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    q = GAME_SERVICE.next_question(state)
    if q is not None:
        GAME_SERVICE.record_answer(state, q, Answer(answer))
        db.save_answer(config.DB_PATH, gid, q.id, answer, len(state.asked_ids))
    return RedirectResponse(f"/game/{gid}", status_code=303)


@app.get("/game/{gid}/guess", response_class=HTMLResponse)
def guess(request: Request, gid: int):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    entity, posterior = GAME_SERVICE.best_guess(state)
    return templates.TemplateResponse(
        request,
        "guess.html",
        {"game_id": gid, "entity": entity, "posterior": posterior},
    )


@app.post("/game/{gid}/result")
def result(gid: int, correct: str = Form(...)):
    state = SESSIONS.get(gid)
    if state is not None:
        entity, _ = GAME_SERVICE.best_guess(state)
        db.finish_game(config.DB_PATH, gid, entity.id, was_correct=(correct == "1"))
    return RedirectResponse("/", status_code=303)


@app.get("/game/{gid}/wrong", response_class=HTMLResponse)
def wrong_form(request: Request, gid: int):
    return templates.TemplateResponse(request, "wrong.html", {"game_id": gid})


@app.post("/game/{gid}/wrong")
def wrong_submit(gid: int, correct_entity: str = Form(...)):
    state = SESSIONS.get(gid)
    if state is not None:
        entity, _ = GAME_SERVICE.best_guess(state)
        db.finish_game(config.DB_PATH, gid, entity.id, was_correct=False)
    db.save_correction(config.DB_PATH, gid, correct_entity)
    return RedirectResponse("/", status_code=303)


@app.get("/debug/{gid}", response_class=HTMLResponse)
def debug(request: Request, gid: int):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    post = posteriors(state.log_scores)
    ranked = sorted(post.items(), key=lambda kv: kv[1], reverse=True)[:8]
    candidates = []
    for eid, p in ranked:
        e = ENTITY_SERVICE.get_entity(eid)
        candidates.append({"id": eid, "name": e.name, "posterior": p,
                           "log_score": state.log_scores[eid], "features": e.features})
    qmap = {q.id: q for q in ENTITY_SERVICE.questions}
    history = [{"text": qmap[qid].text if qid in qmap else qid, "answer": ans}
               for qid, ans in state.history]
    nq = GAME_SERVICE.next_question(state)
    next_split = (split_score(nq, ENTITY_SERVICE.entities, post) if nq else 0.0)
    return templates.TemplateResponse(
        request,
        "debug.html",
        {"game_id": gid, "candidates": candidates,
         "history": history, "next_question": nq, "next_split": next_split},
    )
