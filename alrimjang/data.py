import json
from pathlib import Path
from typing import Any, Dict

def load_data() -> Dict[str, Any]:
    """data.json을 우선 로드하고, 없으면 data.example.json을 로드합니다."""
    for p in ["data.json", "data.example.json"]:
        path = Path(p)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return {}
