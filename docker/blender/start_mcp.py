"""Enable the baked MCP-for-Blender addon and start its socket server.

The official addon will not start under `blender -b` (it needs the GUI
timer thread). This script is meant to be launched as
`xvfb-run blender --python /opt/blender/start_mcp.py`.
"""
import os
import sys

import addon_utils
import bpy

PORT = int(os.environ.get("BLENDER_MCP_PORT", "9876"))
HOST = os.environ.get("BLENDER_MCP_HOST", "0.0.0.0")

# Make sure the baked module is importable even before preferences exist.
addon_utils.enable("blender_mcp", default_set=True, persistent=True)

prefs_owner = bpy.context.preferences.addons.get("blender_mcp")
if prefs_owner is None:
    sys.stderr.write("blender_mcp addon failed to enable\n")
    raise SystemExit(1)

prefs = prefs_owner.preferences
prefs.bind_address = HOST
prefs.allow_remote_connections = True

scene = bpy.context.scene
scene.blendermcp_port = PORT
if hasattr(scene, "blendermcp_auto_start_server"):
    scene.blendermcp_auto_start_server = True

import blender_mcp  # noqa: E402  (imported after enable)

server = blender_mcp.BlenderMCPServer(host=HOST, port=PORT)
bpy.types.blendermcp_server = server
server.start()
if not server.running:
    sys.stderr.write("BlenderMCP server failed to start\n")
    raise SystemExit(1)
print(f"MCP_READY {HOST}:{PORT}", flush=True)
