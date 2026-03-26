import time
import cv2
import numpy as np
import threading
from flask import Response


class MjpegStreamer:
    def __init__(self, renderer=None, app_state=None, show_osd=True):
        self.renderer = renderer
        self.app_state = app_state  # AppState instance to access dynamic settings
        self.show_osd = show_osd
        self.current_frame = None
        self.frame_id = 0
        self.lock = threading.Lock()
        self.running = False

    def start_rendering(self):
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self._render_loop, daemon=True)
        thread.start()

    def _render_loop(self):
        while self.running:
            self.app_state.reload()
            current_fps = self.app_state.settings["app"]["fps"]
            delay = 1.0 / max(1, int(current_fps))

            frame_r = self.renderer.render_frame()
            if frame_r is not None:
                # Convert from RGB to BGR before saving with OpenCV
                frame = cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR)

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
                        f"Frame: {self.frame_id}",
                        (5, 15),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1,
                        cv2.LINE_AA
                    )

                    cv2.putText(
                        frame,
                        "MJPEG Stream OK",
                        (5, 30),
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
                    with self.lock:
                        self.current_frame = jpg.tobytes()
                        self.frame_id += 1

            time.sleep(delay)

    def frame_generator(self):
        last_frame_id = -1
        while True:
            # Get current FPS from settings for sleep delay
            current_fps = self.app_state.settings["app"]["fps"]
            delay = 1.0 / max(1, int(current_fps))

            with self.lock:
                if self.current_frame is not None and self.frame_id != last_frame_id:
                    frame_bytes = self.current_frame
                    last_frame_id = self.frame_id
                else:
                    frame_bytes = None

            if frame_bytes is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

            time.sleep(delay)

    def response(self):
        return Response(
            self.frame_generator(),
            mimetype="multipart/x-mixed-replace; boundary=frame"
        )
