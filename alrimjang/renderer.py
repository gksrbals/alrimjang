import io
import re
from datetime import datetime
from pathlib import Path

import win32clipboard
from PIL import Image, ImageDraw
from jinja2 import Environment, FileSystemLoader
from html2image import Html2Image
from rich.console import Console

from .school_meal import SchoolMeal
from .weather import Weather
from .dday import DdayEvent

console = Console(highlight=False)

# 템플릿 디렉토리
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_JINJA_ENV = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


# ── 마크다운 파싱 ──────────────────────────────────────────────────


def _parse_notices(lines: list[str]) -> list[dict]:
    """
    공지사항 줄 목록을 타입별 dict 목록으로 변환.

    타입:
      divider      → --- 구분선
      important    → [중요] 텍스트
      bold         → **텍스트**
      italic       → *텍스트*
      strikethrough→ ~~텍스트~~
      normal       → 일반 텍스트
    """
    result = []
    for line in lines:
        stripped = line.strip()

        if stripped == "---":
            result.append({"type": "divider", "text": ""})
            continue

        # [중요] 태그 확인 (볼드와 중복 적용 가능)
        is_important = bool(re.match(r"^\[중요\]", stripped))
        text = re.sub(r"^\[중요\]\s*", "", stripped) if is_important else stripped

        # **볼드** 추출
        bold_match = re.fullmatch(r"\*\*(.+)\*\*", text)
        # *이탤릭* 추출 (1글자 이상 모두 커버, bold_match 이후라 ** 충돌 없음)
        italic_match = re.fullmatch(r"\*([^*]+)\*", text)
        # ~~취소선~~ 추출
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


def _render_html(
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


def _copy_to_clipboard(png_path: Path) -> None:
    img = Image.open(png_path).convert("RGBA")
    # 투명 배경 → 검정으로 합성 (클립보드 BMP는 알파 미지원)
    bg = Image.new("RGB", img.size, (0, 0, 0))
    bg.paste(img, mask=img.split()[3])  # 알파 채널을 마스크로 사용
    output = io.BytesIO()
    bg.save(output, "BMP")
    bmp_data = output.getvalue()[14:]
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
    win32clipboard.CloseClipboard()


# ── 이미지 자동 크롭 ──────────────────────────────────────────────


def _autocrop(png_path: Path) -> None:
    """
    이미지 하단 여백 자동 제거.
    중앙 픽셀(x=width/2)에서 카드 배경색이 끝나는 행을 정밀하게 탐색.
    """
    if not png_path.exists():
        return
    img = Image.open(png_path).convert("RGB")
    pixels = img.load()
    width, height = img.size
    cx = width // 2  # 카드 중앙 x 좌표
    body_bg = (10, 10, 10)  # body 배경: #0a0a0a

    last_row = 0
    for y in range(height - 1, -1, -1):
        if pixels[cx, y] != body_bg:
            last_row = y
            break

    crop_height = min(last_row + 1, height)
    img.crop((0, 0, width, crop_height)).save(png_path)


def _apply_rounded_alpha(png_path: Path, radius: int = 12) -> None:
    """
    PNG에 rounded(12px) 모양 알파 마스크 적용.
    4x 슈퍼샘플링으로 안티앨리어싱된 부드러운 모서리를 생성.
    """
    img = Image.open(png_path).convert("RGBA")
    w, h = img.size

    # 4배 크기로 마스크를 그린 뒤 축소 → 부드러운 안티앨리어싱
    scale = 4
    big = Image.new("L", (w * scale, h * scale), 0)
    draw = ImageDraw.Draw(big)
    draw.rounded_rectangle(
        [(0, 0), (w * scale, h * scale)],
        radius=radius * scale,
        fill=255,
    )
    mask = big.resize((w, h), Image.LANCZOS)

    img.putalpha(mask)
    img.save(png_path)  # RGBA PNG로 저장


# ── 브라우저 감지 ──────────────────────────────────────────────────


def _make_hti(output_path: str) -> Html2Image:
    """
    Chrome → Edge 순서로 브라우저를 자동 탐색해 Html2Image 인스턴스 반환.
    둘 다 없으면 FileNotFoundError 대신 친절한 안내 메시지를 출력하고 종료.
    """
    flags = ["--hide-scrollbars"]

    # 1) Chrome 시도 (자동 감지)
    try:
        return Html2Image(output_path=output_path, custom_flags=flags)
    except FileNotFoundError:
        pass

    # 2) Edge 시도
    try:
        return Html2Image(browser="edge", output_path=output_path, custom_flags=flags)
    except FileNotFoundError:
        pass

    # 3) 둘 다 없으면 안내 후 종료
    console.print(
        "[bold red]오류:[/bold red] Chrome 또는 Edge 브라우저를 찾을 수 없습니다.\n"
        "  - Chrome 설치: https://www.google.com/chrome\n"
        "  - Edge 는 Windows 에 기본 내장되어 있습니다."
    )
    raise SystemExit(1)


# ── 메인 진입 ────────────────────────────────────────────────────


def render_and_export(
    today: datetime,
    next_day: datetime,
    timetable: list[str],
    school_meal: "SchoolMeal | None",
    weather: "Weather | None",
    raw_notices: list[str],
    dday_events: list["DdayEvent"] | None = None,
) -> None:
    # 1. 마크다운 파싱
    notices = _parse_notices(raw_notices)

    # 2. HTML 생성
    html = _render_html(
        today, next_day, timetable, school_meal, weather, notices, dday_events or []
    )

    # 3. output 폴더 준비
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    filename = f"{next_day.strftime('%Y%m%d')}.png"

    # 4. html2image → PNG (Chrome 없으면 Edge 자동 폴백)
    hti = _make_hti(str(output_dir))
    hti.screenshot(
        html_str=html,
        save_as=filename,
        size=(800, 3000),  # 넉넉한 높이 (공지 多 경우 대비)
    )

    png_path = output_dir / filename

    # 5. 하단 여백 크롭 (body padding=0이므로 카드 바로 아래에서 자름)
    _autocrop(png_path)

    # 6. 알파 마스크 적용 (rounded 12px → 투명 PNG)
    _apply_rounded_alpha(png_path, radius=12)

    # 7. 클립보드 복사 (알파 채널 → 검정 배경으로 합성 후 BMP 전송)
    _copy_to_clipboard(png_path)
