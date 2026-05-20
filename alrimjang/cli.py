from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

console = Console(highlight=False)

# prompt_toolkit 스타일
_PT_STYLE = Style.from_dict(
    {
        "prompt": "#888888",
        "bottom-toolbar": "bg:#1a1a1a #555555",
    }
)

_TOOLBAR_TEXT = HTML(
    "<b>Enter</b>=줄바꿈  "
    "<b>↑↓</b>=줄이동  "
    "<b>Backspace/Del</b>=삭제  "
    "<b>Ctrl+D</b>=완료  "
    "<b>Ctrl+C</b>=취소"
)


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
    guide = Text()
    guide.append("  마크다운: ", style="dim")
    guide.append("**볼드**", style="bold white")
    guide.append("  ")
    guide.append("*이탤릭*", style="italic")
    guide.append("  ")
    guide.append("~~취소선~~", style="dim white strike")
    guide.append("  ")
    guide.append("[중요]", style="bold red")
    guide.append("  ")
    guide.append("---  구분선", style="dim")
    guide.append("\n  Ctrl+D 로 완료", style="dim")

    console.print(
        Panel(guide, title="[bold]📢  공지사항 입력[/bold]", border_style="dim")
    )

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
        bottom_toolbar=_TOOLBAR_TEXT,
        prompt_continuation=lambda width, line_number, wrap_count: HTML(
            f"<prompt>  {line_number + 1:>2}: </prompt>"
        ),
    )

    try:
        result = session.prompt(HTML("<prompt>   1: </prompt>"))
    except (KeyboardInterrupt, EOFError):
        result = None

    console.print()

    if not result:
        return []

    # 빈 줄 제거 (앞뒤만, 중간 빈 줄은 구분선으로 활용 가능하므로 유지)
    lines = result.splitlines()
    # 앞뒤 공백 줄 트림
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return lines
