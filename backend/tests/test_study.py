import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from test_records_postgres import DATABASE, run_check

from app.models.study import StudyEvent, StudyPlan
from app.services.study_parser import parse_text
from app.services.study_service import allocate, working_days


def test_ready_schedule_without_year_requires_review_and_explicit_year():
    text = "25 жовтня — питання 1–9; 26 жовтня — 10–16"
    unknown = parse_text(text)
    assert unknown["preserve_schedule"] and len(unknown["items"]) == 16
    assert all(row["scheduled_date"] is None for row in unknown["items"])
    assert any("року" in issue["message"] for issue in unknown["issues"])
    parsed = parse_text(text, 2026)
    assert parsed["items"][0]["scheduled_date"] == "2026-10-25"
    assert parsed["items"][9]["scheduled_date"] == "2026-10-26"
    assert parsed["issues"] == []


def test_import_groups_reserve_and_prefixed_identifiers():
    result = parse_text(
        "Предмет: Алгебра\nДедлайн: 2026-10-30\nРівень 1 (вага 3): N1.1–N1.8\n29.10.2026 — резерв"
    )
    assert result["name"] == "Алгебра" and result["total"] == 8
    assert result["reserve_days"] == 1 and result["deadline"] == "2026-10-30"
    assert result["items"][7]["label"] == "N1.8" and result["items"][0]["weight"] == 3


def test_duplicate_gaps_overlap_total_and_subitems_are_not_silently_counted():
    result = parse_text("Всього: 8\nПитання 1–3\nПитання 3, 5\n1.1 підпункт\nКартка 1.2")
    assert [row["label"] for row in result["items"]] == ["1", "2", "3", "5"]
    messages = " ".join(issue["message"] for issue in result["issues"])
    assert all(token in messages for token in ("Дублікат", "Пропуски", "Заявлено", "Підпункт"))


@pytest.mark.parametrize("value", ["N1.8–N2.3", "5–1", "1–10000"])
def test_unsafe_ranges_are_reported(value):
    result = parse_text(value)
    assert result["items"] == [] and result["issues"]


def test_weighted_schedule_balance_buffers_and_zero_days():
    rows = [dict(label=str(n + 1), weight=w) for n, w in enumerate([4, 4, 1, 1, 1, 1])]
    output = allocate(rows, date(2026, 10, 25), date(2026, 10, 29), 2)
    assert set(output.values()) == {"2026-10-25", "2026-10-26"}
    loads = [
        sum(row["weight"] for row in rows if output[row["label"]] == day)
        for day in set(output.values())
    ]
    assert loads == [6, 6]
    assert set(allocate(rows, date(2026, 10, 29), date(2026, 10, 29), 0).values()) == {None}
    assert len(working_days(date(2026, 10, 25), date(2026, 10, 29), 2)) == 2


def test_plain_schedule_is_contiguous_and_uses_early_days():
    rows = [dict(label=str(n), weight=1) for n in range(1, 7)]
    output = allocate(rows, date(2026, 10, 25), date(2026, 10, 27), 0)
    assert [output[str(n)] for n in range(1, 7)] == ["2026-10-25"] * 3 + ["2026-10-26"] * 3
    short = allocate(rows[:2], date(2026, 10, 25), date(2026, 10, 30), 0)
    assert short == {"1": "2026-10-25", "2": "2026-10-26"}


def test_count_only_and_reserve_dates_require_a_deadline_not_a_guessed_one():
    result = parse_text("Мій предмет\n16 питань\n2026-10-29 — резерв")
    assert result["declared_total"] == 16 and result["items"] == []
    assert result["deadline"] is None and result["reserve_days"] == 1
    assert any("дедлайн" in issue["message"] for issue in result["issues"])


def test_invalid_weight_and_long_numbers_are_reported_without_inventing_items():
    result = parse_text("Рівень 1 (вага 1000): N1.1–N1.3")
    assert result["items"][0]["weight"] == 1000
    assert any("Складність" in issue["message"] for issue in result["issues"])
    assert parse_text("9" * 5000)["items"] == []


