"""Bipartite and greedy spatial association between detected hands and objects."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from orion.core.logger import get_logger
from orion_ai.hand.schemas import HandObservation, HandState
from orion_ai.interaction.geometry import (
    GeometricInteractionFeatures,
    InteractionGeometryCalculator,
)
from orion_ai.interaction.multimodal_schemas import InteractionState
from orion_ai.interaction.object_schemas import ObjectObservation

logger = get_logger("orion_ai.interaction.associator")


@dataclass
class HandObjectCandidate:
    """Paired candidate representing an observed spatial relationship."""

    hand: HandObservation
    obj: ObjectObservation
    features: GeometricInteractionFeatures
    state_hint: InteractionState


class HandObjectAssociator:
    """Associates hands with candidate objects using Hungarian bipartite matching on distance/overlap."""

    def __init__(
        self,
        geometry_calc: InteractionGeometryCalculator | None = None,
        max_association_dist_norm: float = 0.5,
    ) -> None:
        self.geometry_calc = geometry_calc or InteractionGeometryCalculator()
        self.max_association_dist_norm = max_association_dist_norm

    def associate(
        self,
        hands: list[HandObservation],
        objects: list[ObjectObservation],
        reference_diagonal: float = 1000.0,
        prev_distances: dict[tuple[str, str], float] | None = None,
    ) -> list[HandObjectCandidate]:
        """Pair visible hands to candidate target objects."""
        if not hands or not objects:
            return []

        # Filter out hands that are missing or completely invalid
        valid_hands = [h for h in hands if h.state != HandState.MISSING]
        if not valid_hands:
            return []

        n_hands = len(valid_hands)
        m_objects = len(objects)

        # Build cost matrix: combination of normalized distance and (1 - overlap)
        cost_matrix = np.full((n_hands, m_objects), fill_value=1e4, dtype=np.float32)
        features_matrix: list[list[GeometricInteractionFeatures | None]] = [
            [None for _ in range(m_objects)] for _ in range(n_hands)
        ]

        for i, hand in enumerate(valid_hands):
            for j, obj in enumerate(objects):
                pair_key = (hand.hand_id, obj.object_id)
                prev_dist = prev_distances.get(pair_key) if prev_distances else None
                feat = self.geometry_calc.compute_features(
                    hand=hand,
                    obj=obj,
                    reference_diagonal=reference_diagonal,
                    prev_normalized_distance=prev_dist,
                )
                features_matrix[i][j] = feat

                if (
                    feat.normalized_distance <= self.max_association_dist_norm
                    or feat.overlap_ratio > 0.0
                ):
                    # Lower cost is better: distance minus overlap bonus
                    cost = feat.normalized_distance - (0.5 * feat.overlap_ratio)
                    cost_matrix[i, j] = max(0.0, float(cost))

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        candidates: list[HandObjectCandidate] = []
        for r, c in zip(row_ind, col_ind, strict=False):
            if cost_matrix[r, c] >= 1e3:
                continue

            feat = features_matrix[r][c]
            if feat is None:
                continue

            hand = valid_hands[r]
            obj = objects[c]

            # Infer instantaneous state hint
            state_hint = InteractionState.NO_INTERACTION
            if feat.is_in_contact:
                state_hint = InteractionState.CONTACT
            elif feat.is_near:
                state_hint = (
                    InteractionState.APPROACHING
                    if feat.approach_velocity > 0.01
                    else InteractionState.NEAR
                )

            candidates.append(
                HandObjectCandidate(
                    hand=hand,
                    obj=obj,
                    features=feat,
                    state_hint=state_hint,
                )
            )

        return candidates
