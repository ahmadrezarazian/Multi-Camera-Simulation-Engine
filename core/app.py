from flask import Flask
from .state import AppState
from render.renderer import Renderer
from stream.mjpeg_stream import MjpegStreamer
from web.routes import register_routes


class MiniCamSimApp:
    def __init__(self):
        self.state = AppState()
        self.flask_app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')

        settings = self.state.settings
        self.renderer = Renderer(settings)
        self.streamer = MjpegStreamer(self.renderer, fps=settings['app']['fps'])

        register_routes(self.flask_app, self.streamer)

    def run(self):
        app_cfg = self.state.settings['app']
        self.flask_app.run(host=app_cfg['host'], port=app_cfg['port'], threaded=True)
