"""D-Day 카운트다운 모듈."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class DdayEvent:
    """하나의 D-Day 이벤트."""

    name: str
    target_date: date
    remaining: int  # 남은 일수 (0 = 당일, 음수 = 지남)
    emoji: str = "📌"


def load_dday_events(
    reference: datetime,
    path: str = "dday.json",
) -> list[DdayEvent]:
    """
    dday.json에서 이벤트를 로드하고 남은 일수를 계산.

    JSON 형식 예시::

        [
            {"name": "중간고사", "date": "2026-06-15", "emoji": "📝"},
            {"name": "여름방학", "date": "2026-07-18", "emoji": "🏖️"}
        ]

    Args:
        reference: 기준일 (다음 등교일)
        path: JSON 파일 경로

    Returns:
        남은 일수 기준 오름차순 정렬된 이벤트 목록 (지난 이벤트 제외)
    """
    p = Path(path)
    if not p.exists():
        return []

    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError, Exception:
        return []

    ref_date = reference.date() if isinstance(reference, datetime) else reference

    events: list[DdayEvent] = []
    for item in raw:
        try:
            target = date.fromisoformat(item["date"])
        except KeyError, ValueError:
            continue

        remaining = (target - ref_date).days
        if remaining < 0:
            continue  # 지난 이벤트 제외

        events.append(
            DdayEvent(
                name=item.get("name", "이벤트"),
                target_date=target,
                remaining=remaining,
                emoji=item.get("emoji", "📌"),
            )
        )

    events.sort(key=lambda e: e.remaining)
    return events
