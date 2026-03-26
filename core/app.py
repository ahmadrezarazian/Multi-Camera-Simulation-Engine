from flask import Flask
from .state import AppState
from render.renderer import Renderer
from stream.mjpeg_stream import MjpegStreamer
from web.routes import register_routes


class MultiCamSimApp:
    def __init__(self):
        self.state = AppState()
        self.flask_app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')
        self.flask_app.config['APP_VERSION'] = self.state.settings['version']

        self.renderer = Renderer(self.state.settings) # Pass initial settings
        self.streamer = MjpegStreamer(self.renderer, app_state=self.state) # Pass app_state for dynamic settings
        self.streamer.start_rendering()

        register_routes(self.flask_app, self.streamer)

    def run(self):
        app_cfg = self.state.settings['app']
        self.flask_app.run(host=app_cfg['host'], port=app_cfg['port'], threaded=True)
