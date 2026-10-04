"""One-dimensional label placement."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

_EPS = 1e-9


@dataclass
class _Cluster:
    first: int  # index of the first position in the cluster
    count: int
    top: float  # position of the first element


def place_labels(desired: Sequence[float], min_distance: float) -> list[float]:
    """Spread sorted label positions so neighbors are at least ``min_distance`` apart.

    Overlapping labels are merged into clusters that are centered on their
    desired positions, which minimizes the total squared displacement.
    """
    clusters: list[_Cluster] = []
    for index, position in enumerate(desired):
        clusters.append(_Cluster(index, 1, position))
        while len(clusters) > 1:
            a, b = clusters[-2], clusters[-1]
            if a.top + a.count * min_distance <= b.top + _EPS:
                break
            count = a.count + b.count
            top = sum(desired[a.first + k] - k * min_distance for k in range(count)) / count
            clusters[-2:] = [_Cluster(a.first, count, top)]
    result: list[float] = []
    for cluster in clusters:
        result.extend(cluster.top + k * min_distance for k in range(cluster.count))
    return result
