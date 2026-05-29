"""알림장 웹 에디터 서버."""

from __future__ import annotations

import base64
import json
import logging
import os
import signal
import threading
import time
import webbrowser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import holidays
from dotenv import load_dotenv, set_key
from flask import Flask, jsonify, render_template, request, send_from_directory

from .data import load_data
from .dday import load_dday_events
from .renderer import copy_png_to_clipboard, parse_notices, render_html
from .school_meal import SchoolMeal
from .timetable import Timetable
from .weather import Weather

load_dotenv()

_KR_HOLIDAYS = holidays.KR()

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
)


# ── 캐시 ─────────────────────────────────────────────────────────

_cache: dict = {}


def _is_holiday(d: date, school_holidays: dict[str, str]) -> bool:
    return d.weekday() >= 5 or d in _KR_HOLIDAYS or d.isoformat() in school_holidays


def _get_next_school_day(school_holidays: dict[str, str]) -> tuple[date, date]:
    # 항상 KST(UTC+9) 기준으로 현재 날짜 계산
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()
    candidate = today + timedelta(days=1)
    while _is_holiday(candidate, school_holidays):
        candidate += timedelta(days=1)
    return today, candidate


# ── 라우트 ────────────────────────────────────────────────────────


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    """현재 설정·데이터를 JSON으로 반환."""
    if not _cache:
        return jsonify({"error": "서버 초기화 중입니다."}), 503
    meal = _cache.get("school_meal")
    weather = _cache.get("weather")
    dday = _cache.get("dday_events", [])

    return jsonify(
        {
            "today_str": _cache["today_str"],
            "next_day_str": _cache["next_day_str"],
            "next_day_date": _cache["next_day"].isoformat(),
            "timetable": _cache["timetable"],
            "settings": {
                **_cache["settings"],
                "school_start_hour": _cache.get("school_start_hour", 9),
            },
            "school_meal": {
                "menus": meal.menus,
                "calories": meal.calories,
            }
            if meal
            else None,
            "weather": {
                "emoji": weather.emoji,
                "temp": weather.temp,
                "max_temp": weather.max_temp,
                "min_temp": weather.min_temp,
                "description": weather.description,
                "rain_prob": weather.rain_prob,
                "wind_speed": weather.wind_speed,
            }
            if weather
            else None,
            "dday_events": [{"name": e.name, "emoji": e.emoji, "remaining": e.remaining} for e in dday],
        }
    )


@app.route("/api/preview", methods=["POST"])
def preview():
    """공지사항 텍스트를 받아 미리보기 HTML 반환."""
    if not _cache:
        return jsonify({"error": "서버 초기화 중입니다."}), 503
    body = request.get_json(silent=True) or {}
    notices_text: str = body.get("notices", "")
    settings: dict = body.get("settings", _cache["settings"])

    lines = [line for line in notices_text.splitlines() if line.strip()] if notices_text.strip() else []
    notices = parse_notices(lines)

    meal = _cache.get("school_meal") if settings.get("meal") else None
    weather = _cache.get("weather") if settings.get("weather") else None
    dday = _cache.get("dday_events", []) if settings.get("dday") else []

    html = render_html(
        today=_cache["today_dt"],
        next_day=_cache["next_dt"],
        timetable=_cache["timetable"],
        school_meal=meal,
        weather=weather,
        notices=notices,
        dday_events=dday,
        school_start_hour=_cache.get("school_start_hour", 9),
    )

    return jsonify({"html": html})


@app.route("/api/generate", methods=["POST"])
def generate():
    """프론트엔드에서 캡처한 이미지를 파일로 저장하고 클립보드에 복사."""
    body = request.get_json(silent=True) or {}
    data_url: str = body.get("dataUrl", "")
    settings: dict = body.get("settings", _cache["settings"])

    if not data_url or not data_url.startswith("data:image/png;base64,"):
        return jsonify({"success": False, "error": "유효하지 않은 이미지 데이터입니다."}), 400

    # 설정 변경 .env 저장 (필요 시)
    env_path = Path(".env")
    if env_path.exists():
        set_key(str(env_path), "SCHOOL_MEAL_ENABLED", str(settings.get("meal", True)))
        set_key(str(env_path), "WEATHER_ENABLED", str(settings.get("weather", True)))
        set_key(str(env_path), "DDAY_ENABLED", str(settings.get("dday", True)))

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    filename = f"{_cache['next_day'].strftime('%Y%m%d')}.png"
    png_path = output_dir / filename

    # Base64 디코딩 후 파일 저장
    base64_data = data_url.split(",")[1]
    image_data = base64.b64decode(base64_data)
    with open(png_path, "wb") as f:
        f.write(image_data)

    # 클립보드에 복사
    copy_png_to_clipboard(png_path)

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "url": f"/output/{filename}",
        }
    )


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(str(Path.cwd() / "output"), filename)


