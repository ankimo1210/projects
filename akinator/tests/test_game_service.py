from app.services.entity_service import EntityService


def test_entity_service_lookup(small_pool, small_questions):
    svc = EntityService(small_pool, small_questions)
    assert svc.get_entity("a").name == "アクターA"
    assert svc.get_entity("zzz") is None
    assert len(svc.entities) == 4
    assert len(svc.questions) == 4
