import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows 터미널 인코딩을 UTF-8로 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import holidays
from dotenv import load_dotenv
from rich.console import Console

from alrimjang.timetable import Timetable
from alrimjang.school_meal import SchoolMeal
from alrimjang.weather import Weather
from alrimjang.cli import get_user_input
from alrimjang.renderer import render_and_export

load_dotenv()
console = Console(highlight=False)

# 한국 공휴일
_KR_HOLIDAYS = holidays.KR()


def _load_school_holidays(path: str = "school_holidays.json") -> dict[str, str]:
    """학교 자체 휴일 파일 로드. 없으면 빈 dict."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _is_holiday(d: date, school_holidays: dict[str, str]) -> bool:
    """주말 or 국가공휴일 or 학교자체휴일 여부"""
    return (
        d.weekday() >= 5  # 토·일
        or d in _KR_HOLIDAYS  # 국가 공휴일
        or d.isoformat() in school_holidays  # 학교 자체 휴일
    )


def _get_holiday_name(d: date, school_holidays: dict[str, str]) -> str:
    """휴일 이름 반환"""
    if d.isoformat() in school_holidays:
        return school_holidays[d.isoformat()]
    if d in _KR_HOLIDAYS:
        return _KR_HOLIDAYS[d]
    if d.weekday() == 5:
        return "토요일"
    return "일요일"


def get_next_school_day(school_holidays: dict[str, str]) -> tuple[date, date]:
    """
    오늘 날짜와 다음 등교일을 반환.
    주말·국가공휴일·학교자체휴일을 모두 건너뜀.
    """
    today = date.today()
    candidate = today + timedelta(days=1)

    while _is_holiday(candidate, school_holidays):
        candidate += timedelta(days=1)

    # 내일이 아닌 경우 안내 출력
    if candidate > today + timedelta(days=1):
        tomorrow = today + timedelta(days=1)
        name = _get_holiday_name(tomorrow, school_holidays)
        weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]
        console.print(
            f"\n[yellow]⚠️  내일({tomorrow.month}/{tomorrow.day})은 "
            f"[bold]{name}[/bold]입니다.[/yellow]\n"
            f"   [dim]다음 등교일("
            f"{candidate.month}/{candidate.day} "
            f"{weekday_kr[candidate.weekday()]})로 알림장을 작성합니다.[/dim]\n"
        )

    return today, candidate


def main() -> None:
    console.rule("[bold]📋 알림장[/bold]")

    # 학교 자체 휴일 로드
    school_holidays = _load_school_holidays()

    # 다음 등교일 계산
    today, next_day = get_next_school_day(school_holidays)
    next_datetime = datetime(next_day.year, next_day.month, next_day.day)

    # 공지사항 입력
    raw_notices = get_user_input()
    if not raw_notices:
        console.print("[red]공지사항이 없습니다. 종료합니다.[/red]")
        sys.exit(0)

    # 시간표 로드
    timetable_obj = Timetable.load_timetable("timetable.json")
    timetable = timetable_obj.get_timetable(next_datetime)

    # 급식 조회
    console.print("[dim]급식 정보 조회 중...[/dim]")
    school_meal = SchoolMeal.fetch_school_meal(next_datetime)
    if school_meal:
        console.print("[green]급식 조회 완료[/green]")
    else:
        console.print("[yellow]급식 정보 없음 (섹션 숨김)[/yellow]")

    # 날씨 조회
    console.print("[dim]날씨 정보 조회 중...[/dim]")
    weather = Weather.fetch_weather(next_datetime)
    if weather:
        console.print("[green]날씨 조회 완료[/green]")
    else:
        console.print("[yellow]날씨 정보 없음 (섹션 숨김)[/yellow]")

    console.print()

    # 렌더링 & 출력
    today_datetime = datetime(today.year, today.month, today.day)
    render_and_export(
        today=today_datetime,
        next_day=next_datetime,
        timetable=timetable,
        school_meal=school_meal,
        weather=weather,
        raw_notices=raw_notices,
    )

    console.rule("[bold green]완료[/bold green]")


if __name__ == "__main__":
    main()
