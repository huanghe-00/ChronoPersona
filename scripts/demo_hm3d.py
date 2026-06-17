#!/usr/bin/env python3
"""HM3D embodied demo: WebSocket server driving 3D navigation.

Usage:
    python scripts/demo_hm3d.py
    # Then open frontend/canvas.html in browser
"""

import asyncio
import json
import os
from datetime import datetime, timezone

import websockets

from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.contracts.schemas import (
    ActionPlan,
    EmotionState,
    EmotionLabel,
    EmbodiedState,
)
from chronopersona.embodied import HM3DAdapter, VLNAgent

DATASET_ROOT = os.path.expanduser(
    "~/projects/ChronoPersona/dataset/habitat-matterport-3dresearch/example/"
)
DEFAULT_SCENE = os.path.join(DATASET_ROOT, "00337-CFVBbU9Rsyb")

adapter = HM3DAdapter(scene_dir=DEFAULT_SCENE, agent_id="agent_0")
vln = VLNAgent(adapter=adapter)
planner = ActionPlanner()


def build_scene_objects() -> dict:
    """Return object dict for frontend dynamic rendering."""
    return {
        "sofa": {"x": 2, "y": 3, "z": 0, "label": "沙发"},
        "bed": {"x": 8, "y": 12, "z": 0, "label": "床"},
        "table": {"x": 3, "y": 2, "z": 0, "label": "桌子"},
        "chair": {"x": 5, "y": 5, "z": 0, "label": "椅子"},
        "fridge": {"x": 10, "y": 5, "z": 0, "label": "冰箱"},
        "coffee_table": {"x": 4, "y": 3, "z": 0, "label": "茶几"},
    }


def make_state_payload(percept: EmbodiedState) -> dict:
    return {
        "event": "embodied.state",
        "data": {
            "x": percept.x,
            "y": percept.y,
            "z": percept.z,
            "theta": percept.theta,
            "scene_id": percept.scene_id,
            "scene_objects": build_scene_objects(),
            "fov_objects": percept.fov_objects,
            "metadata": {"position_3d": (percept.x, percept.y, percept.z)},
        },
    }


async def push_state(websocket):
    percept = adapter.get_perception("agent_0")
    payload = make_state_payload(percept)
    await websocket.send(json.dumps(payload))


async def handler(websocket, path):
    await push_state(websocket)

    async for message in websocket:
        msg = json.loads(message)
        event = msg.get("event", "")
        data = msg.get("data", {})

        if event == "chat.message":
            text = data.get("message", "")
            branch_id = data.get("branch_id", "main")

            # VLN parsing
            goal = vln.parse_command(text)
            if goal:
                result = vln.execute_navigation(text, branch_id=branch_id)
                reply = (
                    f"已到达{goal.target_object}，"
                    f"共移动 {result.steps_taken} 步"
                    if result.success
                    else f"未能到达{goal.target_object}"
                )
                action_token = "navigate_to_object"
                reasoning = f"VLN target={goal.target_object}, success={result.success}"
            else:
                reply = f"收到：{text}（未识别导航意图）"
                action_token = "idle"
                reasoning = "No navigation pattern matched"

            # Build emotion state
            emotion = EmotionState(
                current_state=EmotionLabel.NEUTRAL,
                intensity=0.5,
                trigger_reason="demo",
                state_since=datetime.now(timezone.utc).isoformat(),
            )

            # Build action plan
            plan = ActionPlan(
                action_token=action_token,
                action_params={"target": goal.target_object if goal else ""},
                reasoning=reasoning,
            )

            # Send chat.reply
            await websocket.send(
                json.dumps(
                    {
                        "event": "chat.reply",
                        "data": {
                            "reply_text": reply,
                            "action_plan": {
                                "action_token": plan.action_token,
                                "action_params": plan.action_params,
                                "reasoning": plan.reasoning,
                            },
                            "emotion_state": {
                                "current_state": emotion.current_state.value,
                                "intensity": emotion.intensity,
                            },
                            "branch_id": branch_id,
                        },
                    }
                )
            )

            # Push embodied state after navigation
            await push_state(websocket)

        elif event == "embodied.action":
            action = data.get("action", {})
            adapter.execute_action("agent_0", action)
            await push_state(websocket)


if __name__ == "__main__":
    print("HM3D demo server starting on ws://localhost:8765/ws")
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(handler, "localhost", 8765)
    )
    asyncio.get_event_loop().run_forever()
