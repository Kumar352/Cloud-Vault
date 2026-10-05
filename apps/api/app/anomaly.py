"""Small deterministic Isolation Forest for review-only activity anomaly signals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence


def _expected_path(size: int) -> float:
    if size <= 1:
        return 0.0
    if size == 2:
        return 1.0
    harmonic = math.log(size - 1) + 0.5772156649
    return 2 * harmonic - (2 * (size - 1) / size)


@dataclass
class _Node:
    size: int
    feature: int | None = None
    split: float = 0.0
    left: "_Node | None" = None
    right: "_Node | None" = None


class IsolationForest:
    """Random partition trees; intentionally small for local demo-sized audit data."""

    def __init__(self, trees: int = 64, sample_size: int = 128, seed: int = 31) -> None:
        self.trees = trees
        self.sample_size = sample_size
        self.random = random.Random(seed)
        self.forest: list[_Node] = []
        self.dimensions = 0

    def _build(self, points: list[Sequence[float]], depth: int, max_depth: int) -> _Node:
        node = _Node(size=len(points))
        if depth >= max_depth or len(points) <= 1:
            return node
        ranges = [i for i in range(self.dimensions) if min(p[i] for p in points) < max(p[i] for p in points)]
        if not ranges:
            return node
        feature = self.random.choice(ranges)
        low = min(point[feature] for point in points)
        high = max(point[feature] for point in points)
        split = self.random.uniform(low, high)
        left = [point for point in points if point[feature] < split]
        right = [point for point in points if point[feature] >= split]
        if not left or not right:
            return node
        node.feature, node.split = feature, split
        node.left = self._build(left, depth + 1, max_depth)
        node.right = self._build(right, depth + 1, max_depth)
        return node

    def fit(self, points: Sequence[Sequence[float]]) -> "IsolationForest":
        if not points or not points[0]:
            raise ValueError("Training examples are required")
        self.dimensions = len(points[0])
        if any(len(point) != self.dimensions for point in points):
            raise ValueError("Training feature dimensions do not match")
        maximum_depth = math.ceil(math.log2(min(len(points), self.sample_size)))
        self.forest = []
        for _ in range(self.trees):
            sample = self.random.sample(list(points), min(len(points), self.sample_size))
            self.forest.append(self._build(sample, 0, maximum_depth))
        return self

    def _path(self, node: _Node, point: Sequence[float], depth: int = 0) -> float:
        if node.feature is None or node.left is None or node.right is None:
            return depth + _expected_path(node.size)
        child = node.left if point[node.feature] < node.split else node.right
        return self._path(child, point, depth + 1)

    def score(self, point: Sequence[float]) -> float:
        if not self.forest:
            raise ValueError("Call fit before scoring")
        if len(point) != self.dimensions:
            raise ValueError("Feature dimensions do not match")
        normalizer = _expected_path(self.sample_size)
        if normalizer == 0:
            return 0.0
        path = sum(self._path(tree, point) for tree in self.forest) / len(self.forest)
        return 2 ** (-path / normalizer)


FEATURES = ("actions_in_hour", "bytes_uploaded_in_hour", "denied_actions_in_hour", "distinct_files_in_hour")


def synthetic_evaluation(seed: int = 19) -> dict[str, object]:
    rng = random.Random(seed)
    normal = [
        [max(0, rng.gauss(4, 1.5)), max(0, rng.gauss(40_000, 18_000)), max(0, rng.gauss(0.1, 0.35)), max(1, rng.gauss(3, 1.2))]
        for _ in range(128)
    ]
    anomalies = [
        [80, 80_000_000, 20, 70],
        [60, 2_000_000, 35, 40],
        [45, 90_000_000, 5, 100],
        [100, 20_000_000, 45, 80],
    ]
    model = IsolationForest().fit(normal)
    threshold = 0.62
    normal_scores = [model.score(row) for row in normal]
    anomaly_scores = [model.score(row) for row in anomalies]
    true_positive = sum(score >= threshold for score in anomaly_scores)
    false_positive = sum(score >= threshold for score in normal_scores)
    return {
        "model": "local-isolation-forest",
        "training_examples": len(normal),
        "synthetic_anomalies": len(anomalies),
        "threshold": threshold,
        "precision": true_positive / max(1, true_positive + false_positive),
        "recall": true_positive / len(anomalies),
        "false_positive_rate": false_positive / len(normal),
        "normal_score_max": round(max(normal_scores), 4),
        "anomaly_scores": [round(score, 4) for score in anomaly_scores],
    }


def reasons(point: Sequence[float], baseline: Sequence[Sequence[float]]) -> list[str]:
    output = []
    for index, label in enumerate(FEATURES):
        values = [row[index] for row in baseline]
        median = sorted(values)[len(values) // 2]
        deviations = sorted(abs(value - median) for value in values)
        mad = max(1.0, deviations[len(deviations) // 2])
        if abs(point[index] - median) / mad >= 6:
            output.append(f"{label} is {point[index]:g}, far from the synthetic baseline median {median:g}")
    return output[:4]
