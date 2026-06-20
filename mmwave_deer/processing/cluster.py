from __future__ import annotations

import math

from mmwave_deer.types import Cluster, RadarPoint


def _dist(a: RadarPoint, b: RadarPoint) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def cluster_points(
    points: list[RadarPoint],
    eps_m: float = 0.75,
    min_points: int = 2,
    min_snr_db: float = 0.0,
) -> list[Cluster]:
    """Simple density clustering for sparse mmWave point clouds."""
    usable = [p for p in points if p.snr >= min_snr_db]
    if not usable:
        return []

    visited = [False] * len(usable)
    clusters: list[Cluster] = []

    for i, seed in enumerate(usable):
        if visited[i]:
            continue
        visited[i] = True
        neighbors = [j for j, p in enumerate(usable) if _dist(seed, p) <= eps_m]
        if len(neighbors) < min_points:
            continue

        members = [usable[i]]
        queue = [j for j in neighbors if j != i]
        while queue:
            j = queue.pop()
            if visited[j]:
                continue
            visited[j] = True
            members.append(usable[j])
            for k, p in enumerate(usable):
                if not visited[k] and _dist(usable[j], p) <= eps_m:
                    queue.append(k)

        xs = [p.x for p in members]
        ys = [p.y for p in members]
        zs = [p.z for p in members]
        clusters.append(
            Cluster(
                points=members,
                centroid_x=sum(xs) / len(xs),
                centroid_y=sum(ys) / len(ys),
                centroid_z=sum(zs) / len(zs),
                extent_x=max(xs) - min(xs),
                extent_y=max(ys) - min(ys),
                extent_z=max(zs) - min(zs),
                mean_velocity=sum(p.velocity for p in members) / len(members),
                mean_snr=sum(p.snr for p in members) / len(members),
                point_count=len(members),
            )
        )

    return clusters
