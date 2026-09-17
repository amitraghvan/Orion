"""Decoupled network video streaming manager supporting destination IP push and HTTP monitoring."""

from __future__ import annotations

import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import cv2
import numpy as np
from app.core.logging import get_logger
from app.core.state_manager import state_manager

logger = get_logger("app.streaming.manager")


class UDPStreamSender:
    """Non-blocking UDP unicast stream transmitter pushing video packets to a target IP."""

    def __init__(self, dest_ip: str, dest_port: int, max_packet_size: int = 60000) -> None:
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.max_packet_size = max_packet_size
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass

    def send_frame(self, frame_bytes: bytes, frame_id: int = 0) -> bool:
        """Send JPEG payload to destination IP:port, chunking if necessary."""
        try:
            total_len = len(frame_bytes)
            if total_len <= self.max_packet_size:
                # Header: Magic (4B: ORIO) | FrameID (4B) | TotalLen (4B) | ChunkIdx (2B) | TotalChunks (2B)
                header = struct.pack("!4sIIHH", b"ORIO", frame_id, total_len, 0, 1)
                self._sock.sendto(header + frame_bytes, (self.dest_ip, self.dest_port))
            else:
                num_chunks = (total_len + self.max_packet_size - 1) // self.max_packet_size
                for chunk_idx in range(num_chunks):
                    start = chunk_idx * self.max_packet_size
                    end = min(start + self.max_packet_size, total_len)
                    chunk_data = frame_bytes[start:end]
                    header = struct.pack(
                        "!4sIIHH", b"ORIO", frame_id, total_len, chunk_idx, num_chunks
                    )
                    self._sock.sendto(header + chunk_data, (self.dest_ip, self.dest_port))
            return True
        except Exception as exc:
            logger.debug(
                "UDP streaming socket error",
                dest=f"{self.dest_ip}:{self.dest_port}",
                error=str(exc),
            )
            return False

    def close(self) -> None:
        try:
            self._sock.close()
        except Exception:
            pass


class MJPEGHandler(BaseHTTPRequestHandler):
    """Serves continuous multipart/x-mixed-replace MJPEG stream for remote observation."""

    server_ref: Any = None

    def do_GET(self) -> None:
        if self.path in ("/", "/live", "/stream"):
            self.send_response(200)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
            self.end_headers()

            while getattr(self.server_ref, "is_running", False):
                jpeg = getattr(self.server_ref, "latest_jpeg", None)
                if jpeg is not None:
                    try:
                        self.wfile.write(b"--FRAME\r\n")
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(jpeg)))
                        self.end_headers()
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError):
                        break
                time.sleep(0.04)
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress HTTP access logging to keep console clean


class StreamManager:
    """Manages IP network video streaming (UDP push to specific destination IP and HTTP server)."""

    def __init__(self) -> None:
        self.is_running = False
        self.latest_jpeg: bytes | None = None
        self._server: HTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._udp_sender: UDPStreamSender | None = None
        self._frame_counter = 0
        self._lock = threading.Lock()

        self.destination_ip: str = "127.0.0.1"
        self.destination_port: int = 5000
        self.mode: str = "udp_unicast"

    def start(
        self,
        mode: str = "udp_unicast",
        destination_ip: str = "127.0.0.1",
        destination_port: int = 5000,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> bool:
        """Commence network streaming service."""
        with self._lock:
            if self.is_running:
                return True

            self.mode = mode
            self.destination_ip = destination_ip
            self.destination_port = destination_port
            self.is_running = True
            state_manager.set_streaming(True)

            # 1. Initialize UDP push stream sender to destination IP
            if destination_ip:
                try:
                    self._udp_sender = UDPStreamSender(destination_ip, destination_port)
                    logger.info(
                        "UDP unicast stream active",
                        destination=f"{destination_ip}:{destination_port}",
                    )
                except Exception as exc:
                    logger.warning("Failed to initialize UDP stream sender", error=str(exc))
                    self._udp_sender = None

            # 2. Start optional HTTP MJPEG preview server
            try:
                handler = MJPEGHandler
                handler.server_ref = self
                self._server = HTTPServer((host, port), handler)
                self._http_thread = threading.Thread(
                    target=self._server.serve_forever,
                    name="StreamServerThread",
                    daemon=True,
                )
                self._http_thread.start()
                logger.info("HTTP live monitoring stream active", url=f"http://{host}:{port}/live")
            except Exception as exc:
                logger.warning("Could not start HTTP streaming server", error=str(exc))
                self._server = None

            return True

    def update_frame(self, frame_bgr: np.ndarray, quality: int = 80) -> None:
        """Encode and transmit latest frame to destination IP and HTTP clients."""
        if not self.is_running or frame_bgr is None:
            return

        try:
            self._frame_counter += 1
            ret, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if not ret:
                return

            jpeg_bytes = buf.tobytes()
            self.latest_jpeg = jpeg_bytes

            # Push to destination IP via UDP
            if self._udp_sender is not None:
                self._udp_sender.send_frame(jpeg_bytes, frame_id=self._frame_counter)
        except Exception:
            pass

    def stop(self) -> None:
        """Halt streaming services cleanly."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            state_manager.set_streaming(False)

        if self._udp_sender:
            self._udp_sender.close()
            self._udp_sender = None

        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
        logger.info("IP streaming services halted.")


# Global stream manager singleton
stream_manager = StreamManager()
