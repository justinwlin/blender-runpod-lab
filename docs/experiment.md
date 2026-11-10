# First render experiment

Status: prepared; two GPU allocation requests failed due to capacity. No GPU render has run yet.

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

## Allocation attempts

1. RTX 5090, Secure Cloud, EU-RO-1, one GPU: capacity error, no pod created.
2. RTX 5090, Community Cloud, one GPU: capacity error, no pod created.

The Community Cloud catalog showed LOW RTX 5090 availability at $0.69/hour.
Both clouds showed NONE for RTX 4090 at inspection.
The create API rejected both 5090 allocations despite the LOW catalog result.
The catalog is advisory; only a successful create response confirms allocation.

The private repository was created and its private status was verified.
The scene script passed Python syntax validation. The setup script passed Bash syntax validation.
These checks do not establish Blender execution or GPU output.
