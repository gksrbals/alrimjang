import argparse
import sys

# Windows 터미널 인코딩을 UTF-8로 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from alrimjang.web import run_web


def main() -> None:
    parser = argparse.ArgumentParser(
        description="📋 알림장 — 학급 알림장 웹 에디터",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="웹 에디터 포트 (기본: 5000)",
    )
    args = parser.parse_args()

    run_web(port=args.port)


if __name__ == "__main__":
    main()
