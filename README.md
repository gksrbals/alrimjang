# 📋 알림장

학급 알림장 이미지를 자동으로 생성하는 CLI 도구입니다.

공지사항을 입력하면 시간표·급식·날씨·D-Day를 자동으로 조합해 깔끔한 이미지(PNG)로 만들고 클립보드에 복사합니다.

---

## 주요 기능

| 기능 | 데이터 소스 | 설정 |
|------|-----------|------|
| 🗓️ 시간표 | `data.json` (로컬) | — |
| 📢 공지사항 | 직접 입력 (마크다운 지원) | — |
| 🍱 급식 | NEIS API | `SCHOOL_MEAL_ENABLED` |
| ☀️ 날씨 | Open-Meteo API (등교 09시 기준) | `WEATHER_ENABLED` |
| 🎯 D-Day | `data.json` (로컬) | `DDAY_ENABLED` |

---

## 실행 방법

```bash
uv run main.py
```

### 요구사항

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Chrome 또는 Edge 브라우저 (이미지 렌더링용)

---

## 공지사항 입력

실행하면 멀티라인 에디터가 나타납니다.

### 조작법

| 키 | 동작 |
|---|---|
| `Enter` | 다음 줄 |
| `↑↓←→` | 커서 이동 |
| `Backspace` / `Delete` | 삭제 |
| `Ctrl+Z` | 되돌리기 |
| **`Ctrl+D`** | **입력 완료** |
| `Ctrl+C` | 취소 후 종료 |
| **`F1`** | **급식 섹션 켜기/끄기** |
| **`F2`** | **날씨 섹션 켜기/끄기** |
| **`F3`** | **D-Day 섹션 켜기/끄기** |

> 💡 **Tip:** 하단 툴바에서 ON/OFF 상태를 실시간으로 확인하고 토글할 수 있습니다. 변경된 상태는 다음 실행 시에도 자동으로 유지됩니다 (`.env` 파일 자동 저장).

### 마크다운 문법

| 입력 | 결과 |
|------|------|
| `**텍스트**` | **굵은 흰색** 글씨 |
| `*텍스트*` | *기울어진 회색* 글씨 |
| `~~텍스트~~` | ~~취소선~~ 처리 |
| `[중요] 텍스트` | 🔴 중요 배지 + 굵은 글씨 |
| `---` | 구분선 |

### 입력 예시

```
**내일 체육복 지참 필수**
*수행평가 제출 마감 D-1*
---
[중요] 현장학습 동의서 제출
도서관 반납일 확인
~~청소 당번: 3모둠 완료~~
```

---

## 설정

### 환경변수 (`.env`)

`.env.example`을 복사해 `.env`로 만들고 값을 채웁니다.

```env
# NEIS 급식 API
NEIS_API_KEY=           # https://open.neis.go.kr 에서 발급
ATPT_OFCDC_SC_CODE=     # 시도교육청코드
SD_SCHUL_CODE=          # 행정표준코드
SCHOOL_MEAL_ENABLED=True # True = 급식 섹션 표시 / False = 급식 섹션 숨김 (F1키로 변경 시 자동 저장)

# ──────────────────────────────
# Open-Meteo 날씨 (학교 위치 좌표)
# ──────────────────────────────
# 학교 좌표 (Google Maps에서 확인 가능)
WEATHER_LAT=0.0
WEATHER_LON=0.0
# True = 표시 / False = 숨김 (F2키로 변경 시 자동 저장)
WEATHER_ENABLED=True

# ──────────────────────────────
# D-Day 카운트다운
# ──────────────────────────────
# True = 표시 / False = 숨김 (F3키로 변경 시 자동 저장)
DDAY_ENABLED=True
```

---

### 데이터 설정 (`data.json`)

기본 제공되는 `data.example.json`을 복사하여 `data.json` 파일을 생성한 후 설정합니다. 이 파일은 Git 추적에서 제외되므로 자유롭게 수정하셔도 됩니다.

```json
{
    "$schema": "./data.schema.json",
    "dday": [
        {"name": "기말고사", "date": "2026-07-01", "emoji": "📝"},
        {"name": "여름방학", "date": "2026-07-18", "emoji": "🏖️"}
    ],
    "school_holidays": [
        {"date": "2026-05-28", "name": "개교기념일"},
        {"date": "2026-06-01", "name": "재량휴업일"}
    ],
    "timetable": {
        "monday":    ["독서", "생과", "이동D", "이동F", "영독작", "확통"],
        "tuesday":   ["영독작", "이동H", "운건", "진로", "이동F", "확통", "독서"],
        "wednesday": ["이동I", "이동E", "심국", "이동H", "창체", "창체"],
        "thursday":  ["이동I", "영독작", "심국", "확통", "운건", "독서", "이동D"],
        "friday":    ["영독작", "독서", "이동D", "이동E", "생과", "심국"],
        "overrides": [
            {"date": "2026-06-10", "subjects": ["국어", "수학", "영어", "자습", "자습", "자습"]}
        ]
    }
}
```

- **dday**: 지난 이벤트는 자동으로 숨겨지며, 남은 일수에 따라 색상이 자동 변경됩니다. (🔴 3일 이하 / 🟡 7일 이하 / 🔵 8일 이상)
- **school_holidays**: 국가 공휴일은 자동으로 처리되므로 등록할 필요가 없습니다. 개교기념일 등 학교 자체 휴일만 `YYYY-MM-DD` 형식으로 등록하세요. 등록된 날짜는 건너뛰고 다음 등교일 기준으로 알림장을 작성합니다.
- **timetable**: 기본 요일별 시간표를 설정합니다. 특정 날짜에 시간표가 변경(예: 시험)되는 경우 `overrides`에 날짜(`YYYY-MM-DD`)를 키로 하여 시간표를 덮어씌울 수 있습니다.

---

## 결과물

- **이미지 파일**: `output/YYYYMMDD.png`로 저장
- **클립보드**: 자동 복사 → `Ctrl+V`로 바로 붙여넣기

---

## 프로젝트 구조

```
alrimjang/
├── main.py                  # 진입점 (2단계 CLI 흐름)
├── data.example.json        # 데이터 템플릿
├── data.schema.json         # JSON 스키마
├── .env                     # 환경변수 설정
├── output/                  # 생성된 이미지
│   └── 20260522.png
└── alrimjang/
    ├── __init__.py
    ├── cli.py               # CLI UI (rich + prompt_toolkit)
    ├── data.py              # 데이터 로더 (data.json 파싱)
    ├── renderer.py          # HTML→PNG 렌더링, 크롭, 라운드 마스크
    ├── school_meal.py       # NEIS 급식 API
    ├── weather.py           # Open-Meteo 날씨 API
    ├── timetable.py         # 시간표 모델
    ├── dday.py              # D-Day 계산 로직
    └── templates/
        └── notice.html.j2   # Jinja2 HTML 템플릿
```

---

## 라이선스

[MIT](LICENSE)
