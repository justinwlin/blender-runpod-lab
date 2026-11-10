# First render experiment

Status: prepared; GPU render has not run yet.

## Access check

The Runpod MCP connection returned live account and GPU catalog data.
The local runpodctl user command returned HTTP 401.
RUNPOD_API_KEY was absent from the local process environment.
No credential value was read, printed, or committed.

Use the authenticated MCP connection for infrastructure and direct SSH for file transfer and execution.
Do not assume MCP authentication also authenticates the CLI.

## Proposed setup

- One RTX 5090, Secure Cloud.
- Catalog price at inspection: $1.19/hour, plus storage charges.
- RTX 4090 Secure Cloud stock: NONE at inspection.
- Blender 5.0.1, Linux x64, official archive with SHA-256 verification.
- One 1600 × 1000 PNG, Cycles, OptiX, at most 128 samples.
- A generated scene with no external assets.
- Delete only the experiment pod after results are downloaded and verified.

The connected create-pod API does not expose a termination schedule.
Cleanup must be tracked explicitly; process timeout alone does not stop pod billing.
