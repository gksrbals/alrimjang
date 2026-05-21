import os
import requests
from dataclasses import dataclass
from datetime import datetime


# WMO 날씨 코드 → (이모지, 한국어 설명)
WMO_CODE_MAP: dict[int, tuple[str, str]] = {
    0: ("☀️", "맑음"),
    1: ("🌤️", "대체로 맑음"),
    2: ("⛅", "구름 많음"),
    3: ("☁️", "흐림"),
    45: ("🌫️", "안개"),
    48: ("🌫️", "짙은 안개"),
    51: ("🌦️", "가벼운 이슬비"),
    53: ("🌦️", "이슬비"),
    55: ("🌧️", "강한 이슬비"),
    61: ("🌧️", "가벼운 비"),
    63: ("🌧️", "비"),
    65: ("🌧️", "강한 비"),
    71: ("🌨️", "가벼운 눈"),
    73: ("🌨️", "눈"),
    75: ("🌨️", "강한 눈"),
    77: ("🌨️", "싸락눈"),
    80: ("🌦️", "소나기"),
    81: ("🌧️", "강한 소나기"),
    82: ("⛈️", "폭우"),
    85: ("🌨️", "눈 소나기"),
    86: ("🌨️", "강한 눈 소나기"),
    95: ("⛈️", "뇌우"),
    96: ("⛈️", "우박 뇌우"),
    99: ("⛈️", "강한 우박 뇌우"),
}


@dataclass(frozen=True)
class Weather:
    emoji: str  # 날씨 이모지 (09시 기준)
    description: str  # 날씨 설명  (09시 기준)
    temp: int  # 09시 기온 (°C)
    max_temp: int  # 일 최고기온 (°C)
    min_temp: int  # 일 최저기온 (°C)
    rain_prob: int  # 강수확률 %, 09시 기준
    wind_speed: float  # 풍속 m/s,  09시 기준

    @staticmethod
    def fetch_weather(dt: datetime) -> "Weather | None":
        """
        Open-Meteo API로 날씨 조회 (무료, API 키 불필요).

        - 날씨 코드·기온·강수확률·풍속은 등교 시간(09:00) 기준 hourly 데이터 사용
        - 일 최고/최저기온은 daily 데이터 사용
        - 오류 시 None 반환
        """
        try:
            lat = os.getenv("WEATHER_LAT")
            lon = os.getenv("WEATHER_LON")
            if not lat or not lon:
                return None

            target_date = dt.strftime("%Y-%m-%d")
            target_hour = f"{target_date}T09:00"  # 등교 09시 슬롯

            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": [
                    "weathercode",
                    "temperature_2m",
                    "precipitation_probability",
                    "windspeed_10m",
                ],
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                ],
                "timezone": "Asia/Seoul",
                "forecast_days": 7,
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            hourly = data["hourly"]
            daily = data["daily"]

            # 09시 슬롯 인덱스
            if target_hour not in hourly["time"]:
                return None
            hi = hourly["time"].index(target_hour)

            # 일별 인덱스
            if target_date not in daily["time"]:
                return None
            di = daily["time"].index(target_date)

            code = hourly["weathercode"][hi]
            emoji, desc = WMO_CODE_MAP.get(code, ("🌡️", "날씨 정보 없음"))

            return Weather(
                emoji=emoji,
                description=desc,
                temp=round(hourly["temperature_2m"][hi]),
                max_temp=round(daily["temperature_2m_max"][di]),
                min_temp=round(daily["temperature_2m_min"][di]),
                rain_prob=hourly["precipitation_probability"][hi] or 0,
                wind_speed=round(hourly["windspeed_10m"][hi] / 3.6, 1),  # km/h → m/s
            )

        except Exception:
            return None
