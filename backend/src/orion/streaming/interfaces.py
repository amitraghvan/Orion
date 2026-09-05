"""Streaming Architecture for ORION BAS AI Copilot.

Architecture only: interfaces for RTSP, WebRTC, Local LAN multicast, and WebSocket telemetry feeds.
Zero streaming implementation.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class StreamSessionConfig(BaseModel):
    """Configuration contract for active video / telemetry streaming sessions."""

    session_id: str
    stream_type: str  # rtsp, webrtc, lan, websocket
    target_endpoint: str
    bitrate_kbps: int = 4000
    fps: int = 30
    width: int = 1920
    height: int = 1080


class RTSPStreamerInterface(ABC):
    """Interface for internal RTSP video broadcast server."""

    @abstractmethod
    async def start_server(self, port: int, mount_point: str) -> None:
        """Start RTSP media server listener."""
        raise NotImplementedError("NOT IMPLEMENTED: RTSPStreamerInterface.start_server")

    @abstractmethod
    async def push_frame(self, frame_buffer: Any) -> None:
        """Push encoded frame into RTSP server buffer."""
        raise NotImplementedError("NOT IMPLEMENTED: RTSPStreamerInterface.push_frame")

    @abstractmethod
    async def stop_server(self) -> None:
        """Stop RTSP streaming service."""
        raise NotImplementedError("NOT IMPLEMENTED: RTSPStreamerInterface.stop_server")


class WebRTCStreamerInterface(ABC):
    """Interface for low-latency peer-to-peer browser video streaming."""

    @abstractmethod
    async def create_offer(self) -> dict[str, str]:
        """Generate WebRTC SDP offer."""
        raise NotImplementedError("NOT IMPLEMENTED: WebRTCStreamerInterface.create_offer")

    @abstractmethod
    async def handle_answer(self, answer_sdp: str) -> None:
        """Accept WebRTC SDP answer from client."""
        raise NotImplementedError("NOT IMPLEMENTED: WebRTCStreamerInterface.handle_answer")

    @abstractmethod
    async def add_ice_candidate(self, candidate: dict[str, Any]) -> None:
        """Register ICE candidate."""
        raise NotImplementedError("NOT IMPLEMENTED: WebRTCStreamerInterface.add_ice_candidate")


class LANStreamerInterface(ABC):
    """Interface for air-gapped UDP/RTP multicast streaming over spacecraft local network."""

    @abstractmethod
    async def start_multicast(self, group_ip: str, port: int) -> None:
        """Join multicast group and open UDP socket."""
        raise NotImplementedError("NOT IMPLEMENTED: LANStreamerInterface.start_multicast")

    @abstractmethod
    async def broadcast_packet(self, packet: bytes) -> None:
        """Send raw RTP packet to multicast group."""
        raise NotImplementedError("NOT IMPLEMENTED: LANStreamerInterface.broadcast_packet")


class WebSocketTelemetryInterface(ABC):
    """Interface for real-time structured telemetry and bounding box broadcasting."""

    @abstractmethod
    async def connect_client(self, client_id: str, websocket: Any) -> None:
        """Register active WebSocket client connection."""
        raise NotImplementedError("NOT IMPLEMENTED: WebSocketTelemetryInterface.connect_client")

    @abstractmethod
    async def disconnect_client(self, client_id: str) -> None:
        """Clean up disconnected WebSocket client."""
        raise NotImplementedError("NOT IMPLEMENTED: WebSocketTelemetryInterface.disconnect_client")

    @abstractmethod
    async def broadcast_telemetry(self, telemetry_payload: dict[str, Any]) -> None:
        """Dispatch JSON telemetry frame to all connected clients."""
        raise NotImplementedError(
            "NOT IMPLEMENTED: WebSocketTelemetryInterface.broadcast_telemetry"
        )
