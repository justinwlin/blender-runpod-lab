# V3_RESULT: Pixel "golden hour" short, rig-ready rebuild

Status: **done.** A 26 s, 1080p, 24 fps short of a rebuilt, rig-ready Pixel on a lived-in desk set, rendered in Cycles on five personal-account pods, graded and titled. Silent (no ElevenLabs key was configured).

## Deliverables (`/workspace/pixel-calico/out/v3/deliver/`)
| File | What |
| --- | --- |
| `pixel_golden_hour.mp4` | The film: 1920x1080, 624 frames, graded, bloom, grain, title. 207 MB master (H.264 crf 15; the grain makes it large). |
| `pixel_golden_hour_share.mp4` | Same film at crf 21, 10.6 MB. |
| `pixel_golden_hour_ungraded.mp4` | Straight encode of the rendered frames, no grade or title. |
| `final_stills_sheet.jpg` | Ten stills pulled from the graded film. |
| `pixel-v3-rigged.blend` | The model and rig alone (textures packed). |
| `pixel-golden-hour-film.blend` | Set, lights, cameras and all animation (textures packed). |
| `atlasA.png`, `atlasB.png`, `maskA.png`, `atlas_preview.jpg` | Baked 4096 calico atlases and the eye-gloss mask. |
| `gate_model_stand/midwalk/pawup/wire.jpg` | Turnaround in three poses and the wireframe view. |

Rendered frames: `out/v3/final_frames/` (624 PNGs, the set that was encoded). Gate rounds are kept, not deleted: `out/v3/gates*`, `gates_model_r4`, `gates_model_r5`, `cut_r5` to `cut_r9`, `lidfix`, `lidfix2`.

## What v3 is
- **Model:** nine all-quad parts plus two eyelids, 17,264 quads, standing pose. The head is the Hunyuan head re-topologised by shrink-wrap; ears, neck, body, legs and tail are modelled. UVs on every part, colours baked to two 4096 atlases, toe beans on the soles.
- **Rig:** deform skeleton with IK legs (Blender IK constraints, four foot targets), FK spine, head, ears and an eight-bone tail, squash and stretch through bone scale, eyelids as `Blink` shape keys.
- **Animation:** keyframed per control with Bezier interpolation and offset keys for tail and ear follow-through. Asleep, drowsy ear twitches, wake and stretch, a four-beat walk to the ball, a paw tap, crouch and pounce, batting between both paws, a look up into the window light, then lying back down under the title.
- **Set and light:** desk, lamp, plant, mug, books, notebook, shelf, framed portrait, window. Animated sun through the window with a light volume, practical lamp, AgX.
- **Cameras:** eight shots, 35 to 100 mm, f/4 to f/8, eased moves, focus on the face.
- **Finish:** bloom, warm grade, vignette, grain, title, fades (ffmpeg).

## How the gates went
Justin reviewed stills throughout. The changes that came from review: plain cylinder legs; splatter-like patches (body, then head); a "broken waist"; bulgy hips; the hard white leg/body seam (the circled hind-leg cup); shot 2 showing the back of the head; a frame where the face turned white (a head pose, not a texture fault); closed lids reading as black bulges; a grey smudge on the closed lid. The softer model was approved at 8:09 PM ET; the later items were fixed after that. Details are in `PROCESS.md`.

## What still looks amateur (honest list)
**Model**
- Only the head comes from the sculpt. Body, neck, legs and tail are smooth parametric shapes, so the cat still reads as a designed toy, not a sculpted character. There is no shoulder, elbow or hock anatomy beyond a slight bend.
- The legs are not one skin with the body. Their tops are tucked under the torso surface, which hides the rim, but a crease remains where each leg and the neck meet the torso, and it shows in close-ups (the settle shot, under the chest).
- The eyes are painted on the head surface; there are no eyeballs, so there are no eye darts and the iris cannot move. Nose and mouth are paint only; there is no mouth or expression rig.
- Ears are thin shells that still look a bit like flat triangles from the side. No fur, whiskers or fuzz.
- Paws have three toe lobes but no separate toes; the foot has no roll, so a lifted paw rotates with the shin.

