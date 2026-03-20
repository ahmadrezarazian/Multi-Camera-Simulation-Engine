import time
import cv2
import numpy as np
from flask import Response


class MjpegStreamer:
    def __init__(self, renderer=None, fps=30, show_osd=True, width=640, height=480):
        self.renderer = renderer
        self.fps = fps
        self.show_osd = show_osd
        self.width = width
        self.height = height

    def frame_generator(self):
        delay = 1.0 / max(1, int(self.fps))
        frame_id = 0

        while True:
            frame_r = self.renderer.render_frame()
            # try:
            #     frame_r = self.renderer.render_frame()
            # except Exception as e:
            #     print(f"Error occurred while rendering frame: {e}")
            #     frame_r = None
            #     continue

            if frame_r is None:
                continue

            # Convert from RGB to BGR before saving with OpenCV
            frame = cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR)

            # save debug image
            cv2.imwrite("debug_frame.png", frame)

            # print("dtype:", frame.dtype, "shape:", frame.shape,
            #       "min:", frame.min(), "max:", frame.max())

            if frame.dtype != np.uint8:
                frame = np.clip(frame, 0, 255).astype(np.uint8)

            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                # keep as-is; your renderer output is effectively BGR for this stream path
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