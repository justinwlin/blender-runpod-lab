# AI realism pass: results

**Stopped on request before it was finished.** One 81-frame test shot (the walk, film frames 160-240, 1280x720) was taken through the whole pipeline once. The full 26 s was never run, and nothing here was approved as final. I judged every result from still frames and contact strips; I did not watch any of the clips play.

## The pipeline that worked best (`t5_key`)

1. **Guide passes from Blender** (`depth_pass.py`, `matte_pass.py`): exact inverse depth and a cat matte for every frame, from the same scene and cameras as the render.
2. **Key frame** (`sdxl_frame_refine`, SDXL + FluffyStyle LoRA): repaint only inside the grown, blurred cat matte at denoise 0.85, with loose depth control (0.4, ends at 50%) and a tile control for colour (0.5, ends at 60%), toy-kitten prompt.
3. **Colour lock** (`colorlock.py`): inside the cat matte, take chroma from the render and pull the low-frequency luma toward the render (0.85); composite over the untouched render.
4. **Video** (`wan_vace_keyframe`, Wan2.2 VACE-Fun A14B Q5 + lightx2v 4 steps): the colour-locked key frame is control frame 1 with mask 0 (keep) and also the reference image; the other 80 control frames are the depth pass with mask 1. 301 s on an RTX 4090.
5. **Colour lock again on every output frame**, then encode (`finish_shot.sh`).

## What worked

- **Fur.** It only appears when the model is allowed to repaint: SDXL at denoise 0.75 and above, or Wan generating from a furry start frame. Wan then carries the fur through the shot with no visible frame-to-frame flicker in the strips I checked.
- **Motion and camera.** With the Blender depth pass as the VACE control (strength 1.0), the generated cat follows the render's pose and the camera move closely.
- **Scene lock.** Repainting only inside the cat matte (key frame) and compositing through the matte (video) keeps the ball, books, wall and light exactly as rendered.
- **Colour lock.** Taking chroma from the render removes the pink, green and olive casts and restores the black / orange / white patch layout, and because the render is stable the colours cannot drift over time.
- **Toy look in key frames.** Loose depth, no line control and the toy prompt give a soft, rounded, plush kitten in stills.
- **Springier walk in Blender.** `film.py` now has a toe-off, a higher passing pose, a soft reach before each footfall, a lower stance and more bounce. Checked in six half-resolution stills only.

## What did not work

- **Low-strength refine** (`t1`, `t3`, `b1`): re-noising the render to 50-75% in Wan, or SDXL img2img at denoise 0.55, returns the same smooth vinyl. No fur.
- **Two chained VACE controls plus a reference** (`t2_full`): ghosted double image with garbled legs and props. Dropped; a single control per VACE node was used afterwards.
- **Patches without a colour lock.** At the denoise needed for fur the calico layout drifts: orange spreads, black patches vanish, and the FluffyStyle LoRA pulls the fur pink; one variant went green (the eye colour in the prompt bled into the fur).
- **Tile control as the patch lock.** There is no good setting: at strength 0.7 or more, or active past about 60% of the steps, it also keeps the smooth plastic surface (no fur); below that the patches drift. That is why colour is fixed afterwards by `colorlock.py` instead.
- **Fur strength in motion.** In the Wan output the fur is softer and more flocked than in the SDXL key frame. The lightx2v speed LoRA is the likely cause; a variant without it on the low-noise stage was planned but not run.
- **Mottled patches.** The luma pull leaves light specks inside the black patches where the AI frame was brighter than the render.
- **Halo.** A faint light outline around the cat remained in the last test, even after matching the AI frame's colour to the render in a ring around the cat and tightening the matte. Not solved.
- **Stiff legs in the AI video.** The AI follows the depth pass, so stiff legs come from the Blender walk. The springier walk was written, but the re-render of that shot was only partly done (one pod's share) when work stopped, and it was never fed back through the AI pass.
- **Shape versus colour lock.** The colour lock assumes the AI cat sits where the rendered cat is. Loosening the depth control enough for a much rounder toy shape, or letting the AI redraw the legs, would put render colours in the wrong place, so "rounder" and "locked patches" pull against each other with this method.

## Not attempted

- Per-frame SDXL versus Wan for flicker: the per-frame run (`b2_sdxl`) was rendered but never assessed or colour-locked.
- Any shot other than the walk; chunking shots longer than 81 frames; the full 26 s.
- Upscaling the 720p AI cat for the 1080p film; IP-Adapter as a colour reference.
- Opening the generated UI-format workflow files in the ComfyUI editor.

## Timings and cost

| Step | Hardware | Time |
| --- | --- | --- |
| ComfyUI + Wan models install | RTX 4090 pod | about 5 min (plus a torch upgrade) |
| Depth pass, 624 frames at 1280x720 | RTX 4090 | about 4 min |
| Matte pass, 624 frames at 1920x1080 | RTX 4090 | about 10 min |
| SDXL key frame, 1280x720, 28 steps | RTX 4090 | 9-21 s |
| Wan VACE refine, 81 frames (low only / high + low) | RTX 4090 | 240 s / 268 s |
| Wan VACE full or start-frame, 81 frames, 4 steps | RTX 4090 | 301-358 s |
| Colour lock + composite, 81 frames | pod CPU | about 2 min |

RTX 4090 pods were $0.89/hr and the RTX A5000 $0.27/hr. The AI-pass tests ran for roughly two hours across up to five pods; I did not track the AI-pass share of the pod bill separately.
