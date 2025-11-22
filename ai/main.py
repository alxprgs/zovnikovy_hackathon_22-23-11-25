import asyncio
import json
import os
import threading
import time
import urllib.request
import traceback
from typing import Optional, Dict, Any

import cv2
import torch
import websockets
from websockets.exceptions import ConnectionClosed

from yolo_world_onnx import YOLOWORLD


ONNX_MODEL_PATH = "yolov8x-worldv2.onnx"
ONNX_MODEL_URL = (
    "https://github.com/Ziad-Algrafi/ODLabel/raw/main/assets/"
    "yolov8x-worldv2.onnx?download="
)

if not os.path.exists(ONNX_MODEL_PATH):
    print("[INFO] YOLO-World ONNX model not found. Downloading...")
    try:
        urllib.request.urlretrieve(ONNX_MODEL_URL, ONNX_MODEL_PATH)
        print("[INFO] Download complete:", ONNX_MODEL_PATH)
    except Exception as e:
        print("[ERROR] Failed to download YOLO-World ONNX:", e)
        raise SystemExit(1)


TARGETS = [
    {
        "name": "phone",
        "prompt": "smartphone, mobile phone, cellphone",
        "color": (0, 255, 0),
    },
    {
        "name": "bottle",
        "prompt": "bottle, plastic water bottle",
        "color": (255, 0, 0),
    },
]

class FrameGrabber:

    def __init__(self, source: str, reopen_delay: float = 1.0):
        self.source = source
        self.reopen_delay = reopen_delay
        self.cap: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.latest_frame = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        src = self.source.strip()
        print(f"[INFO] Opening video source: {src}")

        if src.isdigit():
            cap = cv2.VideoCapture(int(src))
        elif src.startswith("rtsp://"):
            cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(src)

        if not cap or not cap.isOpened():
            print("[ERROR] Cannot open video source")
            return None

        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        return cap

    def start(self):
        if self.thread is not None:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.is_set():
            if self.cap is None or not self.cap.isOpened():
                self.cap = self._open_capture()
                if self.cap is None:
                    time.sleep(self.reopen_delay)
                    continue

            ok, frame = self.cap.read()
            if not ok or frame is None:
                print("[WARN] FrameGrabber: read failed, reopening source...")
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
                time.sleep(self.reopen_delay)
                continue

            with self.lock:
                self.latest_frame = frame

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def get_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                print("[WARN] FrameGrabber thread didn't stop in time; leaving capture open.")
                return
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.thread = None
        self.cap = None


async def heartbeat(ws: websockets.WebSocketClientProtocol, interval: float = 10.0):
    """
    Отправляем WebSocket ping каждые interval секунд.
    ping — это control-frame, JSON не трогает.
    """
    try:
        while True:
            await ws.ping()
            await asyncio.sleep(interval)
    except Exception:
        return

async def ws_receiver(ws: websockets.WebSocketClientProtocol, inbox: asyncio.Queue):
    try:
        async for msg in ws:
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", "ignore")
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                data = {"raw": msg}

            if inbox.full():
                try:
                    _ = inbox.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await inbox.put(data)
    except ConnectionClosed:
        pass
    except Exception as e:
        print("[WARN] ws_receiver error:", e)


async def ws_sender(ws: websockets.WebSocketClientProtocol, outbox: asyncio.Queue):
    try:
        while True:
            payload = await outbox.get()
            await ws.send(json.dumps(payload))
    except ConnectionClosed:
        pass
    except Exception as e:
        print("[WARN] ws_sender error:", e)