def test_shortcuts_cannot_read_or_modify_study_plans():
    from fakes import client_for_token_auth

    client = client_for_token_auth()
    headers = {"Authorization": "Bearer sg_not-a-session"}
    assert client.get("/api/v1/study/plans", headers=headers).status_code == 401
    assert (
        client.post("/api/v1/study/parse", headers=headers, json={"text": "1–3"}).status_code == 401
    )


def body(total=12):
    today = datetime.now(UTC).date()
    return dict(
        name="Власний план",
        total=total,
        deadline=(today + timedelta(days=7)).isoformat(),
        reserve_days=2,
    )


@pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
def test_create_edit_check_replan_move_reload_and_owner_isolation():
    async def check(c, h, ids, sessions):
        response = await c.post("/api/v1/study/plans", headers=h[0], json=body())
        assert response.status_code == 201, response.text
        plan = response.json()
        assert len(plan["items"]) == 12 and plan["version"] == 1
        original_day = plan["items"][0]["scheduled_date"]
        checked = await c.post(
            f"/api/v1/study/plans/{plan['id']}/items/1",
            headers=h[0],
            json=dict(done=True, expected_version=1),
        )
        assert checked.status_code == 200, checked.text
        plan = checked.json()
        done = plan["items"][0]["done_at"]
        # A fresh request/session is the equivalent of reloading the client.
        assert (await c.get("/api/v1/study/plans", headers=h[0])).json()[0]["items"][0][
            "done_at"
        ] == done
        assert (await c.get("/api/v1/study/plans", headers=h[1])).json() == []
        assert (
            await c.get(f"/api/v1/study/plans/{plan['id']}/events", headers=h[1])
        ).status_code == 404
        edited = await c.put(
            f"/api/v1/study/plans/{plan['id']}",
            headers=h[0],
            json={**body(15), "expected_version": plan["version"]},
        )
        assert edited.status_code == 200, edited.text
        plan = edited.json()
        assert (
            plan["items"][0]["done_at"] == done
            and plan["items"][0]["scheduled_date"] == original_day
        )
        preview = (
            await c.get(f"/api/v1/study/plans/{plan['id']}/replan-preview", headers=h[0])
        ).json()
        assert "1" not in preview["assignments"] and len(preview["assignments"]) == 14
        assert (await c.get("/api/v1/study/plans", headers=h[0])).json()[0]["version"] == plan[
            "version"
        ]
        response = await c.post(
            f"/api/v1/study/plans/{plan['id']}/schedule",
            headers=h[0],
            json={
                "expected_version": preview["expected_version"],
                "assignments": preview["assignments"],
            },
        )
        assert response.status_code == 200, response.text
        plan = response.json()
        assert plan["items"][0]["done_at"] == done
        stale = await c.post(
            f"/api/v1/study/plans/{plan['id']}/items/2",
            headers=h[0],
            json=dict(done=True, expected_version=1),
        )
        assert stale.status_code == 409
        assignments = {
            row["label"]: row["scheduled_date"] for row in plan["items"] if not row["done_at"]
        }
        assignments["2"] = plan["start_date"]
        assert (
            await c.post(
                f"/api/v1/study/plans/{plan['id']}/schedule",
                headers=h[0],
                json=dict(expected_version=plan["version"], assignments=assignments),
            )
        ).status_code == 200
        events = (await c.get(f"/api/v1/study/plans/{plan['id']}/events", headers=h[0])).json()
        assert {event["kind"] for event in events} >= {
            "created",
            "edited",
            "completed",
            "replanned",
        }
        exported = (await c.get("/api/v1/me/export", headers=h[0])).json()
        assert len(exported["study_plans"][0]["items"]) == 15 and exported["study_events"]
        async with sessions() as session:
            assert await session.get(StudyPlan, plan["id"]) is not None

    run_check(check)


@pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
def test_import_preserves_schedule_and_edit_preview_keeps_completed_questions():
    async def check(c, h, ids, sessions):
        today = datetime.now(UTC).date()
        first, second = today.isoformat(), (today + timedelta(days=1)).isoformat()
        text = f"Предмет: Мій предмет\n{first} — питання 1–9; {second} — 10–16"
        parsed = (await c.post("/api/v1/study/parse", headers=h[0], json={"text": text})).json()
        payload = {
            **body(16),
            "name": parsed["name"],
            "items": parsed["items"],
            "preserve_schedule": True,
        }
        plan = (await c.post("/api/v1/study/plans", headers=h[0], json=payload)).json()
        assert (
            plan["items"][0]["scheduled_date"] == first
            and plan["items"][9]["scheduled_date"] == second
        )
        plan = (
            await c.post(
                f"/api/v1/study/plans/{plan['id']}/items/1",
                headers=h[0],
                json=dict(done=True, expected_version=plan["version"]),
            )
        ).json()
        preview = await c.post(
            f"/api/v1/study/preview?plan_id={plan['id']}",
            headers=h[0],
            json={**payload, "expected_version": plan["version"], "preserve_schedule": False},
        )
        assert preview.status_code == 200, preview.text
        assert datetime.fromisoformat(
            preview.json()["items"][0]["done_at"]
        ) == datetime.fromisoformat(plan["items"][0]["done_at"])
        assert preview.json()["items"][0]["scheduled_date"] == first
        # Reducing the amount must never silently erase a completed question.
        completed_last = (
            await c.post(
                f"/api/v1/study/plans/{plan['id']}/items/16",
                headers=h[0],
                json=dict(done=True, expected_version=plan["version"]),
            )
        ).json()
        removed = await c.put(
            f"/api/v1/study/plans/{plan['id']}",
            headers=h[0],
            json={**body(15), "expected_version": completed_last["version"]},
        )
        assert removed.status_code == 422
        assert len((await c.get("/api/v1/study/plans", headers=h[0])).json()[0]["items"]) == 16

    run_check(check)


@pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
def test_reserve_rejection_expired_plan_concurrent_updates_and_cascade():
    async def check(c, h, ids, sessions):
        plan = (await c.post("/api/v1/study/plans", headers=h[0], json=body(3))).json()
        assignments = {row["label"]: plan["deadline"] for row in plan["items"]}
        result = await c.post(
            f"/api/v1/study/plans/{plan['id']}/schedule",
            headers=h[0],
            json=dict(expected_version=1, assignments=assignments),
        )
        assert result.status_code == 422
        replies = await asyncio.gather(
            *(
                c.post(
                    f"/api/v1/study/plans/{plan['id']}/items/{n}",
                    headers=h[0],
                    json=dict(expected_version=1, done=True),
                )
                for n in (1, 2)
            )
        )
        assert sorted(reply.status_code for reply in replies) == [200, 409]
        today = datetime.now(UTC).date()
        old = {
            **body(2),
            "start_date": (today - timedelta(days=4)).isoformat(),
            "deadline": (today - timedelta(days=1)).isoformat(),
            "reserve_days": 0,
        }
        expired = (await c.post("/api/v1/study/plans", headers=h[0], json=old)).json()
        preview = (
            await c.get(f"/api/v1/study/plans/{expired['id']}/replan-preview", headers=h[0])
        ).json()
        assert preview["summary"]["status"] == "expired" and set(
            preview["assignments"].values()
        ) == {None}
        await c.request("DELETE", "/api/v1/me", headers=h[0], json=dict(confirm=True))
        async with sessions() as session:
            assert not list(
                await session.scalars(select(StudyEvent).where(StudyEvent.user_id == ids[0]))
            )
            assert not list(
                await session.scalars(select(StudyPlan).where(StudyPlan.user_id == ids[0]))
            )

    run_check(check)
