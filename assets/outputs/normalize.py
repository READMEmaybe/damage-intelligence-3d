"""Normalize Hunyuan3D GLBs into the Phase C canonical convention:
  +x = front, +y = left, +z = up, centered, wheels on z=0, length ~4.7 units.

Hunyuan output is Y-up with length along Z, so base transform is
rotX(+90): (x, y, z) -> (x, -z, y). Front/back orientation is then a yaw
around Z (per model, degrees). Probe mode prints ASCII side views to help
choose the yaw.

Usage:
  python normalize.py --probe            # prints projections, no write
  python normalize.py hatchback 0 ...    # name yaw_deg [name yaw_deg ...]
"""

import argparse
import sys

import numpy as np
import trimesh

LENGTH_TARGET = 4.7
RAW = "raw"
SIMPLE = "simple"

ROT_X90 = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])[:3, :3]


def load(name: str) -> trimesh.Trimesh:
    m = trimesh.load(f"{RAW}/{name}.glb", force="mesh")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(
            [g for g in m.geometry.values() if isinstance(g, trimesh.Trimesh)]
        )
    return m


def base_transform(m: trimesh.Trimesh) -> trimesh.Trimesh:
    m = m.copy()
    m.vertices = m.vertices @ ROT_X90.T
    m.vertices -= [m.bounds[0][0] + m.extents[0] / 2, m.bounds[0][1] + m.extents[1] / 2, m.bounds[0][2]]
    return m


def normalize(m: trimesh.Trimesh, yaw_deg: float) -> trimesh.Trimesh:
    m = m.copy()
    yaw = np.deg2rad(yaw_deg)
    rz = trimesh.transformations.rotation_matrix(yaw, [0, 0, 1])[:3, :3]
    m.vertices = m.vertices @ rz.T
    horiz = max(m.extents[0], m.extents[1])
    scale = LENGTH_TARGET / horiz
    m.apply_scale(scale)
    return m


def ascii_side(m: trimesh.Trimesh, along: str) -> str:
    """ASCII projection: along='x' -> side view (horizontal = length/y), along='y' -> front/back view (horizontal = width/x)."""
    v = m.vertices
    a = 1 if along == "x" else 0
    h_ax = (v[:, a].min(), v[:, a].max())
    v_ax = (v[:, 2].min(), v[:, 2].max())
    w, h = 110, 28
    grid = np.zeros((h, w), dtype=bool)
    xs = ((v[:, a] - h_ax[0]) / (h_ax[1] - h_ax[0]) * (w - 1)).astype(int)
    ys = ((v[:, 2] - v_ax[0]) / (v_ax[1] - v_ax[0]) * (h - 1)).astype(int)
    grid[ys, xs] = True
    lines = ["#" * w]
    for row in grid[::-1]:
        lines.append("".join("#" if c else "." for c in row))
    lines.append("#" * w)
    return "\n".join(lines)


def decimate(m: trimesh.Trimesh, target_verts: int) -> trimesh.Trimesh:
    if len(m.vertices) <= target_verts:
        return m
    try:
        frac = 1.0 - target_verts / len(m.vertices)
        out = m.simplify_quadric_decimation(frac)
        print(f"  decimated {len(m.vertices)} -> {len(out.vertices)} verts")
        return out
    except Exception as e:
        print(f"  decimation failed ({e}), keeping full mesh")
        return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("jobs", nargs="*", help="pairs of name yaw_deg")
    args = ap.parse_args()

    names = [n for n in ["hatchback", "wagon", "suv", "mpv", "transporter"]]

    if args.probe:
        for name in names:
            try:
                m = base_transform(load(name))
            except FileNotFoundError:
                print(f"--- {name}: MISSING ---")
                continue
            print(f"--- {name} extents {m.extents} ---")
            v = m.vertices
            length = v[:, 1]
            ymin, ymax = length.min(), length.max()
            lo = ymin + (ymax - ymin) * 0.10
            hi = ymin + (ymax - ymin) * 0.90
            # height of each end: median z of the last 10% of length
            tail = np.median(v[length <= lo, 2])
            head = np.median(v[length >= hi, 2])
            # width peak location (mirrors) per length bin
            bins = np.linspace(ymin, ymax, 25)
            idx = np.clip(((length - ymin) / (ymax - ymin) * 24).astype(int), 0, 24)
            width = np.array(
                [np.abs(v[idx == b, 0]).max() if (idx == b).any() else 0 for b in range(25)]
            )
            peak = float(np.argmax(width)) / 24
            print(f"  -y end z={tail:.2f}  +y end z={head:.2f}  width peak at {peak:.2f}")
            print("side view (length along x, front unknown):")
            print(ascii_side(m, "x"))
            print()
        return

    jobs = []
    for i in range(0, len(args.jobs), 2):
        jobs.append((args.jobs[i], float(args.jobs[i + 1])))

    import os
    os.makedirs(SIMPLE, exist_ok=True)
    for name, yaw in jobs:
        print(f"normalizing {name} yaw={yaw}")
        m = base_transform(load(name))
        m = normalize(m, yaw)
        m = decimate(m, 140_000)
        m.export(f"{SIMPLE}/{name}.glb")
        print(f"  saved {SIMPLE}/{name}.glb extents={m.extents} center={(m.bounds[0]+m.bounds[1])/2}")


if __name__ == "__main__":
    main()
