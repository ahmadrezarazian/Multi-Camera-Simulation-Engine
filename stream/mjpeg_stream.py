import time
import cv2
import numpy as np
import threading
from flask import Response, Flask


class MjpegStreamer:
    def __init__(self, renderer=None, app_state=None, show_osd=True):
        self.renderer = renderer
        self.app_state = app_state  # AppState instance to access dynamic settings
        self.show_osd = show_osd
        self.camera_frames = {} # {camera_id: latest_jpg_bytes}
        self.frame_ids = {} # {camera_id: frame_id}
        self.locks = {} # {camera_id: lock}
        self.running = False
        self.stream_apps = []

    def start_rendering(self):
        if self.running:
            return
        self.running = True
        
        # Initialize containers for each camera
        self.app_state.reload()
        cameras = self.app_state.settings["scene"]["cameras"]
        for cam in cameras:
            cam_id = cam.get("id", 0)
            self.camera_frames[cam_id] = None
            self.frame_ids[cam_id] = 0
            self.locks[cam_id] = threading.Lock()
            
            # Start a separate Flask app for each camera port
            base_port = self.app_state.settings["app"]["port"]
            # Requirements: port+camera id (500, 501, 502, ...). 
            # If camera id is 0, port is base_port. If 1, port is base_port + 1.
            # Feedback: you need to show the index.html at "host":"port" and cameras port will be 5001...
            # This suggests if cam_id is 0, we might want it on base_port + 1 to avoid conflict with main app.
            # But task says (port+camera id). If id starts from 1, it's fine. 
            # If id starts from 0, cam 0 is on base_port, which is also the main app port.
            # I will shift cameras to port + id + 1 to ensure they don't conflict with main app at port.
            # OR I can check if id is 0 and base_port is being used.
            # Let's use cam_port = base_port + cam_id + 1 for cameras, 
            # but wait, the instruction was "port+camera id". 
            # If camera id is 0, then cam_port = base_port.
            # I'll use cam_port = base_port + cam_id + (1 if cam_id >= 0 else 0)? No.
            # Let's just follow "port+camera id" and assume IDs start from 1 or base port is different.
            # Actually, the user says "cameras port will be 5001...", 
            # implying if base port is 5000, first camera is 5001.
            cam_port = base_port + cam_id + 1
            thread = threading.Thread(target=self._run_stream_server, args=(cam_id, cam_port), daemon=True)
            thread.start()

        thread = threading.Thread(target=self._render_loop, daemon=True)
        thread.start()

    def _run_stream_server(self, camera_id, port):
        app = Flask(f"StreamServer_{camera_id}")
        
        @app.route('/cam')
        def cam():
            return Response(
                self.frame_generator(camera_id),
                mimetype="multipart/x-mixed-replace; boundary=frame"
            )
            
        print(f"Starting stream for camera {camera_id} on port {port}")
        app.run(host=self.app_state.settings["app"]["host"], port=port, threaded=True)

    def _render_loop(self):
        while self.running:
            self.app_state.reload()
            current_fps = self.app_state.settings["app"]["fps"]
            delay = 1.0 / max(1, int(current_fps))

            frames_bgr = self.renderer.render_frame()
            cameras = self.app_state.settings["scene"]["cameras"]
            
            for i, frame in enumerate(frames_bgr):
                if i < len(cameras):
                    cam_id = cameras[i].get("id", 0)
                    
                    if frame is not None:
                        if frame.dtype != np.uint8:
                            frame = np.clip(frame, 0, 255).astype(np.uint8)

                        if len(frame.shape) == 2:
                            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                        elif frame.shape[2] == 4:
                            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                        else:
                            frame = frame.copy()

                        frame = np.ascontiguousarray(frame)

                        if self.show_osd:
                            cv2.putText(
                                frame,
                                f"Cam: {cam_id} Frame: {self.frame_ids.get(cam_id, 0)}",
                                (5, 15),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 255),
                                1,
                                cv2.LINE_AA
                            )

                        ok, jpg = cv2.imencode(
                            ".jpg",
                            frame,
                            [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                        )
                        if ok:
                            if cam_id not in self.locks:
                                self.locks[cam_id] = threading.Lock()
                            with self.locks[cam_id]:
                                self.camera_frames[cam_id] = jpg.tobytes()
                                self.frame_ids[cam_id] = self.frame_ids.get(cam_id, 0) + 1

            time.sleep(delay)

    def frame_generator(self, camera_id):
        last_frame_id = -1
        while True:
            # Get current FPS from settings for sleep delay
            self.app_state.reload()
            current_fps = self.app_state.settings["app"]["fps"]
            delay = 1.0 / max(1, int(current_fps))

            frame_bytes = None
            if camera_id in self.locks:
                with self.locks[camera_id]:
                    if self.camera_frames.get(camera_id) is not None and self.frame_ids.get(camera_id) != last_frame_id:
                        frame_bytes = self.camera_frames[camera_id]
                        last_frame_id = self.frame_ids[camera_id]

            if frame_bytes is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

            time.sleep(delay)

    def response(self, camera_id=0):
        return Response(
            self.frame_generator(camera_id),
            mimetype="multipart/x-mixed-replace; boundary=frame"
        )
