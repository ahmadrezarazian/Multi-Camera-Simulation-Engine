from pathlib import Path
import json

class AppState:
    def __init__(self):
        self.settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
        self.load()

    def load(self):
        default_settings = {
            "version": "1.2.1",
            "app": {
                "host": "127.0.0.1",
                "port": 5000,
                "fps": 30,
                "width": 720,
                "height": 480
            },
            "scene": {
                "name": "Simulation Scene",
                "ambient": 0.3,
                "background_color": [0.1, 0.1, 0.6],
                "light": {
                    "name": "Main Light",
                    "type": "directional",
                    "position": [1.0, 2.0, 3.0],
                    "target": [0.0, 0.0, 0.0],
                    "diffuse_color": [1.0, 1.0, 1.0],
                    "specular_color": [1.0, 1.0, 1.0],
                    "power": 1.0
                },
                "camera": {
                    "name": "Orbit Camera",
                    "motion_type": "AutoRotateOnTarget",
                    "motion_speed": 0.5,
                    "motion_delay": 0.0,
                    "position": [4.0, 2.0, 4.0],
                    "target": [0.0, 0.0, 0.0],
                    "up": [0.0, 1.0, 0.0],
                    "fov": 45.0,
                    "near_clip": 0.1,
                    "far_clip": 100.0,
                    "aspect_ratio": 1.77,
                    "color_type": "RGB"
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
