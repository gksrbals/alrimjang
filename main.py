import contextlib
import io
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows 터미널 인코딩을 UTF-8로 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import holidays
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.text import Text

from alrimjang.timetable import Timetable
from alrimjang.school_meal import SchoolMeal
from alrimjang.weather import Weather
from alrimjang.dday import DdayEvent, load_dday_events
from alrimjang.cli import (
    get_user_input,
    print_header,
    print_progress_header,
)
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
            f"\n  [yellow]⚠️  내일({tomorrow.month}/{tomorrow.day})은 "
            f"[bold]{name}[/bold]입니다.[/yellow]\n"
            f"  [dim]다음 등교일("
            f"{candidate.month}/{candidate.day} "
            f"{weekday_kr[candidate.weekday()]})로 알림장을 작성합니다.[/dim]\n"
        )

    return today, candidate


# ── 진행 상태 출력 헬퍼 ─────────────────────────────────────────────


def _print_step(label: str, detail: str = "", style: str = "dim") -> None:
    """✓ 라벨 디테일 형식으로 한 줄 출력."""
    text = Text()
    text.append("  ✓ ", style="dim green")
    text.append(label, style=style)
    if detail:
        text.append(f" {detail}", style="white")
    console.print(text)


def _print_skip(label: str) -> None:
    """- 라벨 형식으로 비활성 항목 출력."""
    console.print(f"  [dim]- {label}[/dim]")


# ── 메인 ────────────────────────────────────────────────────────────


def main() -> None:
    # ══════════════════════════════════════════════════
    #  Phase 1: 입력
    # ══════════════════════════════════════════════════

    school_holidays = _load_school_holidays()
    today, next_day = get_next_school_day(school_holidays)
    next_datetime = datetime(next_day.year, next_day.month, next_day.day)

    print_header(today, next_day)

    meal_env = os.getenv("SCHOOL_MEAL_ENABLED", "True").strip().lower() in ("true", "1")
    weather_env = os.getenv("WEATHER_ENABLED", "True").strip().lower() in ("true", "1")
    dday_env = os.getenv("DDAY_ENABLED", "True").strip().lower() in ("true", "1")

    raw_notices, meal_enabled, weather_enabled, dday_enabled = get_user_input(
        meal_env, weather_env, dday_env
    )

    if raw_notices is None:
        console.print("  [red]✗ 공지사항 입력이 취소되었습니다. 종료합니다.[/red]")
        sys.exit(0)

    # 설정이 변경되었다면 .env에 저장
    env_path = Path(".env")
    if env_path.exists():
        if meal_enabled != meal_env:
            set_key(str(env_path), "SCHOOL_MEAL_ENABLED", str(meal_enabled))
        if weather_enabled != weather_env:
            set_key(str(env_path), "WEATHER_ENABLED", str(weather_enabled))
        if dday_enabled != dday_env:
            set_key(str(env_path), "DDAY_ENABLED", str(dday_enabled))

    if not raw_notices:
        console.print("  [red]✗ 공지사항이 없습니다. 종료합니다.[/red]")
        sys.exit(0)

    # ══════════════════════════════════════════════════
    #  Phase 2: clear → 수집 + 생성 + 완료
    # ══════════════════════════════════════════════════

    console.clear()
    print_progress_header(next_day)

    _print_step("공지사항", f"{len(raw_notices)}줄")

    # 시간표
    timetable_obj = Timetable.load_timetable("timetable.json")
    timetable = timetable_obj.get_timetable(next_datetime)
    _print_step("시간표", f"{len(timetable)}교시")

    # 급식
    school_meal = None
    if meal_enabled:
        school_meal = SchoolMeal.fetch_school_meal(next_datetime)
        if school_meal:
            _print_step("급식", school_meal.calories)
        else:
            _print_skip("급식 정보 없음")
    else:
        _print_skip("급식 비활성화")

    # 날씨
    weather = None
    if weather_enabled:
        weather = Weather.fetch_weather(next_datetime)
        if weather:
            _print_step(
                "날씨", f"{weather.emoji} {weather.temp}° {weather.description}"
            )
        else:
            _print_skip("날씨 정보 없음")
    else:
        _print_skip("날씨 비활성화")

    # D-Day
    dday_events: list[DdayEvent] = []
    if dday_enabled:
        dday_events = load_dday_events(next_datetime)
        if dday_events:
            _print_step("D-Day", f"{len(dday_events)}개")
    else:
        _print_skip("D-Day 비활성화")

    # 이미지 생성
    console.print()
    today_datetime = datetime(today.year, today.month, today.day)

    with console.status("  [dim]이미지 생성 중...[/dim]", spinner="dots"):
        # html2image 브라우저 stdout/stderr 억제
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            render_and_export(
                today=today_datetime,
                next_day=next_datetime,
                timetable=timetable,
                school_meal=school_meal,
                weather=weather,
                raw_notices=raw_notices,
                dday_events=dday_events,
            )

    filename = f"{next_day.strftime('%Y%m%d')}.png"

    # ── 완료 ──
    result = Text()
    result.append("  ✅ ", style="green")
    result.append(f"output/{filename}", style="bold white underline")
    result.append(" 저장 완료\n", style="green")
    result.append("  📋 ", style="")
    result.append("클립보드 복사 완료", style="green")
    result.append(" — Ctrl+V로 붙여넣기!\n", style="dim")
    console.print(result)


if __name__ == "__main__":
    main()
