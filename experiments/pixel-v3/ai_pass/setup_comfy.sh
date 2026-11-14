#!/bin/sh
# setup_comfy.sh [wan|sdxl|all]: install ComfyUI + the custom nodes and models used for the Pixel AI realism pass on a pod.
# Idempotent: re-running skips what is already there. Logs to /workspace/comfy_setup.log when started with nohup.
set -e
WHAT=${1:-wan}; C=/workspace/ComfyUI; M=$C/models
cd /workspace
[ -d $C ] || git clone -q https://github.com/comfyanonymous/ComfyUI $C
python3 -m pip install -q --upgrade pip
python3 -c "import torch" 2>/dev/null || python3 -m pip install -q --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128      # ComfyUI (comfy_kitchen) needs a newer torch than 2.6
python3 -m pip install -q -r $C/requirements.txt
python3 -m pip install -q "huggingface_hub[hf_transfer]" opencv-python-headless imageio-ffmpeg gguf
for repo in city96/ComfyUI-GGUF Kosinkadink/ComfyUI-VideoHelperSuite; do
  d=$C/custom_nodes/$(basename $repo); [ -d $d ] || git clone -q https://github.com/$repo $d
  [ -f $d/requirements.txt ] && python3 -m pip install -q -r $d/requirements.txt || true
done
dl() { # dl <repo> <path in repo> <target dir>
  mkdir -p $3; f=$3/$(basename $2)
  [ -s $f ] || HF_HUB_ENABLE_HF_TRANSFER=1 python3 -c "
from huggingface_hub import hf_hub_download; import shutil, sys
p = hf_hub_download('$1', '$2', local_dir='/workspace/hf_tmp'); shutil.move(p, '$f')"
  echo "model $(du -h $f | cut -f1) $f"; }
if [ $WHAT = wan ] || [ $WHAT = all ]; then
  dl QuantStack/Wan2.2-VACE-Fun-A14B-GGUF LowNoise/Wan2.2-VACE-Fun-A14B-low-noise-Q5_K_M.gguf $M/diffusion_models
  dl QuantStack/Wan2.2-VACE-Fun-A14B-GGUF HighNoise/Wan2.2-VACE-Fun-A14B-high-noise-Q5_K_M.gguf $M/diffusion_models
  dl Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors $M/text_encoders
  dl Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan_2.1_vae.safetensors $M/vae
  dl Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors $M/loras
  dl Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors $M/loras
fi
if [ $WHAT = sdxl ] || [ $WHAT = all ]; then
  dl stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors $M/checkpoints
  dl xinsir/controlnet-union-sdxl-1.0 diffusion_pytorch_model_promax.safetensors $M/controlnet
  dl mnemic/FluffyStyleXL-SDXL-LoRA FluffyStyleXL.safetensors $M/loras          # trigger word: FluffyStyle (GPL-3.0)
fi
cd $C && git rev-parse --short HEAD | sed 's/^/comfyui commit /'
for d in custom_nodes/ComfyUI-GGUF custom_nodes/ComfyUI-VideoHelperSuite; do (cd $d && echo "$d $(git rev-parse --short HEAD)"); done
python3 -c "import torch; print('torch', torch.__version__, torch.cuda.is_available())"
df -h /workspace | tail -1
echo SETUP_DONE
