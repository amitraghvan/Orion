"""Spatial Temporal Graph Convolutional Network (ST-GCN) in PyTorch for skeleton-based HAR."""

from typing import cast

import torch
from torch import nn

from orion_ai.activity.stgcn.graph import SkeletonGraph

NUM_CLASSES: int = 6  # 6 trained activity classes


class SpatialGraphConv(nn.Module):
    """Spatial graph convolution using partitioned skeleton adjacency and learnable edge masks."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_partitions: int = 3,
        num_joints: int = 17,
    ) -> None:
        super().__init__()
        self.num_partitions = num_partitions
        self.num_joints = num_joints

        # 1x1 convolution mapping in_channels * num_partitions -> out_channels
        self.conv = nn.Conv2d(
            in_channels * num_partitions,
            out_channels,
            kernel_size=(1, 1),
            bias=False,
        )
        self.bn = nn.BatchNorm2d(out_channels)

        # Learnable edge importance weighting mask: shape (num_partitions, 17, 17)
        self.edge_importance = nn.Parameter(
            torch.ones((num_partitions, num_joints, num_joints), dtype=torch.float32)
        )

    def forward(self, x: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Tensor of shape (N, C, T, V)
            A: Normalized adjacency tensor of shape (num_partitions, V, V)
        """
        N, C, T, V = x.size()

        # Apply learnable edge importance: A_eff = A * M
        A_eff = A * self.edge_importance  # shape: (3, V, V)

        # Permute x for batched matrix multiplication: (N, C, T, V) -> (N, T, C, V)
        x_perm = x.permute(0, 2, 1, 3).contiguous().view(N * T, C, V)

        out_list = []
        for k in range(self.num_partitions):
            # (N*T, C, V) x (V, V) -> (N*T, C, V)
            z_k = torch.matmul(x_perm, A_eff[k])
            out_list.append(z_k)

        # Concatenate along channel dimension: (N*T, C*3, V)
        z = torch.cat(out_list, dim=1)
        z = z.view(N, T, C * self.num_partitions, V).permute(0, 2, 1, 3).contiguous()

        return cast("torch.Tensor", self.bn(self.conv(z)))


class STGCNBlock(nn.Module):
    """Residual building block uniting spatial graph conv with temporal 1D convolution."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        temporal_kernel_size: int = 9,
        stride: int = 1,
        dropout: float = 0.2,
        num_partitions: int = 3,
        num_joints: int = 17,
    ) -> None:
        super().__init__()
        self.sgcn = SpatialGraphConv(in_channels, out_channels, num_partitions, num_joints)

        padding = (temporal_kernel_size - 1) // 2
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=(temporal_kernel_size, 1),
                stride=(stride, 1),
                padding=(padding, 0),
                bias=False,
            ),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout),
        )

        self.relu = nn.ReLU(inplace=True)

        # Residual skip connection
        self.residual: nn.Module
        if in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=(1, 1),
                    stride=(stride, 1),
                    bias=False,
                ),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.residual = nn.Identity()

    def forward(self, x: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        res = self.residual(x)
        x = self.relu(self.sgcn(x, A))
        x = self.tcn(x)
        return cast("torch.Tensor", self.relu(x + res))


class STGCNHARModel(nn.Module):
    """Compact, edge-optimized 4-block ST-GCN network for spaceborne human action recognition."""

    def __init__(
        self,
        in_channels: int = 4,
        num_classes: int = NUM_CLASSES,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.graph = SkeletonGraph()
        # Register fixed adjacency buffer (shape: 3, 17, 17)
        self.register_buffer("A", self.graph.to_tensor())

        # Input data batch normalization across channels and joints
        self.data_bn = nn.BatchNorm1d(in_channels * 17)

        # 4-block backbone designed for edge constraints (~250k parameters)
        self.block1 = STGCNBlock(in_channels, 32, stride=1, dropout=dropout)
        self.block2 = STGCNBlock(32, 64, stride=2, dropout=dropout)
        self.block3 = STGCNBlock(64, 128, stride=1, dropout=dropout)
        self.block4 = STGCNBlock(128, 128, stride=2, dropout=dropout)

        # Global average pooling over time and vertices
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        # Linear classifier head
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input tensor of shape (N, C, T, V)
        Returns:
            logits: Tensor of shape (N, num_classes)
        """
        N, C, T, V = x.size()

        # Input batch normalization: permute to (N, C*V, T)
        x_norm = x.permute(0, 1, 3, 2).contiguous().view(N, C * V, T)
        x_norm = self.data_bn(x_norm)
        x = x_norm.view(N, C, V, T).permute(0, 1, 3, 2).contiguous()

        A = self.A  # Buffer tensor (3, 17, 17)

        x = self.block1(x, A)
        x = self.block2(x, A)
        x = self.block3(x, A)
        x = self.block4(x, A)

        # Global spatial-temporal pool: (N, 128, 1, 1)
        x = self.pool(x)
        x = x.view(N, -1)

        return cast("torch.Tensor", self.fc(x))

    def count_parameters(self) -> int:
        """Return total number of trainable model parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