async def camera_client(
    ws_url: str,
    source: str,
    company: str,
    warehouse_id: str,
    api_key: str,
    show: bool = True,
    send_every: float = 0.5,
    conf_thres: float = 0.30,
    iou_thres: float = 0.7,
    reconnect_min_delay: float = 2.0,
    reconnect_max_delay: float = 15.0,
):
    use_gpu = torch.cuda.is_available()
    device_str = "0" if use_gpu else "cpu"
    print(f"[INFO] YOLO-World-ONNX device: {device_str}")

    model = YOLOWORLD(ONNX_MODEL_PATH, device=device_str)

    class_prompts = [t["prompt"] for t in TARGETS]
    model.set_classes(class_prompts)
    names = model.names

    print("[INFO] Model initialized with classes:")
    for idx, name in enumerate(names):
        print(f"  {idx}: {name}")

    grabber = FrameGrabber(source)
    grabber.start()
    last_counts: Dict[str, Optional[int]] = {t["name"]: None for t in TARGETS}
    last_send_time: Dict[str, float] = {t["name"]: 0.0 for t in TARGETS}

    fps_smooth = 0.0
    prev_t = time.time()

    delay = reconnect_min_delay

    while True:
        try:
            print("[INFO] Connecting to WebSocket:", ws_url)
            async with websockets.connect(
                ws_url,
                max_size=10_000_000,
                ping_interval=None,
                compression=None, 
            ) as ws:
                print("[INFO] WebSocket connected")

                # Очереди
                inbox: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=20)
                outbox: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=20)

                auth_payload = {
                    "company": company,
                    "warehouse_id": warehouse_id,
                    "api_key": api_key,
                }
                await ws.send(json.dumps(auth_payload))

                try:
                    auth_resp_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    print("[ERROR] Auth timeout")
                    raise RuntimeError("auth timeout")

                if isinstance(auth_resp_raw, bytes):
                    auth_resp_raw = auth_resp_raw.decode("utf-8", "ignore")

                try:
                    auth_resp = json.loads(auth_resp_raw)
                except json.JSONDecodeError:
                    print("[ERROR] Non-JSON auth response:", auth_resp_raw)
                    raise RuntimeError("bad auth response")

                if not auth_resp.get("ok"):
                    print("[ERROR] Auth failed from server:", auth_resp)
                    await asyncio.sleep(5)
                    continue

                print("[INFO] Auth OK:", auth_resp)

                hb_task = asyncio.create_task(heartbeat(ws, interval=10.0))
                recv_task = asyncio.create_task(ws_receiver(ws, inbox))
                send_task = asyncio.create_task(ws_sender(ws, outbox))

                delay = reconnect_min_delay

                try:
                    while True:
                        frame = grabber.get_frame()
                        if frame is None:
                            await asyncio.sleep(0.01)
                            continue

                        boxes, scores, class_ids = model(
                            frame,
                            conf=conf_thres,
                            imgsz=640,
                            iou=iou_thres,
                        )

                        draw = frame.copy()
                        counts = {t["name"]: 0 for t in TARGETS}
                        H, W = frame.shape[:2]

                        for box, score, class_id in zip(boxes, scores, class_ids):
                            cid = int(class_id)
                            if not (0 <= cid < len(TARGETS)):
                                continue
                            obj = TARGETS[cid]
                            counts[obj["name"]] += 1

                            x, y, w, h = box
                            x1 = max(0, min(W - 1, int(x - w / 2)))
                            y1 = max(0, min(H - 1, int(y - h / 2)))
                            x2 = max(0, min(W - 1, int(x + w / 2)))
                            y2 = max(0, min(H - 1, int(y + h / 2)))

                            color = obj["color"]
                            cv2.rectangle(draw, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(
                                draw,
                                f"{obj['name']} {float(score):.2f}",
                                (x1, max(0, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                color,
                                2,
                            )

                        now = time.time()
                        payload_detect = []
                        for obj in TARGETS:
                            name = obj["name"]
                            cnt = counts[name]

                            need_send = (
                                last_counts[name] is None
                                or last_counts[name] != cnt
                                or (
                                    send_every > 0
                                    and (now - last_send_time[name] >= send_every)
                                )
                            )

                            if need_send:
                                payload_detect.append({"type": name, "count": cnt})
                                last_counts[name] = cnt
                                last_send_time[name] = now

                        if payload_detect:
                            payload = {"detect": payload_detect}
                            if outbox.full():
                                try:
                                    _ = outbox.get_nowait()
                                except asyncio.QueueEmpty:
                                    pass
                            await outbox.put(payload)

                        while not inbox.empty():
                            msg = await inbox.get()
                            if isinstance(msg, dict) and not msg.get("ok", True):
                                print("[SERVER ERROR]", msg)

                        cur_t = time.time()
                        fps = 1.0 / max(1e-6, cur_t - prev_t)
                        prev_t = cur_t
                        fps_smooth = (
                            fps_smooth * 0.9 + fps * 0.1 if fps_smooth > 0 else fps
                        )

                        cv2.putText(
                            draw,
                            f"FPS: {fps_smooth:.1f}",
                            (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.0,
                            (255, 255, 255),
                            2,
                        )

                        if show:
                            cv2.imshow("YOLO-World Camera Client", draw)
                            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                                raise KeyboardInterrupt

                finally:
                    for t in (hb_task, recv_task, send_task):
                        t.cancel()
                    for t in (hb_task, recv_task, send_task):
                        try:
                            await t
                        except asyncio.CancelledError:
                            pass

        except ConnectionClosed as e:
            print(f"[WARN] WebSocket disconnected: {e}. Reconnecting in {delay:.1f}s...")
            await asyncio.sleep(delay)
            delay = min(reconnect_max_delay, delay * 1.5)
            continue
        except KeyboardInterrupt:
            print("[INFO] KeyboardInterrupt – exiting...")
            break
        except Exception as e:
            print("[ERROR] Exception in main loop:", e)
            traceback.print_exc()
            print(f"[INFO] Reconnecting in {delay:.1f}s...")
            await asyncio.sleep(delay)
            delay = min(reconnect_max_delay, delay * 1.5)
            continue

    grabber.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Safe & fast YOLO-World camera client")
    parser.add_argument("--url", required=True, help="ws://host/ws/warehouse/<id>/camera")
    parser.add_argument("--source", required=True, help="0 or rtsp://user:pass@ip/stream")
    parser.add_argument("--company", required=True)
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--send-every", type=float, default=0.5, help="min seconds between updates for same item")
    parser.add_argument("--hide", action="store_true", help="do not show OpenCV window")
    parser.add_argument("--conf", type=float, default=0.30, help="confidence threshold")
    parser.add_argument("--iou", type=float, default=0.70, help="IOU threshold")

    args = parser.parse_args()

    asyncio.run(
        camera_client(
            ws_url=args.url,
            source=args.source,
            company=args.company,
            warehouse_id=args.warehouse_id,
            api_key=args.api_key,
            show=not args.hide,
            send_every=args.send_every,
            conf_thres=args.conf,
            iou_thres=args.iou,
        )
    )