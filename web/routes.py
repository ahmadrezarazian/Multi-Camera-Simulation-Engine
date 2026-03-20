from flask import render_template


def register_routes(app, streamer):
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/cam')
    def cam():
        return streamer.response()
