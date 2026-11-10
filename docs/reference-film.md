# Notes from The Edge Making-Of

Source: user-provided PDF, “The Edge Making-Of,” dated November 9, 2026.
Public artifact: https://claude.ai/artifact/QGWUAjRrzRzZWGcQzSMLfa
These are claims from the PDF, not measurements from this repository.

## Reported method

- One animated Blender scene contained 13 cameras for 13 shots.
- Python scripts built the room, laptop, objects, and animation in Blender 5.0.1.
- Each frame had explicit animation values. Workers could render frames independently.
- Ten Runpod pods rendered different frames from the same scene.
- The script distributed every Nth frame rather than requiring a separate scene for each GPU.
- Eight pods were requested. Six started. Four later pods covered the work of the two failed requests.
- The final fleet contained two RTX 5090 GPUs and eight RTX 4090 GPUs.
- Each pod received a 10 MB scene bundle and a 157 MB screen video.
- The pod decoded the video into screen textures before it rendered.
- The Mac downloaded completed frames every 2.5 minutes.
- Each pod had an 80-minute termination limit.

## Reported output and cost

- 1,329 path-traced frames at 3840 × 2160.
- Cycles with OptiX, 192 maximum samples, adaptive threshold 0.02.
- OpenImageDenoise and AgX color transform.
- RTX 5090: about 12.1 seconds per frame.
- RTX 4090: about 15.2–17.6 seconds per frame.
- Total elapsed render time: 51 minutes 43 seconds.
- Reported render cost: $5.75. This is not a current price estimate.

## Lessons to test

Start with one GPU and one still image. Verify the device and inspect the returned image.
Keep Blender versions, assets, frame numbering, and color settings identical across workers.
Bake simulations before independent frame jobs. Download and verify outputs before pod deletion.
Use explicit cost limits and cleanup. A stopped pod can still incur storage charges.
Record actual timings and distinguish render time from setup and billed time.
