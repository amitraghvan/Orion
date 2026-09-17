"""Automated verification of offline air-gap enforcement and zero external network access."""

import os
import socket
from pathlib import Path

import pytest
from app.core.airgap import enforce_airgap
from app.core.lifecycle import lifecycle
from app.experiments.experiment_engine import experiment_engine
from app.experiments.experiment_loader import load_protocol


def test_airgap_environment_flags():
    """Verify all offline environment flags and settings are actively applied."""
    enforce_airgap()
    assert os.environ.get("ULTRALYTICS_OFFLINE") == "1"
    assert os.environ.get("YOLO_OFFLINE") == "1"
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    assert os.environ.get("TORCH_HUB_OFFLINE") == "1"


def test_airgap_zero_external_network_activity(monkeypatch):
    """Verify application functions completely offline when external socket connections are blocked."""
    enforce_airgap()

    # Intercept all outbound socket connect calls
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        # Allow loopback/localhost only
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ConnectionRefusedError(
                f"Air-gap violation: Attempted external connection to {host}"
            )
        return orig_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

    # 1. Test Lifecycle startup runs cleanly offline
    lifecycle.startup()

    # 2. Test Protocol loading runs cleanly offline
    protocol_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    assert protocol_path.exists()
    protocol = load_protocol(protocol_path)
    assert protocol.metadata.experiment_id is not None

    # 3. Test Experiment engine lifecycle runs cleanly offline
    engine = experiment_engine
    engine.load_protocol_file(str(protocol_path))
    run_id = engine.start_experiment()
    assert run_id.startswith("RUN-")

    # Complete step and abort cleanly
    engine.stop_experiment()
    assert engine.fsm.state.value == "ABORTED"

    lifecycle.shutdown()
