from pathlib import Path
import sys
import time
import torch

sys.path.insert(0, str(Path.home() / "wolf3d/Hunyuan3D-2.1/hy3dshape"))

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline

MODEL = "tencent/Hunyuan3D-2.1"
JOBS = [
    ("04-kombi.png", "wagon"),
    ("06-kompakt-suv.png", "suv"),
    ("08-van-mpv.png", "mpv"),
    ("09-transporter.png", "transporter"),
]
IN_DIR = Path.home() / "wolf3d/inputs/car-references"
OUT_DIR = Path.home() / "wolf3d/outputs/raw"

OUT_DIR.mkdir(parents=True, exist_ok=True)

print("GPU:", torch.cuda.get_device_name(0))
print("Loading Hunyuan3D model...")
t0 = time.time()
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(MODEL)
print(f"Model loaded in {time.time() - t0:.1f}s")

for img, name in JOBS:
    inp = IN_DIR / img
    outp = OUT_DIR / f"{name}.glb"
    if outp.exists():
        print(f"skip {name}: already exists")
        continue
    print(f"Generating {name} from {inp} ...")
    t1 = time.time()
    mesh = pipeline(image=str(inp))[0]
    print(f"  gen {time.time() - t1:.1f}s  verts={len(mesh.vertices)} faces={len(mesh.faces)}")
    mesh.export(outp)
    print(f"  saved {outp}")

print("DONE")
