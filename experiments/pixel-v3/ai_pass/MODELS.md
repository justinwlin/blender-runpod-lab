# Models, LoRAs and nodes used by the AI realism pass

Everything is downloaded by [`setup_comfy.sh`](setup_comfy.sh) (`wan`, `sdxl` or `all`). Revisions are the Hugging Face repo heads on 14 Nov 2026, when the files were downloaded; the script does not pin them.

| What | Repo (revision) | File | Size | Target folder under `ComfyUI/models/` | Licence |
| --- | --- | --- | --- | --- | --- |
| Wan2.2 VACE-Fun A14B, low noise, Q5_K_M GGUF | [QuantStack/Wan2.2-VACE-Fun-A14B-GGUF](https://huggingface.co/QuantStack/Wan2.2-VACE-Fun-A14B-GGUF) (`93b339260b1d`) | `LowNoise/Wan2.2-VACE-Fun-A14B-low-noise-Q5_K_M.gguf` | 13.0 GB | `diffusion_models/` | Apache-2.0 |
| Wan2.2 VACE-Fun A14B, high noise, Q5_K_M GGUF | same | `HighNoise/Wan2.2-VACE-Fun-A14B-high-noise-Q5_K_M.gguf` | 13.0 GB | `diffusion_models/` | Apache-2.0 |
| UMT5-XXL text encoder, fp8 scaled | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) (`ee6f4a40737a`) | `split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.7 GB | `text_encoders/` | Apache-2.0 |
| Wan 2.1 VAE | same | `split_files/vae/wan_2.1_vae.safetensors` | 0.25 GB | `vae/` | Apache-2.0 |
| lightx2v 4-step LoRA, T2V v1.1, high noise | same | `split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | 1.2 GB | `loras/` | Apache-2.0 |
| lightx2v 4-step LoRA, T2V v1.1, low noise | same | `split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` | 1.2 GB | `loras/` | Apache-2.0 |
| SDXL base 1.0 | [stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) (`462165984030`) | `sd_xl_base_1.0.safetensors` | 6.9 GB | `checkpoints/` | OpenRAIL++ |
| ControlNet Union SDXL ProMax (depth / canny / tile) | [xinsir/controlnet-union-sdxl-1.0](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0) (`801a4a3fa3d4`) | `diffusion_pytorch_model_promax.safetensors` | 2.5 GB | `controlnet/` | Apache-2.0 |
| FluffyStyleXL LoRA (trigger word `FluffyStyle`) | [mnemic/FluffyStyleXL-SDXL-LoRA](https://huggingface.co/mnemic/FluffyStyleXL-SDXL-LoRA) (`0ab7ed500981`), also [Civitai 347734](https://civitai.com/models/347734) | `FluffyStyleXL.safetensors` | 0.23 GB | `loras/` | GPL-3.0 |

Why GGUF Q5: the pods have 50 GB disks; the fp8 high + low pair (34.7 GB) plus the text encoder and torch does not fit.

## Software

| Component | Version |
| --- | --- |
| ComfyUI | commit `eee59185f` (cloned 14 Nov 2026) |
| ComfyUI-GGUF (city96) | commit `6ea2651` |
| ComfyUI-VideoHelperSuite (Kosinkadink) | commit `4d907be` |
| Python | 3.10.12 |
| torch / torchvision | 2.11.0+cu128 / 0.26.0+cu128. torch 2.6 fails at ComfyUI start-up (`comfy_kitchen` custom-op schema error) |
| Blender (depth and matte passes) | 5.0.1 |

No other custom nodes: canny, masks, ControlNet and VACE nodes are ComfyUI core.
