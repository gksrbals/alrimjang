import os
import re
import requests
from dataclasses import dataclass
from datetime import datetime


class DDISH_NM:
    """급식 요리명 파싱 (알레르기 번호 자동 제거)"""

    def __init__(self, original: str):
        self.original = original
        self._parsed = self._parse(original)

    def _parse(self, original: str) -> list[str]:
        items = original.split("<br/>")
        cleaned = []
        for item in items:
            # 알레르기 번호 제거: "된장찌개(5.6.9.)" → "된장찌개"
            item = re.sub(r"\s*\([\d.]+\)", "", item).strip()
            if item:
                cleaned.append(item)
        return cleaned

    def __str__(self) -> str:
        return "\n".join(self._parsed)

    def __iter__(self):
        return iter(self._parsed)

    def __len__(self) -> int:
        return len(self._parsed)


@dataclass(frozen=True)
class SchoolMeal:
    menus: list[str]  # 메뉴 목록
    calories: str  # 칼로리 정보 (예: "871.8 Kcal")

    @staticmethod
    def fetch_school_meal(date: datetime) -> "SchoolMeal | None":
        """
        NEIS API로 급식 정보 조회.
        급식 없는 날(공휴일·방학 등) 또는 API 오류 시 None 반환.
        """
        try:
            url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
            params = {
                "KEY": os.getenv("NEIS_API_KEY"),
                "Type": "json",
                "pIndex": 1,
                "pSize": 10,
                "ATPT_OFCDC_SC_CODE": os.getenv("ATPT_OFCDC_SC_CODE"),
                "SD_SCHUL_CODE": os.getenv("SD_SCHUL_CODE"),
                "MLSV_YMD": date.strftime("%Y%m%d"),
                "MMEAL_SC_CODE": "2",  # 2 = 중식
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 급식 데이터 없는 경우 (공휴일·방학)
            if "mealServiceDietInfo" not in data:
                return None

            result = data["mealServiceDietInfo"]
            code = result[0]["head"][1]["RESULT"]["CODE"]
            if code != "INFO-000":
                return None

            row = result[1]["row"][0]
            ddish = DDISH_NM(row["DDISH_NM"])
            cal = row.get("CAL_INFO", "").replace(" Kcal", " kcal")

            return SchoolMeal(menus=list(ddish), calories=cal)

        except Exception:
            return None
