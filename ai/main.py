from __future__ import annotations

import os
import time
import threading
from queue import Queue, Empty
from typing import Dict, Optional

import cv2
import httpx
import torch
from ultralytics import YOLO


RTSP_URL = "rtsp://Alx_admin:123@10.2.50.154:554/stream1"

SERVER = "https://hackathon.asfes.ru"
ORG_NAME = "123"
WAREHOUSE_ID = "6922ae861986302025f83ef1"
CAMERA_API_KEY = "zF2Cys4-HJxIOHBRavNZGYlnz_JXtSrJ"

ENDPOINT = f"{SERVER.rstrip('/')}/camera"

MODEL_PATH = "yolo12x.pt"
IMGSZ = 640
CONF = 0.35
IOU = 0.5

TARGET_CLASS_NAMES = {
    "apple": "apple",
    "bottle": "bottle",
    "cell phone": "phone",
}

COLORS = {
    "apple": (0, 255, 0),
    "bottle": (255, 0, 0),
    "cell phone": (0, 200, 255),
}

SEND_INTERVAL_SEC = 1.0


class CountsPoster(threading.Thread):
    def __init__(self, queue: Queue, interval_sec: float, endpoint: str):
        super().__init__(daemon=True)
        self.queue = queue
        self.interval_sec = interval_sec
        self.endpoint = endpoint
        self._stop = threading.Event()
        self._latest_counts: Dict[str, int] = {}

    def stop(self):
        self._stop.set()

    def run(self):
        with httpx.Client(timeout=5.0) as client:
            last_send = 0.0
            while not self._stop.is_set():
                try:
                    while True:
                        self._latest_counts = self.queue.get_nowait()
                except Empty:
                    pass

                now = time.time()
                if now - last_send >= self.interval_sec:
                    last_send = now
                    try:
                        payload = self._build_request(self._latest_counts)
                        client.post(self.endpoint, json=payload)
                    except Exception as e:
                        print("[API ERROR]", repr(e))

                time.sleep(0.05)

    @staticmethod
    def _build_request(counts: Dict[str, int]) -> Dict:
        detect_list = []
        for coco_name, count in counts.items():
            if count <= 0:
                continue
            detect_list.append({"type": coco_name, "count": int(count)})

        return {
            "auth": {
                "company": ORG_NAME,
                "warehouse_id": WAREHOUSE_ID,
                "api_key": CAMERA_API_KEY,
            },
            "payload": {"detect": detect_list},
        }


class RTSPGrabber(threading.Thread):
    """
    Постоянно читает RTSP и хранит только последний кадр.
    Если инференс тормозит — старые кадры не копятся.
    """

    def __init__(self, url: str):
        super().__init__(daemon=True)
        self.url = url
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_frame: Optional[any] = None
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self.fails = 0

    def stop(self):
        self._stop.set()

    def _open(self):
        os.environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS",
            "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;0"
        )

        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def run(self):
        self.cap = self._open()
        if not self.cap.isOpened():
            print("[RTSP] cannot open stream")
            return

        while not self._stop.is_set():
            ok = self.cap.grab()
            if not ok:
                self.fails += 1
                if self.fails > 30:
                    print("[RTSP] reconnecting...")
                    try:
                        self.cap.release()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    self.cap = self._open()
                    self.fails = 0
                continue

            self.fails = 0
            ok, frame = self.cap.retrieve()
            if not ok or frame is None:
                continue

            with self.lock:
                self.last_frame = frame

        try:
            self.cap.release()
        except Exception:
            pass

    def get_latest(self):
        with self.lock:
            if self.last_frame is None:
                return None
            return self.last_frame.copy()


def pick_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def draw_hud(frame, counts_pretty: Dict[str, int], fps: float):
    cv2.putText(
        frame, f"FPS: {fps:.1f}",
        (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
        0.8, (255, 255, 255), 2, cv2.LINE_AA
    )
    y = 55
    for pretty_name, c in counts_pretty.items():
        cv2.putText(
            frame, f"{pretty_name}: {c}",
            (10, y), cv2.FONT_HERSHEY_SIMPLEX,
            0.8, (255, 255, 255), 2, cv2.LINE_AA
        )
        y += 28


def main():
    device = pick_device()
    print("[INFO] device:", device)

    if device == "cuda":
        torch.backends.cudnn.benchmark = True

    model = YOLO(MODEL_PATH).to(device)
    half = (device == "cuda")

    grabber = RTSPGrabber(RTSP_URL)
    grabber.start()

    counts_queue: Queue = Queue(maxsize=1)
    poster = CountsPoster(counts_queue, SEND_INTERVAL_SEC, ENDPOINT)
    poster.start()

    last_t = time.time()
    fps_ema = 0.0
    alpha = 0.1

    MIN_INFER_DT = 0.0
    last_infer_t = 0.0

    try:
        while True:
            frame = grabber.get_latest()
            if frame is None:
                time.sleep(0.01)
                continue

            now = time.time()
            if MIN_INFER_DT > 0 and (now - last_infer_t) < MIN_INFER_DT:
                cv2.imshow("ASFES Camera Client (YOLO12x + RTSP + API)", frame)
                if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
                    break
                continue

            last_infer_t = now

            results = model.predict(
                source=frame,
                imgsz=IMGSZ,
                conf=CONF,
                iou=IOU,
                half=half,
                verbose=False,
                device=device
            )

            counts: Dict[str, int] = {k: 0 for k in TARGET_CLASS_NAMES.keys()}

            for r in results:
                if r.boxes is None:
                    continue
                boxes = r.boxes.xyxy.cpu().numpy()
                cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                confs = r.boxes.conf.cpu().numpy()

                for (x1, y1, x2, y2), cls_id, cf in zip(boxes, cls_ids, confs):
                    coco_name = model.names.get(cls_id, str(cls_id))
                    if coco_name not in TARGET_CLASS_NAMES:
                        continue

                    counts[coco_name] += 1

                    color = COLORS.get(coco_name, (0, 255, 255))
                    cv2.rectangle(frame, (int(x1), int(y1)),
                                  (int(x2), int(y2)), color, 2)

                    label = f"{TARGET_CLASS_NAMES[coco_name]} {cf:.2f}"
                    cv2.putText(
                        frame, label,
                        (int(x1), int(y1) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, color, 2, cv2.LINE_AA
                    )

            counts_pretty = {TARGET_CLASS_NAMES[k]: v for k, v in counts.items()}

            new_t = time.time()
            dt = new_t - last_t
            last_t = new_t
            inst_fps = (1.0 / dt) if dt > 1e-6 else 0.0
            fps_ema = inst_fps if fps_ema == 0.0 else (fps_ema * (1 - alpha) + inst_fps * alpha)

            draw_hud(frame, counts_pretty, fps_ema)

            if counts_queue.full():
                try:
                    counts_queue.get_nowait()
                except Empty:
                    pass
            counts_queue.put_nowait(counts)

            cv2.imshow("ASFES Camera Client (YOLO12x + RTSP + API)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

    finally:
        grabber.stop()
        poster.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
