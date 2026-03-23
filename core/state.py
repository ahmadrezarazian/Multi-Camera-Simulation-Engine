from pathlib import Path
import json

class AppState:
    def __init__(self):
        self.settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
        self.load()

    def load(self):
        default_settings = {
            "app": {
                "host": "127.0.0.1",
                "port": 5000,
                "fps": 30,
                "width": 1280,
                "height": 720
            },
            "scene": {
                "Name": "Simulation Scene",
                "Ambient": 0.3,
                "BackgroundColor": [0.1, 0.1, 0.6],
                "Light": {
                    "Name": "Main Light",
                    "Type": "directional",
                    "Position": [1.0, 2.0, 3.0],
                    "Target": [0.0, 0.0, 0.0],
                    "DiffuseColor": [1.0, 1.0, 1.0],
                    "SpecularColor": [1.0, 1.0, 1.0],
                    "Power": 1.0
                },
                "Camera": {
                    "Name": "Orbit Camera",
                    "ViewType": "Mono",
                    "MotionType": "AutoRotateOnTarget",
                    "MotionSpeed": 0.5,
                    "Position": [4.0, 2.0, 4.0],
                    "Target": [0.0, 0.0, 0.0],
                    "Up": [0.0, 1.0, 0.0],
                    "FOV": 45.0,
                    "NearClip": 0.1,
                    "FarClip": 100.0,
                    "AspectRatio": 1.77
                }
            }
        }

        if not self.settings_path.exists():
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)
            self.settings = default_settings
        else:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                self.settings = json.load(f)

    def reload(self):
        self.load()
