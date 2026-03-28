from flask import render_template


def register_routes(app, streamer):
    @app.route('/')
    def home():
        cameras = streamer.app_state.settings["scene"]["cameras"]
        host = streamer.app_state.settings["app"]["host"]
        base_port = streamer.app_state.settings["app"]["port"]
        
        camera_list = []
        for cam in cameras:
            cam_id = cam.get("id", 0)
            camera_list.append({
                "id": cam_id,
                "name": cam.get("name", f"Camera {cam_id}"),
                "url": f"http://{host}:{base_port + cam_id + 1}/cam"
            })
            
        return render_template('index.html', 
                             app_version=app.config['APP_VERSION'],
                             cameras=camera_list)

    @app.route('/cam')
    def cam():
        return streamer.response()