**Texture**
- The body calico is a procedural pattern I invented. It is not the reference's patch layout; only the head follows the art, and with the speckles removed on request.
- The top and back of the head are grazing to every art view, so those atlas islands have some soft, stair-stepped edges (visible in `atlas_preview.jpg`).
- UVs are six cube-face islands per part: correct and low-distortion, but many seams and no hand painting.
- Closed eyelids have a slightly ragged white/black edge.

**Rig**
- No control rig: there are no custom shapes, no IK/FK switch, no pole targets, no spline tail. It is a deform skeleton posed from a script.
- Squash and stretch is whole-body bone scale; there is no lattice and no volume preservation.

**Animation**
- **I have not watched the film play.** There is no video viewer on the box, so I judged the motion from still frames and contact sheets only. Timing, spacing and arcs have not been reviewed by eye by me.
- Keys were written by a script at pose beats, not placed by an animator in the graph editor. Head tracking during the ball play is computed from the ball position.
- Feet are IK-planted during the walk, but I did not measure sliding between keys. The walk is short-legged and bouncy rather than cat-like.
- Paw-to-ball contact is approximate; in the batting section the head dips over the ball and hides the hit.
- The stand-up, pounce and lie-down have anticipation and overshoot keyed in, but the weight shift is simple (the body mostly translates).

**Shots, light, finish**
- In both wide shots Pixel is small in frame.
- The lamp dome clips to white; the light shafts are subtle; the vignette and grain are fairly heavy.
- Only shot 2 (frames 60 to 89) was re-rendered with the final eyelid. Blinks in other shots (around frames 92 to 101, 135, 330 to 338, 500 to 511, and the closing eyes at the end) use the previous lid, whose colour edge is coarser.
- No sound at all.

## Render and cost
- Cycles OptiX, 1920x1080, 192 samples with 0.02 adaptive threshold, OpenImageDenoise, AgX, motion blur, depth of field, volume.
- Frame times: about 21 to 23 s on three RTX 4090 pods, 29 s on a fourth, 37 to 40 s on the RTX A5000.
- All 624 frames took about 65 minutes wall (02:15 to 03:20 UTC on 14 Nov 2026), first on three pods, then on five after the limit was raised. Shot 2's 30 frames were re-rendered in about 8 minutes.
- Every frame was opened and checked before encoding; one frame truncated in transfer was fetched again (the bad copy is kept in `out/v3/frames_bad/`).
- Cost (billed-duration estimates, not invoices) up to 03:45 UTC: about **$7.80** for the five pods, of which the final render itself was about $3.60.

## Pods: all five left RUNNING, as instructed
| Pod | GPU | $/hr | Created (UTC) |
| --- | --- | --- | --- |
| pixel-calico-anim | RTX A5000 | 0.27 | 13 Nov 22:12 |
| pixel-calico-r2 | RTX 4090 | 0.89 | 14 Nov 01:29 |
| pixel-calico-r3 | RTX 4090 | 0.89 | 14 Nov 01:29 |
| pixel-calico-r4 | RTX 4090 | 0.89 | 14 Nov 02:30 |
| pixel-calico-r5 | RTX 4090 | 0.89 | 14 Nov 02:30 |

Together they bill about **$3.83/hr** while idle. None was terminated; Justin said he will cut them himself. `pixel-calico-r2` dropped SSH connections several times during the run. Pods named `catvid-*` on the same account are not mine and were not touched.

## Process and repo
- `PROCESS.md` has a full v3 section (pipeline, model, bake, rig, animation, set, commands, timings, what failed).
- This folder (`experiments/pixel-v3/`) holds the scripts, `README.md` with rebuild steps, and `PROCESS.md`. No media is in git.
