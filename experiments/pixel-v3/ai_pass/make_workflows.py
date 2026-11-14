"""Generate the ComfyUI API-format workflows for the Pixel AI realism pass.
python make_workflows.py <out_dir> [key=value ...]   (see P below for the parameters)
Writes: wan_vace_full.api.json, wan_vace_refine.api.json, wan_vace_keyframe.api.json, sdxl_frame_refine.api.json"""
import json, sys
P = dict(frames='/workspace/pc/v3/post/final_frames', depth='/workspace/ai/depth', ref='/workspace/ai/ref', key='/workspace/ai/key',
         start=160, length=81, width=1280, height=720, seed=7, prefix='wan', denoise_from=2, steps=4,
         canny_lo=0.08, canny_hi=0.22, depth_strength=1.0, line_strength=0.7, sd_denoise=0.42, sd_steps=28, sd_cfg=5.5, lora=0.8, tile_strength=0.0, tile_end=0.6,
         depth_end=1.0, line_end=0.9, sd_prompt='v2', matte='', mask_grow=20, mask_blur=12)
for a in sys.argv[2:]:
    k, v = a.split('=', 1); P[k] = type(P[k])(v) if not isinstance(P[k], str) else v
OUT = sys.argv[1]
POS = ("A small fluffy calico kitten with soft, fine, realistic fur and delicate white whiskers, large glossy green eyes, pink nose, "
       "white muzzle, chest and paws, clean black and orange patches, on a dark walnut desk beside a glowing mushroom lamp, "
       "warm golden-hour window light, natural soft shine on the fur, shallow depth of field, cinematic, photorealistic, highly detailed")
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，"
       "画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走, "
       "plastic, rubber, vinyl toy, smooth 3d render, extra limbs, deformed, text, watermark")

def base(g):
    g['clip'] = {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'type': 'wan', 'device': 'default'}}
    g['pos'] = {'class_type': 'CLIPTextEncode', 'inputs': {'text': POS, 'clip': ['clip', 0]}}
    g['neg'] = {'class_type': 'CLIPTextEncode', 'inputs': {'text': NEG, 'clip': ['clip', 0]}}
    g['vae'] = {'class_type': 'VAELoader', 'inputs': {'vae_name': 'wan_2.1_vae.safetensors'}}
    g['src'] = {'class_type': 'VHS_LoadImagesPath', 'inputs': {'directory': P['frames'], 'image_load_cap': P['length'], 'skip_first_images': P['start'], 'select_every_nth': 1}}
    g['src_s'] = {'class_type': 'ImageScale', 'inputs': {'image': ['src', 0], 'upscale_method': 'lanczos', 'width': P['width'], 'height': P['height'], 'crop': 'disabled'}}
    g['line'] = {'class_type': 'Canny', 'inputs': {'image': ['src_s', 0], 'low_threshold': P['canny_lo'], 'high_threshold': P['canny_hi']}}
    g['dep'] = {'class_type': 'VHS_LoadImagesPath', 'inputs': {'directory': P['depth'], 'image_load_cap': P['length'], 'skip_first_images': P['start'], 'select_every_nth': 1}}
    g['dep_s'] = {'class_type': 'ImageScale', 'inputs': {'image': ['dep', 0], 'upscale_method': 'bilinear', 'width': P['width'], 'height': P['height'], 'crop': 'disabled'}}

def model(g, which):
    g[f'unet_{which}'] = {'class_type': 'UnetLoaderGGUF', 'inputs': {'unet_name': f'Wan2.2-VACE-Fun-A14B-{which}-noise-Q5_K_M.gguf'}}
    g[f'lora_{which}'] = {'class_type': 'LoraLoaderModelOnly', 'inputs': {'model': [f'unet_{which}', 0], 'lora_name': f'wan2.2_t2v_lightx2v_4steps_lora_v1.1_{which}_noise.safetensors', 'strength_model': 1.0}}
    g[f'ms_{which}'] = {'class_type': 'ModelSamplingSD3', 'inputs': {'model': [f'lora_{which}', 0], 'shift': 5.0}}

