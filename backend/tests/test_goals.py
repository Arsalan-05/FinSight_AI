"""Goal progress PATCH and agent prompt integration."""

from agent.goals import goals_summary_for_prompt, update_goal
from db.models import User


def test_patch_goal_progress(client, db_session):
    user = User(id="goal-user", email="goal@test.com", name="Goal User")
    db_session.add(user)
    db_session.commit()

    from app.auth import get_current_user_optional
    from app.main import app

    app.dependency_overrides[get_current_user_optional] = lambda: user

    created = client.post(
        "/goals/",
        json={"title": "Emergency fund", "target_amount": 5000},
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    patched = client.patch(f"/goals/{goal_id}", json={"current_amount": 1200})
    assert patched.status_code == 200
    body = patched.json()
    assert body["current_amount"] == 1200

    summary = goals_summary_for_prompt(user)
    assert "Emergency fund" in summary
    assert "1,200" in summary

    app.dependency_overrides.pop(get_current_user_optional, None)


def test_update_goal_not_found(db_session):
    user = User(id="g2", email="g2@test.com", name="G2")
    db_session.add(user)
    db_session.commit()
    assert update_goal(db_session, user, "missing", current_amount=10) is None
