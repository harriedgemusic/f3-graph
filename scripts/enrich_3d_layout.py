#!/usr/bin/env python3
"""
Enrich public/data/graph.json with:
- 3-tier density classification: "atlas" (~420 nodes), "core" (~1700 nodes), "extended" (all 4239)
- True 3D stratified galaxy coordinates: x3d, y3d, z3d
- True 3D tactical map coordinates: mapX, mapY (vertical stratum), mapZ (north/south on ground plane)
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

GRAPH_PATH = Path("/Users/harriedgemusic/Documents/repos/f3-graph/public/data/graph.json")

STRATUM_Y_GALAXY = {
    "quest": 190.0,
    "event": 135.0,
    "character": 25.0,
    "location": -25.0,
    "item": -135.0,
    "object": -185.0,
}

STRATUM_Y_MAP = {
    "quest": 170.0,
    "event": 125.0,
    "character": 55.0,
    "location": 0.0,
    "object": -65.0,
    "item": -115.0,
}

DLC_ORBIT_ANGLES = {
    "anchorage": 0.0,
    "pitt": 2.0 * math.pi / 5.0,
    "brokensteel": 4.0 * math.pi / 5.0,
    "pointlookout": 6.0 * math.pi / 5.0,
    "zeta": 8.0 * math.pi / 5.0,
}


def main():
    t0 = time.time()
    data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    edges = data["edges"]
    n_nodes = len(nodes)
    id_to_idx = {nd["id"]: i for i, nd in enumerate(nodes)}

    # Build adjacency & quest/event neighbor bonus scores
    quest_or_event_ids = {nd["id"] for nd in nodes if nd["type"] in ("quest", "event")}
    qe_neighbor_count: dict[str, int] = defaultdict(int)
    for e in edges:
        if e["source"] in quest_or_event_ids:
            qe_neighbor_count[e["target"]] += 1
        if e["target"] in quest_or_event_ids:
            qe_neighbor_count[e["source"]] += 1

    # 1. Assign 3-tier progressive density ("atlas", "core", "extended")
    atlas_ids: set[str] = set(quest_or_event_ids)

    def pick_top(ntype: str, limit: int):
        cands = [nd for nd in nodes if nd["type"] == ntype]

        def score(nd):
            bonus = qe_neighbor_count[nd["id"]] * 4.0
            if ntype == "location" and nd["subtype"] in ("marker", "world"):
                bonus += 15.0
            if ntype == "object" and nd["subtype"] == "perk":
                bonus += 8.0
            return (bonus + nd["degree"], nd["degree"])

        cands.sort(key=score, reverse=True)
        for nd in cands[:limit]:
            atlas_ids.add(nd["id"])

    pick_top("character", 90)
    pick_top("location", 90)
    pick_top("item", 60)
    pick_top("object", 55)

    core_ids: set[str] = set(atlas_ids)
    for nd in nodes:
        if nd["type"] in ("quest", "event"):
            core_ids.add(nd["id"])
        elif nd["type"] == "location" and nd["subtype"] in ("marker", "world"):
            core_ids.add(nd["id"])
        elif qe_neighbor_count[nd["id"]] > 0 and nd["degree"] >= 2:
            core_ids.add(nd["id"])
        elif nd["degree"] >= 5:
            core_ids.add(nd["id"])

    for nd in nodes:
        nid = nd["id"]
        if nid in atlas_ids:
            nd["tier"] = "atlas"
        elif nid in core_ids:
            nd["tier"] = "core"
        else:
            nd["tier"] = "extended"

    # 2. Compute True 3D Multi-Stratum Galaxy Layout (x3d, y3d, z3d)
    rng = np.random.default_rng(2077)
    pos3d = np.zeros((n_nodes, 3), dtype=np.float64)
    target_y = np.zeros(n_nodes, dtype=np.float64)

    for i, nd in enumerate(nodes):
        ty = STRATUM_Y_GALAXY.get(nd["type"], 0.0)
        target_y[i] = ty
        dlc = nd["dlc"]
        if dlc == "base":
            # Spread base nodes using previous 2D clustered angle + radius
            ang = math.atan2(nd["y"], nd["x"])
            rad = 90.0 + min(260.0, math.hypot(nd["x"], nd["y"]) * 0.25)
            pos3d[i, 0] = math.cos(ang) * rad + rng.normal(0, 45.0)
            pos3d[i, 1] = ty + rng.normal(0, 18.0)
            pos3d[i, 2] = math.sin(ang) * rad + rng.normal(0, 45.0)
        else:
            ang = DLC_ORBIT_ANGLES.get(dlc, 0.0) + rng.normal(0, 0.22)
            rad = 430.0 + rng.normal(0, 55.0)
            pos3d[i, 0] = math.cos(ang) * rad
            pos3d[i, 1] = ty + rng.normal(0, 18.0)
            pos3d[i, 2] = math.sin(ang) * rad

    src_idx = np.array([id_to_idx[e["source"]] for e in edges], dtype=np.int32)
    tgt_idx = np.array([id_to_idx[e["target"]] for e in edges], dtype=np.int32)

    iters = 55
    for it in range(iters):
        disp = np.zeros_like(pos3d)

        # Edge spring attraction
        if len(src_idx) > 0:
            diff = pos3d[tgt_idx] - pos3d[src_idx]
            dist = np.linalg.norm(diff, axis=1) + 1e-6
            force = (dist - 88.0) * 0.045
            fvec = (diff / dist[:, None]) * force[:, None]
            np.add.at(disp, src_idx, fvec)
            np.add.at(disp, tgt_idx, -fvec)

        # Chunked 3D repulsion
        chunk = 512
        rep_strength = 4400.0
        for s in range(0, n_nodes, chunk):
            e = min(s + chunk, n_nodes)
            d = pos3d[s:e, None, :] - pos3d[None, :, :]
            d2 = np.sum(d * d, axis=2) + 85.0
            inv = rep_strength / (d2 * np.sqrt(d2))
            disp[s:e] += np.sum(d * inv[:, :, None], axis=1)

        # Soft vertical stratum alignment + gentle horizontal centering
        disp[:, 1] += (target_y - pos3d[:, 1]) * 0.095
        disp[:, 0] -= pos3d[:, 0] * 0.012
        disp[:, 2] -= pos3d[:, 2] * 0.012

        max_step = 32.0 * (1.0 - it / (iters + 6.0))
        norms = np.linalg.norm(disp, axis=1) + 1e-6
        scale = np.minimum(1.0, max_step / norms)
        pos3d += disp * scale[:, None]

    # Normalize X/Z to [-600, 600] and Y to [-260, 260]
    xz_max = max(np.abs(pos3d[:, 0]).max(), np.abs(pos3d[:, 2]).max(), 1.0)
    pos3d[:, 0] = (pos3d[:, 0] / xz_max) * 580.0
    pos3d[:, 2] = (pos3d[:, 2] / xz_max) * 580.0
    y_max = max(np.abs(pos3d[:, 1]).max(), 1.0)
    pos3d[:, 1] = (pos3d[:, 1] / y_max) * 250.0

    # 3. Compute 3D Tactical Map Coordinates (mapX, mapY, mapZ)
    # Keep real Wasteland horizontal plane on (X, Z) with North = -Z, and stratify Y vertically
    orig_mx = np.array([nd["mapX"] for nd in nodes], dtype=np.float64)
    orig_my = np.array([nd["mapY"] for nd in nodes], dtype=np.float64)
    m_span = max(np.abs(orig_mx).max(), np.abs(orig_my).max(), 1.0)

    for i, nd in enumerate(nodes):
        mx = (orig_mx[i] / m_span) * 540.0
        mz = -(orig_my[i] / m_span) * 540.0
        base_y = STRATUM_Y_MAP.get(nd["type"], 0.0)
        if nd["type"] == "location" and nd["subtype"] in ("marker", "world"):
            my = 0.0
        else:
            my = base_y + float(rng.normal(0, 12.0))

        nd["x3d"] = round(float(pos3d[i, 0]), 2)
        nd["y3d"] = round(float(pos3d[i, 1]), 2)
        nd["z3d"] = round(float(pos3d[i, 2]), 2)
        nd["mapX"] = round(float(mx), 2)
        nd["mapY"] = round(float(my), 2)
        nd["mapZ"] = round(float(mz), 2)

        for k in ("x3d", "y3d", "z3d", "mapX", "mapY", "mapZ"):
            assert math.isfinite(nd[k]), f"Non-finite {k} on {nd['id']}"

    data["meta"]["atlasNodes"] = len(atlas_ids)
    data["meta"]["coreNodes"] = len(core_ids)

    GRAPH_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    tier_counts = Counter(nd["tier"] for nd in nodes)
    atlas_types = Counter(nd["type"] for nd in nodes if nd["tier"] == "atlas")
    atlas_edges = sum(1 for e in edges if e["source"] in atlas_ids and e["target"] in atlas_ids)
    print(f"Enriched 3D graph in {time.time() - t0:.2f}s:")
    print(f"  tiers: {dict(tier_counts)} (atlas={len(atlas_ids)}, core={len(core_ids)}, total={n_nodes})")
    print(f"  atlas types: {dict(atlas_types)}, atlas edges: {atlas_edges}")
    print(f"  file size: {GRAPH_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