def vace(g, ref):
    """two chained VACE conditionings: exact depth from Blender, then canny line art of the render (keeps the patch edges)"""
    a = {'positive': ['pos', 0], 'negative': ['neg', 0], 'vae': ['vae', 0], 'width': P['width'], 'height': P['height'], 'length': P['length'], 'batch_size': 1,
         'strength': P['depth_strength'], 'control_video': ['dep_s', 0]}
    b = {'positive': ['vace_d', 0], 'negative': ['vace_d', 1], 'vae': ['vae', 0], 'width': P['width'], 'height': P['height'], 'length': P['length'], 'batch_size': 1,
         'strength': P['line_strength'], 'control_video': ['line', 0]}
    if ref:
        g['ref'] = {'class_type': 'VHS_LoadImagesPath', 'inputs': {'directory': P['ref'], 'image_load_cap': 1, 'skip_first_images': 0, 'select_every_nth': 1}}
        g['ref_s'] = {'class_type': 'ImageScale', 'inputs': {'image': ['ref', 0], 'upscale_method': 'lanczos', 'width': P['width'], 'height': P['height'], 'crop': 'center'}}
        a['reference_image'] = ['ref_s', 0]; b['reference_image'] = ['ref_s', 0]
    g['vace_d'] = {'class_type': 'WanVaceToVideo', 'inputs': a}; g['vace_l'] = {'class_type': 'WanVaceToVideo', 'inputs': b}

def ks(model_node, latent, start, end, add_noise, leftover):
    return {'class_type': 'KSamplerAdvanced', 'inputs': {'model': [model_node, 0], 'add_noise': add_noise, 'noise_seed': P['seed'], 'steps': P['steps'], 'cfg': 1.0,
            'sampler_name': 'euler', 'scheduler': 'simple', 'positive': ['vace_l', 0], 'negative': ['vace_l', 1], 'latent_image': latent,
            'start_at_step': start, 'end_at_step': end, 'return_with_leftover_noise': leftover}}

