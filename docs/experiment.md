# First render experiment

Status: complete. The GPU render succeeded, the files were verified, and the pod was deleted.

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

## Region-specific follow-up

Both catalogs reported LOW RTX 5090 capacity in EU-RO-1 with CUDA 13.2.
A request pinned to that region and CUDA version still failed due to capacity.
RTX A6000 then reported NONE.
RTX PRO 4000 Blackwell reported LOW capacity in EU-RO-1 at $0.57/hour.
Its allocation succeeded on 2026-11-10 at 01:54:01 UTC.
Pod ID: `6mrcvhrbgvhqxq`.
Image: `runpod/base:1.0.2-ubuntu2404`.
The pod has a 20 GB container disk and no network volume.

The SSH proxy rejected the task key. Direct SSH became available after startup.
Direct SSH uses the public key injected through PUBLIC_KEY at creation.
Account-wide SSH keys were not changed.
The GPU reported NVIDIA RTX PRO 4000 Blackwell, driver 595.91.07, and 24467 MiB memory.

## Verified result

- Blender: 5.0.1.
- Engine: Cycles.
- Backend: OptiX.
- Enabled device: NVIDIA RTX PRO 4000 Blackwell.
- CPU device: disabled for the Cycles render.
- Resolution: 1600 × 1000.
- Maximum samples: 128, adaptive threshold 0.01.
- Render call duration: 10.569 seconds.
- Output: `results/first-light.png`.
- Editable scene: `results/first-light.blend`.
- Device and render evidence: `results/render-metadata.json` and `results/render.log`.

The image was opened and visually inspected after download.
SHA-256 checks matched the remote PNG, Blender scene, and metadata files.
The log contains an AMD HIP initialization warning. The selected NVIDIA OptiX render completed successfully.
This test did not benchmark an RTX 4090 or RTX 5090.

## Cleanup and estimated cost

Runpod accepted pod deletion with HTTP 204 at approximately 01:58:05 UTC.
A subsequent get-pod call returned HTTP 404, `pod not found`.
The allocated interval was approximately 243 seconds, including setup, render, transfer, and checks.
At $0.57/hour, that interval implies about $0.0385 in compute charges, plus storage charges.
This is an elapsed-time estimate, not a reconciled invoice.
No network volume was created. The existing account pod was not changed.

## Reusable findings

- Verify GPU capacity for the exact cloud, region, count, and CUDA constraints.
- A successful create response is stronger evidence than LOW catalog availability.
- Do not treat RUNNING as proof that SSH is ready. Wait for direct connection details.
- A pod-specific PUBLIC_KEY can authenticate direct SSH without changing account keys.
- Use the runtime GPU report for VRAM. The create response's gpu.memory field can describe host RAM.
- Blender's demo script needs no external assets and can run without a local Blender session.
- Retrieve and verify all output before deleting temporary compute.
