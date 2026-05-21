import tomllib
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

console = Console(highlight=False)

# ── prompt_toolkit 테마 ────────────────────────────────────────────

_PT_STYLE = Style.from_dict(
    {
        "prompt": "#BBBBBB",
        "bottom-toolbar": "#AAAAAA",
        "bottom-toolbar.text": "#CCCCCC",
    }
)


# ── 마크다운 가이드 패널 ────────────────────────────────────────────


def _build_guide_panel() -> Panel:
    """공지사항 입력 가이드를 예쁜 패널로 렌더링."""
    guide = Table.grid(padding=(0, 2))
    guide.add_column(style="white", justify="right", min_width=12)
    guide.add_column()

    guide.add_row("**텍스트**", Text("볼드 처리", style="bold white"))
    guide.add_row("*텍스트*", Text("이탤릭 처리", style="italic #E0E0E0"))
    guide.add_row("~~텍스트~~", Text("취소선 처리", style="strike #AAAAAA"))
    guide.add_row("[중요] 텍스트", Text("중요 배지", style="bold #FF6B6B"))
    guide.add_row("---", Text("구분선", style="#AAAAAA"))

    return Panel(
        guide,
        title="[bold]📢 공지사항 입력[/bold]",
        subtitle="[#AAAAAA]마크다운 문법 지원[/#AAAAAA]",
        border_style="#777777",
        padding=(1, 2),
    )


def _get_project_version() -> str:
    """pyproject.toml에서 버전을 읽어옵니다."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


# ── 헤더 ────────────────────────────────────────────────────────────


def print_header(today, next_day) -> None:
    """앱 시작 헤더 + 날짜 정보를 출력."""
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

    title = Text()
    title.append("📋", style="")
    title.append("  알 림 장", style="bold white")
    
    version_str = _get_project_version()
    title.append(f"  v{version_str}\n", style="#888888")
    
    title.append(
        f"   {today.year}. {today.month:02d}. {today.day:02d} ({weekday_kr[today.weekday()]})",
        style="#AAAAAA",
    )
    title.append("  →  ", style="#888888")
    title.append(
        f"{next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
        style="bold #629EE4",
    )
    title.append(" 알림장 작성", style="#AAAAAA")

    console.print(
        Panel(
            title,
            border_style="#777777",
            padding=(1, 2),
        )
    )


# ── 진행 헤더 (clear 후 표시) ────────────────────────────────────────


def print_progress_header(next_day) -> None:
    """clear 후 표시되는 간결한 헤더."""
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

    header = Text()
    header.append("  📋 알림장", style="bold white")
    header.append(
        f" — {next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
        style="#629EE4",
    )
    console.print(header)
    console.print()


# ── 공지사항 입력 ────────────────────────────────────────────────────


def get_user_input(
    meal_on: bool = True,
    weather_on: bool = True,
    dday_on: bool = True,
) -> tuple[list[str] | None, bool, bool, bool]:
    """
    prompt_toolkit 멀티라인 에디터로 공지사항 입력.
    F1, F2, F3 키를 통해 설정(급식, 날씨, D-Day)을 토글할 수 있음.
    """
    console.print(_build_guide_panel())

    state = {
        "meal": meal_on,
        "weather": weather_on,
        "dday": dday_on,
    }

    def _toolbar():
        meal_color = "#629EE4" if state["meal"] else "#888888"
        weather_color = "#629EE4" if state["weather"] else "#888888"
        dday_color = "#629EE4" if state["dday"] else "#888888"

        meal_text = "ON" if state["meal"] else "OFF"
        weather_text = "ON" if state["weather"] else "OFF"
        dday_text = "ON" if state["dday"] else "OFF"

        return HTML(
            '<style fg="#777777">│</style> '
            "<b>Enter</b>=줄바꿈  "
            '<style fg="#777777">│</style> '
            "<b>Ctrl+D</b>=완료  "
            '<style fg="#777777">│</style> '
            "<b>Ctrl+C</b>=취소  "
            '<style fg="#777777">│</style> '
            f'<b>F1</b> 급식:<style fg="{meal_color}">{meal_text}</style>  '
            f'<b>F2</b> 날씨:<style fg="{weather_color}">{weather_text}</style>  '
            f'<b>F3</b> D-Day:<style fg="{dday_color}">{dday_text}</style>'
        )

    kb = KeyBindings()

    @kb.add("c-d")
    def _submit(event):
        event.app.exit(result=event.app.current_buffer.text)

    @kb.add("c-c")
    def _cancel(event):
        event.app.exit(result=None)

    @kb.add("f1")
    def _toggle_meal(event):
        state["meal"] = not state["meal"]
        event.app.invalidate()

    @kb.add("f2")
    def _toggle_weather(event):
        state["weather"] = not state["weather"]
        event.app.invalidate()

    @kb.add("f3")
    def _toggle_dday(event):
        state["dday"] = not state["dday"]
        event.app.invalidate()

    session: PromptSession = PromptSession(
        history=InMemoryHistory(),
        style=_PT_STYLE,
        key_bindings=kb,
        multiline=True,
        bottom_toolbar=_toolbar,
        prompt_continuation=lambda width, line_number, wrap_count: HTML(
            f"<prompt>  {line_number + 1:>2}: </prompt>"
        ),
    )

    try:
        result = session.prompt(HTML("<prompt>   1: </prompt>"))
    except (KeyboardInterrupt, EOFError):
        result = None

    console.print()

    if result is None:
        return None, state["meal"], state["weather"], state["dday"]

    # 빈 줄 제거
    lines = result.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return lines, state["meal"], state["weather"], state["dday"]
