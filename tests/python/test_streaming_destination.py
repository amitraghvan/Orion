"""Tests for destination IP streaming and unicast UDP video packet transmission."""

import socket
import struct
import time
import urllib.request

import numpy as np
import pytest
from app.streaming.stream_manager import StreamManager, UDPStreamSender


def find_free_port(kind=socket.SOCK_DGRAM) -> int:
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_udp_stream_sender_single_packet():
    port = find_free_port(socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", port))
    receiver.settimeout(2.0)

    sender = UDPStreamSender(dest_ip="127.0.0.1", dest_port=port, max_packet_size=1024)
    payload = b"TEST_PAYLOAD_FRAME_BYTES_ORION"
    success = sender.send_frame(payload, frame_id=42)
    assert success is True

    data, addr = receiver.recvfrom(2048)
    receiver.close()
    sender.close()

    magic, frame_id, total_len, chunk_idx, total_chunks = struct.unpack("!4sIIHH", data[:16])
    assert magic == b"ORIO"
    assert frame_id == 42
    assert total_len == len(payload)
    assert chunk_idx == 0
    assert total_chunks == 1
    assert data[16:] == payload


def test_udp_stream_sender_chunking():
    port = find_free_port(socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", port))
    receiver.settimeout(2.0)

    max_chunk = 500
    sender = UDPStreamSender(dest_ip="127.0.0.1", dest_port=port, max_packet_size=max_chunk)
    payload = b"X" * 1250  # Requires 3 chunks: 500, 500, 250
    success = sender.send_frame(payload, frame_id=101)
    assert success is True

    chunks = []
    for _ in range(3):
        data, _ = receiver.recvfrom(2048)
        magic, frame_id, total_len, chunk_idx, total_chunks = struct.unpack("!4sIIHH", data[:16])
        assert magic == b"ORIO"
        assert frame_id == 101
        assert total_len == 1250
        assert total_chunks == 3
        chunks.append((chunk_idx, data[16:]))

    receiver.close()
    sender.close()

    chunks.sort(key=lambda x: x[0])
    reassembled = b"".join(c[1] for c in chunks)
    assert reassembled == payload


def test_stream_manager_runtime_transmission():
    udp_port = find_free_port(socket.SOCK_DGRAM)
    http_port = find_free_port(socket.SOCK_STREAM)

    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", udp_port))
    receiver.settimeout(2.0)

    manager = StreamManager()
    manager.start(
        mode="udp_unicast",
        destination_ip="127.0.0.1",
        destination_port=udp_port,
        host="127.0.0.1",
        port=http_port,
    )
    assert manager.is_running is True

    # Generate test frame and push
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_frame[25:75, 25:75] = [0, 255, 0]  # Green square
    manager.update_frame(dummy_frame)

    data, _ = receiver.recvfrom(65535)
    receiver.close()

    magic, frame_id, total_len, chunk_idx, total_chunks = struct.unpack("!4sIIHH", data[:16])
    assert magic == b"ORIO"
    assert frame_id >= 1
    assert len(data[16:]) > 0

    # Test HTTP MJPEG endpoint connectivity
    time.sleep(0.1)
    url = f"http://127.0.0.1:{http_port}/live"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type", "")
        assert "multipart/x-mixed-replace" in content_type

    manager.stop()
    assert manager.is_running is False
