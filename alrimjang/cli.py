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
        "prompt": "#888888",
        "bottom-toolbar": "bg:#111111 #555555",
        "bottom-toolbar.text": "#888888",
    }
)


def _toolbar():
    return HTML(
        '<style bg="#111111" fg="#444444">│</style> '
        "<b>Enter</b>=줄바꿈  "
        '<style bg="#111111" fg="#444444">│</style> '
        "<b>↑↓</b>=줄이동  "
        '<style bg="#111111" fg="#444444">│</style> '
        "<b>Ctrl+D</b>=완료  "
        '<style bg="#111111" fg="#444444">│</style> '
        "<b>Ctrl+C</b>=취소"
    )


# ── 마크다운 가이드 패널 ────────────────────────────────────────────


def _build_guide_panel() -> Panel:
    """공지사항 입력 가이드를 예쁜 패널로 렌더링."""
    guide = Table.grid(padding=(0, 2))
    guide.add_column(style="dim white", justify="right", min_width=12)
    guide.add_column()

    guide.add_row("**텍스트**", Text("볼드 처리", style="bold white"))
    guide.add_row("*텍스트*", Text("이탤릭 처리", style="italic #CCCCCC"))
    guide.add_row("~~텍스트~~", Text("취소선 처리", style="strike dim"))
    guide.add_row("[중요] 텍스트", Text("중요 배지", style="bold #FF6B6B"))
    guide.add_row("---", Text("구분선", style="dim"))

    return Panel(
        guide,
        title="[bold]📢 공지사항 입력[/bold]",
        subtitle="[dim]마크다운 문법 지원[/dim]",
        border_style="#333333",
        padding=(1, 2),
    )


# ── 헤더 ────────────────────────────────────────────────────────────


def print_header(today, next_day) -> None:
    """앱 시작 헤더 + 날짜 정보를 출력."""
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

    title = Text()
    title.append("📋", style="")
    title.append("  알 림 장", style="bold white")
    title.append("  v0.1.0\n", style="dim #555555")
    title.append(
        f"   {today.year}. {today.month:02d}. {today.day:02d} ({weekday_kr[today.weekday()]})",
        style="dim",
    )
    title.append("  →  ", style="dim #444444")
    title.append(
        f"{next_day.month}월 {next_day.day}일 {weekday_kr[next_day.weekday()]}요일",
        style="bold #629EE4",
    )
    title.append(" 알림장 작성", style="dim")

    console.print(
        Panel(
            title,
            border_style="#333333",
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


def get_user_input() -> list[str]:
    """
    prompt_toolkit 멀티라인 에디터로 공지사항 입력.

    - 방향키(↑↓←→), Home/End, Backspace/Delete 완전 지원
    - Enter       → 새 줄
    - Ctrl+D      → 입력 완료
    - Ctrl+C      → 취소 (빈 목록 반환)

    지원 마크다운:
      **텍스트**    → 볼드
      *텍스트*      → 이탤릭
      ~~텍스트~~    → 취소선
      [중요] 텍스트  → 빨간 배지
      ---           → 구분선
    """
    console.print(_build_guide_panel())

    # 커스텀 키 바인딩
    kb = KeyBindings()

    @kb.add("c-d")
    def _submit(event):
        """Ctrl+D → 완료"""
        event.app.exit(result=event.app.current_buffer.text)

    @kb.add("c-c")
    def _cancel(event):
        """Ctrl+C → 취소"""
        event.app.exit(result=None)

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
    except KeyboardInterrupt, EOFError:
        result = None

    console.print()

    if not result:
        return []

    # 빈 줄 제거 (앞뒤만, 중간 빈 줄은 구분선으로 활용 가능하므로 유지)
    lines = result.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return lines
