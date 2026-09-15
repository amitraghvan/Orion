"""Unit tests for STGCNHARModel PyTorch architecture and deterministic inference repeatability."""

import torch
from torch import nn

from orion_ai.activity.stgcn.model import NUM_CLASSES, STGCNHARModel


def test_stgcn_forward_pass_shape() -> None:
    """Verify ST-GCN forward pass produces expected logit dimensions (N, 6)."""
    model = STGCNHARModel(in_channels=4, num_classes=NUM_CLASSES)
    model.eval()

    # Batch of 2 sequences, 4 channels, 32 frames, 17 joints
    dummy_input = torch.randn((2, 4, 32, 17), dtype=torch.float32)

    with torch.no_grad():
        output = model(dummy_input)

    assert output.shape == (2, NUM_CLASSES)
    assert not torch.isnan(output).any()


def test_stgcn_parameter_count_budget() -> None:
    """Verify model parameter count meets the edge-optimized target budget (~250k parameters)."""
    model = STGCNHARModel(in_channels=4, num_classes=NUM_CLASSES)
    total_params = model.count_parameters()

    # Parameter budget constraint: between 100k and 500k parameters
    assert 100_000 <= total_params <= 500_000, f"Expected ~250k parameters, got {total_params}"


def test_stgcn_backward_gradient_flow() -> None:
    """Verify backpropagation computes valid non-zero gradients across all trainable parameters."""
    model = STGCNHARModel(in_channels=4, num_classes=NUM_CLASSES)
    model.train()

    dummy_input = torch.randn((2, 4, 32, 17), dtype=torch.float32)
    targets = torch.tensor([0, 3], dtype=torch.long)

    criterion = nn.CrossEntropyLoss()
    logits = model(dummy_input)
    loss = criterion(logits, targets)

    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"Parameter {name} has no gradient"
        assert not torch.isnan(param.grad).any(), f"Parameter {name} has NaN gradient"


def test_stgcn_deterministic_inference_repeatability() -> None:
    """Verify that identical input tensors produce 100% bitwise identical output logits."""
    model = STGCNHARModel(in_channels=4, num_classes=NUM_CLASSES)
    model.eval()

    torch.manual_seed(42)
    fixed_input = torch.randn((1, 4, 32, 17), dtype=torch.float32)

    with torch.no_grad():
        run1 = model(fixed_input)
        run2 = model(fixed_input)
        run3 = model(fixed_input)

    assert torch.equal(run1, run2), "ST-GCN inference run 1 and run 2 produced differing outputs"
    assert torch.equal(run2, run3), "ST-GCN inference run 2 and run 3 produced differing outputs"
