import json
from datetime import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Timetable:
    monday: list[str]
    tuesday: list[str]
    wednesday: list[str]
    thursday: list[str]
    friday: list[str]
    overrides: dict[str, list[str]] = field(default_factory=dict)

    def get_timetable(self, day: datetime) -> list[str]:
        """
        요일에 맞는 시간표 반환.
        해당 날짜에 overrides 항목이 있으면 우선 적용.

        timetable.json 예시:
          "overrides": {
            "2026-05-22": ["체육", "수학", "영어", "국어", "과학"]
          }
        """
        date_str = day.strftime("%Y-%m-%d")
        if date_str in self.overrides:
            return self.overrides[date_str]
        weekday = day.strftime("%A").lower()  # 'monday' ~ 'friday'
        if not hasattr(self, weekday):
            raise ValueError(
                f"시간표가 없는 요일입니다: {day.strftime('%A')} ({date_str})"
            )
        return getattr(self, weekday)

    @staticmethod
    def load_timetable(data: dict) -> "Timetable":
        """JSON 데이터에서 시간표 로드. overrides 없으면 빈 dict로 초기화."""
        timetable_data = data.get("timetable", {}).copy()
        raw_overrides = timetable_data.pop("overrides", [])
        if isinstance(raw_overrides, dict):
            overrides = raw_overrides
        else:
            overrides = {o["date"]: o.get("subjects", []) for o in raw_overrides if "date" in o}
        
        # 누락된 요일 기본값 추가
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            if day not in timetable_data:
                timetable_data[day] = []
                
        return Timetable(**timetable_data, overrides=overrides)
