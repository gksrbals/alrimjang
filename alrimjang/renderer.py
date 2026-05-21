import io
import re
from datetime import datetime
from pathlib import Path

import win32clipboard
from PIL import Image
from jinja2 import Environment, FileSystemLoader

from .school_meal import SchoolMeal
from .weather import Weather
from .dday import DdayEvent

# 템플릿 디렉토리
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_JINJA_ENV = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


# ── 마크다운 파싱 ──────────────────────────────────────────────────


def parse_notices(lines: list[str]) -> list[dict]:
    """
    공지사항 줄 목록을 타입별 dict 목록으로 변환.
    """
    result = []
    for line in lines:
        stripped = line.strip()

        if stripped == "---":
            result.append({"type": "divider", "text": ""})
            continue

        is_important = bool(re.match(r"^\[중요\]", stripped))
        text = re.sub(r"^\[중요\]\s*", "", stripped) if is_important else stripped

        bold_match = re.fullmatch(r"\*\*(.+)\*\*", text)
        italic_match = re.fullmatch(r"\*([^*]+)\*", text)
        strike_match = re.fullmatch(r"~~(.+)~~", text)

        if is_important:
            clean = bold_match.group(1) if bold_match else text
            result.append({"type": "important", "text": clean})
        elif bold_match:
            result.append({"type": "bold", "text": bold_match.group(1)})
        elif italic_match:
            result.append({"type": "italic", "text": italic_match.group(1)})
        elif strike_match:
            result.append({"type": "strikethrough", "text": strike_match.group(1)})
        else:
            result.append({"type": "normal", "text": text})

    return result


# ── HTML 렌더링 ───────────────────────────────────────────────────


def render_html(
    today: datetime,
    next_day: datetime,
    timetable: list[str],
    school_meal: "SchoolMeal | None",
    weather: "Weather | None",
    notices: list[dict],
    dday_events: list[DdayEvent],
) -> str:
    template = _JINJA_ENV.get_template("notice.html.j2")
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

    return template.render(
        today_str=f"{today.year}. {today.month:02d}. {today.day:02d} ({weekday_kr[today.weekday()]})",
        next_day_str=f"{next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
        timetable=timetable,
        school_meal=school_meal,
        weather=weather,
        notices=notices,
        dday_events=dday_events,
    )


# ── 클립보드 복사 ─────────────────────────────────────────────────


def copy_png_to_clipboard(png_path: Path) -> None:
    """PNG 이미지를 읽어서 윈도우 클립보드(BMP 포맷)로 복사합니다."""
    img = Image.open(png_path).convert("RGBA")
    # 투명 배경 → 검정으로 합성 (클립보드 BMP는 알파 미지원)
    bg = Image.new("RGB", img.size, (0, 0, 0))
    bg.paste(img, mask=img.split()[3])
    output = io.BytesIO()
    bg.save(output, "BMP")
    bmp_data = output.getvalue()[14:]
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
    win32clipboard.CloseClipboard()
