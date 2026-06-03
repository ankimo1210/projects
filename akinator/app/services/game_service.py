"""Per-session game orchestration over the pure inference functions.

GameState is plain data (serializable to/from the request/DB). GameService is
stateless beyond the EntityService it wraps; all mutation lives on the passed-in
state."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.inference.question_selection import select_question
from app.inference.scoring import posteriors, top_candidates, update_log_score
from app.models import Answer, Entity, Question
from app.services.entity_service import EntityService


@dataclass
class GameState:
    log_scores: dict[str, float]
    asked_ids: set[str] = field(default_factory=set)
    history: list[tuple[str, str]] = field(default_factory=list)  # (question_id, answer)


class GameService:
    def __init__(self, entities: EntityService, guess_threshold: float = 0.85,
                 max_questions: int = 20) -> None:
        self.entities = entities
        self.guess_threshold = guess_threshold
        self.max_questions = max_questions

    def new_game(self) -> GameState:
        return GameState(log_scores={e.id: 0.0 for e in self.entities.entities})

    def _weights(self, state: GameState) -> dict[str, float]:
        return posteriors(state.log_scores)

    def next_question(self, state: GameState) -> Question | None:
        return select_question(
            self.entities.questions,
            self.entities.entities,
            self._weights(state),
            state.asked_ids,
        )

    def record_answer(self, state: GameState, question: Question, answer: Answer) -> None:
        for e in self.entities.entities:
            state.log_scores[e.id] = update_log_score(
                state.log_scores[e.id], e, question, answer
            )
        state.asked_ids.add(question.id)
        state.history.append((question.id, answer.value))

    def best_guess(self, state: GameState) -> tuple[Entity, float]:
        top = top_candidates(state.log_scores, k=1)
        entity_id, posterior = top[0]
        return self.entities.get_entity(entity_id), posterior

    def should_guess(self, state: GameState) -> bool:
        if len(state.asked_ids) >= self.max_questions:
            return True
        if self.next_question(state) is None:
            return True
        _, posterior = self.best_guess(state)
        return posterior >= self.guess_threshold
