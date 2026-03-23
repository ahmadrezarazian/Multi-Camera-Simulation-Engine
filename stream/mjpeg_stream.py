import time
import cv2
import numpy as np
from flask import Response


class MjpegStreamer:
    def __init__(self, renderer=None, app_state=None, show_osd=True):
        self.renderer = renderer
        self.app_state = app_state # AppState instance to access dynamic settings
        self.show_osd = show_osd

    def frame_generator(self):
        # Get current FPS from settings
        current_fps = self.app_state.settings["app"]["fps"]
        delay = 1.0 / max(1, int(current_fps))
        frame_id = 0

        while True:
            self.app_state.reload() # Reload settings on each frame for dynamic updates
            frame_r = self.renderer.render_frame()
            #frame_r = self.renderer.render_frame(self.app_state.settings)

            if frame_r is None:
                continue

            # Convert from RGB to BGR before saving with OpenCV
            frame = cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR)

            # save debug image
            cv2.imwrite("frame_generator_out.png", frame)

            if frame.dtype != np.uint8:
                frame = np.clip(frame, 0, 255).astype(np.uint8)

            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                frame = frame.copy()

            frame = np.ascontiguousarray(frame)

            cv2.imwrite("debug_frame.png", frame)

            if self.show_osd:
                cv2.putText(
                    frame,
                    f"Frame: {frame_id}",
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
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
            )

            frame_id += 1
            time.sleep(delay)

    def response(self):
        return Response(
            self.frame_generator(),
            mimetype="multipart/x-mixed-replace; boundary=frame"
        )
