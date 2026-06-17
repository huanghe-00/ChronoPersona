#!/usr/bin/env python3
"""Temporary Habitat-sim compatibility check for HM3D dataset."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    import habitat_sim
    print(f"[OK] habitat_sim imported, version: {habitat_sim.__version__}")
except ImportError as e:
    print(f"[FAIL] habitat_sim not installed: {e}")
    sys.exit(1)

SCENE_GLB = "/root/projects/ChronoPersona/dataset/habitat-matterport-3dresearch/example/00337-CFVBbU9Rsyb/CFVBbU9Rsyb.basis.glb"

print(f"[INFO] Testing scene: {SCENE_GLB}")

try:
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = SCENE_GLB
    sim_cfg.enable_physics = False

    agent_cfg = habitat_sim.AgentConfiguration()

    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)

    print(f"[OK] Simulator created successfully")
    print(f"[RESULT] pathfinder.is_loaded: {sim.pathfinder.is_loaded}")

    has_semantic = hasattr(sim, "semantic_scene") and sim.semantic_scene is not None
    print(f"[RESULT] has semantic_scene: {has_semantic}")

    if has_semantic and sim.semantic_scene.objects:
        print(f"[RESULT] semantic objects count: {len(sim.semantic_scene.objects)}")
    else:
        print(f"[RESULT] semantic objects count: 0 (not available)")

    print("\n[Habitat 0.2.4 can load this scene]")

except Exception as e:
    print(f"[FAIL] Failed to load scene: {type(e).__name__}: {e}")
    print("\n[Habitat 0.2.4 CANNOT load this scene — use HM3DAdapter fallback]")
    sys.exit(1)