@app.route("/api/data")
def get_data():
    """data.json 원본 반환."""
    return jsonify(_cache.get("data", {}))


@app.route("/api/data", methods=["PUT"])
def update_data():
    """data.json 저장 + 캐시 갱신."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    # $schema 보존
    body.setdefault("$schema", "./data.schema.json")

    # manual_meal: data.json에는 저장하지 않고 캐시에만 반영 (세션 한정)
    manual_meal = body.pop("manual_meal", None)

    # 파일 저장
    data_path = Path("data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=4)
        f.write("\n")

    old_next_day = _cache.get("next_day")

    # 휴일 재계산
    raw_holidays = body.get("school_holidays", [])
    if isinstance(raw_holidays, dict):
        school_holidays = raw_holidays
    else:
        school_holidays = {h["date"]: h["name"] for h in raw_holidays if "date" in h and "name" in h}

    today, next_day = _get_next_school_day(school_holidays)
    next_dt = datetime(next_day.year, next_day.month, next_day.day)
    today_dt = datetime(today.year, today.month, today.day)
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

    # 시간표 재로드
    timetable_obj = Timetable.load_timetable(body)
    timetable = timetable_obj.get_timetable(next_dt)

    # D-Day 재로드 (생성일 기준)
    dday_events = load_dday_events(today_dt, body)

    # 날짜가 바뀌었으면 급식 재조회
    old_school_start_hour = _cache.get("school_start_hour", 9)
    new_school_start_hour = body.get("school_start_hour", 9)
    if not isinstance(new_school_start_hour, int) or not (1 <= new_school_start_hour <= 23):
        new_school_start_hour = 9
    if next_day != old_next_day:
        _cache["school_meal"] = SchoolMeal.fetch_school_meal(next_dt)

    # manual_meal이 전달된 경우 캐시에 반영 (날짜 재조회 이후에 적용)
    if manual_meal is not None:
        menus = [m.strip() for m in (manual_meal.get("menus") or []) if str(m).strip()]
        if menus:
            _cache["school_meal"] = SchoolMeal(
                menus=menus,
                calories=manual_meal.get("calories", "").strip(),
            )
        else:
            # 메뉴를 모두 비운 경우: 급식 없음으로 처리
            _cache["school_meal"] = None

    # 날짜 또는 등교시간이 바뀌었으면 날씨 재조회
    if next_day != old_next_day or new_school_start_hour != old_school_start_hour:
        _cache["weather"] = Weather.fetch_weather(next_dt, school_hour=new_school_start_hour)

    _cache.update(
        {
            "data": body,
            "today": today,
            "today_dt": today_dt,
            "next_day": next_day,
            "next_dt": next_dt,
            "today_str": f"{today.year}. {today.month:02d}. {today.day:02d} ({weekday_kr[today.weekday()]})",
            "next_day_str": f"{next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
            "timetable": timetable,
            "dday_events": dday_events,
            "school_start_hour": new_school_start_hour,
        }
    )

    return jsonify({"success": True, "date_changed": next_day != old_next_day})


@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    """서버 종료 요청 처리."""

    def kill_server():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=kill_server, daemon=True).start()
    return jsonify({"success": True})


# ── 서버 실행 ─────────────────────────────────────────────────────


def run_web(host: str = "127.0.0.1", port: int = 5000) -> None:
    """데이터 로드(progress) → 웹 서버 시작 → 브라우저 자동 열기."""
    from rich.console import Console
    from rich.text import Text

    console = Console(highlight=False)

    # ── 헬퍼 ──
    def _step(label: str, detail: str = "") -> None:
        t = Text()
        t.append("  ✓ ", style="green")
        t.append(label, style="#AAAAAA")
        if detail:
            t.append(f" {detail}", style="white")
        console.print(t)

    def _skip(label: str) -> None:
        console.print(f"  [#AAAAAA]  - {label}[/#AAAAAA]")

    # ── 헤더 ──
    console.print()
    h = Text()
    h.append("  📋 알림장 웹 에디터", style="bold white")
    console.print(h)
    console.print()

    # ── 1. 기본 데이터 ──
    data = load_data()

    raw_holidays = data.get("school_holidays", [])
    if isinstance(raw_holidays, dict):
        school_holidays = raw_holidays
    else:
        school_holidays = {h["date"]: h["name"] for h in raw_holidays if "date" in h and "name" in h}

    today, next_day = _get_next_school_day(school_holidays)
    next_dt = datetime(next_day.year, next_day.month, next_day.day)
    today_dt = datetime(today.year, today.month, today.day)
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

    _step(
        "날짜 계산",
        f"{next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
    )

    # ── 2. 시간표 ──
    timetable_obj = Timetable.load_timetable(data)
    timetable = timetable_obj.get_timetable(next_dt)
    _step("시간표", f"{len(timetable)}교시")

    # ── 3. 급식 (항상 시도) ──
    school_meal = None
    with console.status("  ⏳ 급식 정보 조회 중...", spinner="dots"):
        school_meal = SchoolMeal.fetch_school_meal(next_dt)
    if school_meal:
        _step("급식", school_meal.calories)
    else:
        _skip("급식 정보 없음")

    # ── 4. 날씨 (항상 시도) ──
    school_start_hour = data.get("school_start_hour", 9)
    if not isinstance(school_start_hour, int) or not (1 <= school_start_hour <= 23):
        school_start_hour = 9
    weather = None
    with console.status("  ⏳ 날씨 정보 조회 중...", spinner="dots"):
        weather = Weather.fetch_weather(next_dt, school_hour=school_start_hour)
    if weather:
        _step("날씨", f"{weather.emoji} {weather.temp}° {weather.description}")
    else:
        _skip("날씨 정보 없음")

    # ── 5. D-Day (생성일 기준) ──
    dday_events = load_dday_events(today_dt, data)
    if dday_events:
        _step("D-Day", f"{len(dday_events)}개")
    else:
        _skip("D-Day 이벤트 없음")

    # ── 설정 (초기 토글 상태만) ──
    meal_on = os.getenv("SCHOOL_MEAL_ENABLED", "True").strip().lower() in ("true", "1")
    weather_on = os.getenv("WEATHER_ENABLED", "True").strip().lower() in ("true", "1")
    dday_on = os.getenv("DDAY_ENABLED", "True").strip().lower() in ("true", "1")

    # ── 캐시 저장 ──
    _cache.update(
        {
            "data": data,
            "today": today,
            "today_dt": today_dt,
            "next_day": next_day,
            "next_dt": next_dt,
            "today_str": f"{today.year}. {today.month:02d}. {today.day:02d} ({weekday_kr[today.weekday()]})",
            "next_day_str": f"{next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
            "timetable": timetable,
            "school_meal": school_meal,
            "weather": weather,
            "dday_events": dday_events,
            "school_start_hour": school_start_hour,
            "settings": {
                "meal": meal_on,
                "weather": weather_on,
                "dday": dday_on,
            },
        }
    )

    # ── 준비 완료 ──
    console.print()
    console.print("  [green]✅ 준비 완료![/green]")
    console.print(f"  [#AAAAAA]http://{host}:{port}[/#AAAAAA]")
    console.print("  [#AAAAAA]Ctrl+C로 종료[/#AAAAAA]\n")

    # 브라우저 열기 (서버 바인딩 후 살짝 대기)
    def _open_browser():
        time.sleep(0.8)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()

    # Flask/werkzeug 로그 및 배너 억제 (터미널 깔끔하게)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import flask.cli

    flask.cli.show_server_banner = lambda *_: None

    app.run(host=host, port=port, debug=False)
