from pathlib import Path
import json

class AppState:
    def __init__(self):
        settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"

        default_settings = {
            "width": 640,
            "height": 480,
            "fps": 30,
            "camera": {
                "radius": 5.0,
                "speed": 0.5
            }
        }

        if not settings_path.exists():
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)
            self.settings = default_settings
        else:
            with open(settings_path, "r", encoding="utf-8") as f:
                self.settings = json.load(f)