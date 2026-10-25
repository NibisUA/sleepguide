import heapq
import math
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select

from app.analytics.sleep_rules import local_date_of
from app.models.study import StudyEvent, StudyPlan
from app.services.diary_lock import lock_diary
from app.services.errors import DomainError


def working_days(start, deadline, reserve):
    size = (deadline - timedelta(days=reserve) - start).days
    if size > 1096:
        raise DomainError("study_invalid", "План може тривати не більше трьох років")
    return [start + timedelta(days=n) for n in range(max(0, size))]


def allocate(items, start, deadline, reserve):
    """Greedy largest-first weighted balancing; no empty reserve days get work."""
    days = working_days(start, deadline, reserve)
    pending = [row for row in items if not row.get("done_at")]
    result = {row["label"]: None for row in pending}
    if days and pending and all(row["weight"] == 1 for row in pending):
        count, extra = divmod(len(pending), len(days))
        cursor = 0
        for index, day in enumerate(days):
            for row in pending[cursor : cursor + count + (index < extra)]:
                result[row["label"]] = day.isoformat()
            cursor += count + (index < extra)
        return result
    if days and pending:
        loads = [(0, index) for index in range(len(days))]
        heapq.heapify(loads)
        for row in sorted(pending, key=lambda item: -item["weight"]):
            load, index = heapq.heappop(loads)
            result[row["label"]] = days[index].isoformat()
            heapq.heappush(loads, (load + row["weight"], index))
    return result


def summary(plan, today):
    pending = [row for row in plan.items if not row.get("done_at")]
    days = working_days(max(today, plan.start_date), plan.deadline, plan.reserve_days)
    load = sum(row["weight"] for row in pending)
    return dict(
        total=len(plan.items),
        done=len(plan.items) - len(pending),
        remaining=len(pending),
        percent=round((len(plan.items) - len(pending)) * 100 / len(plan.items))
        if plan.items
        else 0,
        working_days_left=len(days),
        days_to_deadline=max(0, (plan.deadline - today).days),
        daily_questions=math.ceil(len(pending) / len(days)) if days else None,
        daily_weight=math.ceil(load / len(days)) if days else None,
        status="complete"
        if not pending
        else "expired"
        if today > plan.deadline
        else "no_days"
        if not days
        else "overload"
        if plan.daily_capacity
        and (
            load > len(days) * plan.daily_capacity
            or any(row["weight"] > plan.daily_capacity for row in pending)
        )
        else "active",
    )


async def get_plan(session, user, plan_id):
    plan = await session.scalar(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id, StudyPlan.id == plan_id)
        .with_for_update()
    )
    if plan is None:
        raise DomainError("study_not_found", "План не знайдено")
    return plan


def check_version(plan, version):
    if version != plan.version:
        raise DomainError(
            "study_conflict", "План змінено в іншій вкладці. Онови його та повтори дію"
        )


def event(session, user, plan, kind, detail):
    session.add(StudyEvent(user_id=user.id, plan_id=plan.id, kind=kind, detail=detail))


def validate_schedule(items, start, deadline, reserve):
    last = deadline - timedelta(days=reserve)
    for item in items:
        if item.get("done_at") or not item.get("scheduled_date"):
            continue
        day = date.fromisoformat(item["scheduled_date"])
        if not start <= day < last:
            raise DomainError(
                "study_invalid",
                "Дата питання поза робочими днями. Дедлайн і дні запасу залишаються без нових питань",
            )


async def save_plan(session, user, body, plan_id=None):
    await lock_diary(session, user.id)
    today = local_date_of(datetime.now(UTC), user.timezone)
    start = body.start_date or today
    if start > body.deadline:
        raise DomainError("study_invalid", "Початок не може бути після дедлайну")
    working_days(start, body.deadline, body.reserve_days)
    if plan_id:
        plan = await get_plan(session, user, plan_id)
        check_version(plan, body.expected_version)
        old = {item["label"]: item for item in plan.items}
    else:
        count = await session.scalar(
            select(func.count()).select_from(StudyPlan).where(StudyPlan.user_id == user.id)
        )
        if count >= 50:
            raise DomainError("study_invalid", "Можна створити до 50 планів")
        plan = StudyPlan(user_id=user.id, version=0)
        old = {}
    incoming = prepare_items(body, old, today, start)
    plan.name, plan.deadline, plan.start_date = body.name, body.deadline, start
    plan.reserve_days, plan.daily_capacity, plan.items = (
        body.reserve_days,
        body.daily_capacity,
        incoming,
    )
    plan.version += 1
    session.add(plan)
    await session.flush()
    event(
        session,
        user,
        plan,
        "edited" if plan_id else "created",
        dict(total=len(incoming), deadline=body.deadline.isoformat(), items=incoming),
    )
    await session.commit()
    return plan


async def check_item(session, user, plan_id, label, body):
    await lock_diary(session, user.id)
    plan = await get_plan(session, user, plan_id)
    check_version(plan, body.expected_version)
    rows = [dict(row) for row in plan.items]
    row = next((item for item in rows if item["label"] == label), None)
    if row is None:
        raise DomainError("study_not_found", "Питання не знайдено")
    row["done_at"] = datetime.now(UTC).isoformat() if body.done else None
    plan.items = rows
    plan.version += 1
    event(session, user, plan, "completed" if body.done else "reopened", dict(label=label))
    await session.commit()
    return plan


async def apply_schedule(session, user, plan_id, body):
    await lock_diary(session, user.id)
    plan = await get_plan(session, user, plan_id)
    check_version(plan, body.expected_version)
    pending = {row["label"] for row in plan.items if not row.get("done_at")}
    if set(body.assignments) != pending:
        raise DomainError("study_invalid", "Розклад має містити рівно всі невиконані питання")
    rows = [dict(row) for row in plan.items]
    changes = []
    for row in rows:
        if row["label"] in pending:
            value = body.assignments[row["label"]]
            new_date = value.isoformat() if value else None
            if new_date != row.get("scheduled_date"):
                changes.append(
                    dict(label=row["label"], before=row.get("scheduled_date"), after=new_date)
                )
            row["scheduled_date"] = new_date
    validate_schedule(rows, plan.start_date, plan.deadline, plan.reserve_days)
    plan.items, plan.version = rows, plan.version + 1
    event(session, user, plan, "replanned", dict(changes=changes))
    await session.commit()
    return plan


def prepare_items(body, old, today, start):
    if body.items is None and old and any(not key.isdigit() for key in old):
        raise DomainError("study_invalid", "Для власних номерів редагуй список питань")
    incoming = (
        [item.model_dump(mode="json") for item in body.items]
        if body.items is not None
        else [
            dict(
                label=str(n),
                title="",
                group="",
                weight=1,
                scheduled_date=old.get(str(n), {}).get("scheduled_date"),
            )
            for n in range(1, body.total + 1)
        ]
    )
    labels = {item["label"] for item in incoming}
    if any(row.get("done_at") and key not in labels for key, row in old.items()):
        raise DomainError(
            "study_invalid", "Не можна прибрати виконане питання. Залиши його номер у списку"
        )
    for row in incoming:
        row["done_at"] = old.get(row["label"], {}).get("done_at")
        if row["done_at"]:
            row["scheduled_date"] = old[row["label"]].get("scheduled_date")
    if not body.preserve_schedule:
        allocation = allocate(incoming, max(today, start), body.deadline, body.reserve_days)
        for row in incoming:
            if row["label"] in allocation:
                row["scheduled_date"] = allocation[row["label"]]
    validate_schedule(incoming, start, body.deadline, body.reserve_days)
    return incoming