# A1: full VACE generation from controls + a reference image (high-noise then low-noise, lightx2v 4 steps)
g = {}; base(g); model(g, 'high'); model(g, 'low'); vace(g, True)
g['s_high'] = ks('ms_high', ['vace_l', 2], 0, P['steps'] // 2, 'enable', 'enable')
g['s_low'] = ks('ms_low', ['s_high', 0], P['steps'] // 2, P['steps'], 'disable', 'disable')
g['trim'] = {'class_type': 'TrimVideoLatent', 'inputs': {'samples': ['s_low', 0], 'trim_amount': ['vace_l', 3]}}
g['dec'] = {'class_type': 'VAEDecode', 'inputs': {'samples': ['trim', 0], 'vae': ['vae', 0]}}
g['save'] = {'class_type': 'SaveImage', 'inputs': {'images': ['dec', 0], 'filename_prefix': P['prefix'] + '_full/f'}}
json.dump(g, open(f'{OUT}/wan_vace_full.api.json', 'w'), indent=1, ensure_ascii=False)

# A2: VACE refine. Start from the render itself (encoded), add noise and run only the last steps on the low-noise model,
# with the same depth + line controls. Colours, patches, motion and camera come from the render; the model adds fur and shine.
g = {}; base(g); model(g, 'low'); vace(g, False)
g['enc'] = {'class_type': 'VAEEncode', 'inputs': {'pixels': ['src_s', 0], 'vae': ['vae', 0]}}
half = P['steps'] // 2
if P['denoise_from'] < half:      # stronger refine: the first steps are above the low-noise model's range, so the high-noise model takes them
    model(g, 'high')
    g['s_high'] = ks('ms_high', ['enc', 0], P['denoise_from'], half, 'enable', 'enable')
    g['s_low'] = ks('ms_low', ['s_high', 0], half, P['steps'], 'disable', 'disable')
else:
    g['s_low'] = ks('ms_low', ['enc', 0], P['denoise_from'], P['steps'], 'enable', 'disable')
g['dec'] = {'class_type': 'VAEDecode', 'inputs': {'samples': ['s_low', 0], 'vae': ['vae', 0]}}
g['save'] = {'class_type': 'SaveImage', 'inputs': {'images': ['dec', 0], 'filename_prefix': P['prefix'] + '_refine/f'}}
json.dump(g, open(f'{OUT}/wan_vace_refine.api.json', 'w'), indent=1, ensure_ascii=False)

# A3: VACE with a start frame. The first control frame is a furry key frame (made by the SDXL workflow from the same render
# frame) marked 'keep'; the remaining control frames are the Blender depth pass marked 'generate'. The key frame is also the
# reference image. Fur and patches come from the key frame, motion and camera from the depth.
g = {}; base(g); model(g, 'high'); model(g, 'low')
g['key'] = {'class_type': 'VHS_LoadImagesPath', 'inputs': {'directory': P['key'], 'image_load_cap': 1, 'skip_first_images': 0, 'select_every_nth': 1}}
g['key_s'] = {'class_type': 'ImageScale', 'inputs': {'image': ['key', 0], 'upscale_method': 'lanczos', 'width': P['width'], 'height': P['height'], 'crop': 'disabled'}}
g['dep']['inputs'].update(image_load_cap=P['length'] - 1, skip_first_images=P['start'] + 1)
g['ctl'] = {'class_type': 'ImageBatch', 'inputs': {'image1': ['key_s', 0], 'image2': ['dep_s', 0]}}
g['m0'] = {'class_type': 'EmptyImage', 'inputs': {'width': P['width'], 'height': P['height'], 'batch_size': 1, 'color': 0}}
g['m1'] = {'class_type': 'EmptyImage', 'inputs': {'width': P['width'], 'height': P['height'], 'batch_size': P['length'] - 1, 'color': 16777215}}
g['mb'] = {'class_type': 'ImageBatch', 'inputs': {'image1': ['m0', 0], 'image2': ['m1', 0]}}
g['mask'] = {'class_type': 'ImageToMask', 'inputs': {'image': ['mb', 0], 'channel': 'red'}}
g['vace_l'] = {'class_type': 'WanVaceToVideo', 'inputs': {'positive': ['pos', 0], 'negative': ['neg', 0], 'vae': ['vae', 0], 'width': P['width'], 'height': P['height'],
               'length': P['length'], 'batch_size': 1, 'strength': P['depth_strength'], 'control_video': ['ctl', 0], 'control_masks': ['mask', 0], 'reference_image': ['key_s', 0]}}
g['s_high'] = ks('ms_high', ['vace_l', 2], 0, P['steps'] // 2, 'enable', 'enable')
g['s_low'] = ks('ms_low', ['s_high', 0], P['steps'] // 2, P['steps'], 'disable', 'disable')
g['trim'] = {'class_type': 'TrimVideoLatent', 'inputs': {'samples': ['s_low', 0], 'trim_amount': ['vace_l', 3]}}
g['dec'] = {'class_type': 'VAEDecode', 'inputs': {'samples': ['trim', 0], 'vae': ['vae', 0]}}
g['save'] = {'class_type': 'SaveImage', 'inputs': {'images': ['dec', 0], 'filename_prefix': P['prefix'] + '_key/f'}}
json.dump(g, open(f'{OUT}/wan_vace_keyframe.api.json', 'w'), indent=1, ensure_ascii=False)

# B: per-frame SDXL img2img with the FluffyStyle LoRA and a union ControlNet (depth, canny lines, tile for colour lock).
# With matte=<dir> only the cat region is repainted (latent noise mask from the Blender cat matte, grown and blurred) and the
# untouched render is composited back outside it. Run one frame per prompt (length=1) so every frame gets the same noise.
SD_PROMPTS = {
 'v1': "FluffyStyle, " + POS,
 'v2': ("FluffyStyle, macro photograph of a real fluffy calico kitten, dense soft fur with visible individual hairs, fuzzy fur edges, long white whiskers, "
        "glossy green eyes, pink nose, white muzzle chest and paws, black and orange fur patches, on a dark walnut desk, warm golden hour light, "
        "shallow depth of field, photorealistic, 85mm, highly detailed fur"),
 'toy': ("FluffyStyle, a cute miniature toy kitten, soft rounded plush figurine with fluffy flocked fur, chubby rounded body, short stubby legs, big round head, "
         "large glossy green eyes, tiny pink nose, white whiskers, calico coat: white muzzle, chest and paws with black and orange patches, soft fuzzy silhouette, "
         "adorable collectible mini toy cat, macro product photo on a dark walnut desk, warm golden hour light, shallow depth of field, highly detailed soft fur")}
SD_NEG = "hard plastic, vinyl, glossy smooth surface, blocky, angular, low poly, 3d render, cartoon drawing, blurry, deformed, extra limbs, extra tail, text, watermark, low quality"
g = {}
g['ckpt'] = {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}}
g['lora'] = {'class_type': 'LoraLoader', 'inputs': {'model': ['ckpt', 0], 'clip': ['ckpt', 1], 'lora_name': 'FluffyStyleXL.safetensors', 'strength_model': P['lora'], 'strength_clip': P['lora']}}
g['pos'] = {'class_type': 'CLIPTextEncode', 'inputs': {'text': SD_PROMPTS[P['sd_prompt']], 'clip': ['lora', 1]}}
g['neg'] = {'class_type': 'CLIPTextEncode', 'inputs': {'text': SD_NEG if P['sd_prompt'] == 'toy' else "plastic, rubber, vinyl, smooth 3d render, cartoon, blurry, deformed, extra limbs, text, watermark, low quality", 'clip': ['lora', 1]}}
def load(name, directory, method):
    g[name] = {'class_type': 'VHS_LoadImagesPath', 'inputs': {'directory': directory, 'image_load_cap': P['length'], 'skip_first_images': P['start'], 'select_every_nth': 1}}
    g[name + '_s'] = {'class_type': 'ImageScale', 'inputs': {'image': [name, 0], 'upscale_method': method, 'width': P['width'], 'height': P['height'], 'crop': 'disabled'}}
load('src', P['frames'], 'lanczos'); load('dep', P['depth'], 'bilinear')
g['line'] = {'class_type': 'Canny', 'inputs': {'image': ['src_s', 0], 'low_threshold': P['canny_lo'], 'high_threshold': P['canny_hi']}}
g['cn'] = {'class_type': 'ControlNetLoader', 'inputs': {'control_net_name': 'diffusion_pytorch_model_promax.safetensors'}}
last = ('pos', 'neg', 0, 0)
for tag, typ, img, strength, end in (('d', 'depth', 'dep_s', P['depth_strength'], P['depth_end']), ('l', 'canny/lineart/anime_lineart/mlsd', 'line', P['line_strength'], P['line_end']),
                                     ('t', 'tile', 'src_s', P['tile_strength'], P['tile_end'])):
    if strength <= 0: continue
    g['cn_type_' + tag] = {'class_type': 'SetUnionControlNetType', 'inputs': {'control_net': ['cn', 0], 'type': typ}}
    g['cn_' + tag] = {'class_type': 'ControlNetApplyAdvanced', 'inputs': {'positive': [last[0], last[2]], 'negative': [last[1], last[3]], 'control_net': ['cn_type_' + tag, 0],
                      'image': [img, 0], 'strength': strength, 'start_percent': 0.0, 'end_percent': end, 'vae': ['ckpt', 2]}}
    last = ('cn_' + tag, 'cn_' + tag, 0, 1)
g['enc'] = {'class_type': 'VAEEncode', 'inputs': {'pixels': ['src_s', 0], 'vae': ['ckpt', 2]}}
latent = ['enc', 0]
if P['matte']:
    load('mt', P['matte'], 'bilinear')
    g['mt_m'] = {'class_type': 'ImageToMask', 'inputs': {'image': ['mt_s', 0], 'channel': 'red'}}
    g['mt_g'] = {'class_type': 'GrowMask', 'inputs': {'mask': ['mt_m', 0], 'expand': P['mask_grow'], 'tapered_corners': True}}
    g['mt_i'] = {'class_type': 'MaskToImage', 'inputs': {'mask': ['mt_g', 0]}}
    g['mt_b'] = {'class_type': 'ImageBlur', 'inputs': {'image': ['mt_i', 0], 'blur_radius': P['mask_blur'], 'sigma': P['mask_blur'] / 2.0}}
    g['mt_f'] = {'class_type': 'ImageToMask', 'inputs': {'image': ['mt_b', 0], 'channel': 'red'}}
    g['enc_m'] = {'class_type': 'SetLatentNoiseMask', 'inputs': {'samples': ['enc', 0], 'mask': ['mt_f', 0]}}; latent = ['enc_m', 0]
g['ks'] = {'class_type': 'KSampler', 'inputs': {'model': ['lora', 0], 'seed': P['seed'], 'steps': P['sd_steps'], 'cfg': P['sd_cfg'], 'sampler_name': 'dpmpp_2m', 'scheduler': 'karras',
           'positive': [last[0], last[2]], 'negative': [last[1], last[3]], 'latent_image': latent, 'denoise': P['sd_denoise']}}
g['dec'] = {'class_type': 'VAEDecode', 'inputs': {'samples': ['ks', 0], 'vae': ['ckpt', 2]}}
outimg = ['dec', 0]
if P['matte']:
    g['comp'] = {'class_type': 'ImageCompositeMasked', 'inputs': {'destination': ['src_s', 0], 'source': ['dec', 0], 'x': 0, 'y': 0, 'resize_source': False, 'mask': ['mt_f', 0]}}; outimg = ['comp', 0]
g['save'] = {'class_type': 'SaveImage', 'inputs': {'images': outimg, 'filename_prefix': P['prefix'] + '_sdxl/f'}}
json.dump(g, open(f'{OUT}/sdxl_frame_refine.api.json', 'w'), indent=1, ensure_ascii=False)
json.dump(P, open(f'{OUT}/params.json', 'w'), indent=1)
print('wrote 3 workflows to', OUT, P)
