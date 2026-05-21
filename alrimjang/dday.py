"""D-Day 카운트다운 모듈."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class DdayEvent:
    """하나의 D-Day 이벤트."""

    name: str
    target_date: date
    remaining: int  # 남은 일수 (1 이상; 당일·과거는 load_dday_events에서 제외됨)
    emoji: str = "📌"


def load_dday_events(
    reference: datetime,
    data: dict,
) -> list[DdayEvent]:
    """
    data dict에서 이벤트를 로드하고 남은 일수를 계산.

    Args:
        reference: 기준일 (생성일, 오늘)
        data: 알림장 데이터 딕셔너리

    Returns:
        남은 일수 기준 오름차순 정렬된 이벤트 목록 (당일·과거 이벤트 제외)
    """
    raw = data.get("dday", [])

    ref_date = reference.date() if isinstance(reference, datetime) else reference

    events: list[DdayEvent] = []
    for item in raw:
        try:
            target = date.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue

        remaining = (target - ref_date).days
        if remaining <= 0:
            continue  # 당일(0) 및 지난 이벤트 제외

        events.append(
            DdayEvent(
                name=item.get("name", "이벤트"),
                target_date=target,
                remaining=remaining,
                emoji=item.get("emoji", "📌"),
            )
        )

    return events
