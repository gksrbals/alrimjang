from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Timetable:
    monday: list[str]
    tuesday: list[str]
    wednesday: list[str]
    thursday: list[str]
    friday: list[str]
    overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    def get_timetable(self, day: datetime) -> list[str]:
        """
        요일에 맞는 시간표 반환.
        해당 날짜에 overrides 항목이 있으면 부분 적용 (Sparse Override).

        timetable.json 예시:
          "overrides": {
            "2026-05-22": {"3": "자율", "7": "방과후"}
          }
        """
        date_str = day.strftime("%Y-%m-%d")
        weekday = day.strftime("%A").lower()  # 'monday' ~ 'friday'

        if not hasattr(self, weekday):
            raise ValueError(f"시간표가 없는 요일입니다: {day.strftime('%A')} ({date_str})")

        base_tt = getattr(self, weekday).copy()

        if date_str in self.overrides:
            override_rules = self.overrides[date_str]
            # 호환성 처리: 이전 배열 형태의 override가 남아있을 경우
            if isinstance(override_rules, list):
                return override_rules

            for period_str, subject in override_rules.items():
                try:
                    period_idx = int(period_str) - 1  # 1교시 -> index 0
                    if period_idx < 0:
                        continue
                    # 배열 길이가 부족하면 빈 문자열로 확장
                    while len(base_tt) <= period_idx:
                        base_tt.append("")
                    base_tt[period_idx] = subject
                except ValueError:
                    pass

        # 빈 문자열을 뒤에서부터 제거 (trim)
        while base_tt and not base_tt[-1]:
            base_tt.pop()

        return base_tt

    @staticmethod
    def load_timetable(data: dict) -> "Timetable":
        """JSON 데이터에서 시간표 로드. overrides 없으면 빈 dict로 초기화."""
        timetable_data = data.get("timetable", {}).copy()
        raw_overrides = timetable_data.pop("overrides", {})
        if isinstance(raw_overrides, list):
            overrides = {o["date"]: o.get("subjects", {}) for o in raw_overrides if "date" in o}
        else:
            overrides = raw_overrides

        # 누락된 요일 기본값 추가
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            if day not in timetable_data:
                timetable_data[day] = []

        return Timetable(**timetable_data, overrides=overrides)
