#!/bin/bash
# The two models the interface's picture tools use (tools/upscale_anime.py, tools/cutout_anime.py), downloaded to
# ~/.cache/voidrise-models (not in the repository: ~190 MB). Then: python3 tools/make_ui_assets.py
set -e
M="${VOIDRISE_MODELS:-$HOME/.cache/voidrise-models}"; mkdir -p "$M"; cd "$M"
pip install -q ncnn onnxruntime pillow numpy
[ -f realesrgan-x4plus-anime.bin ] || { curl -sSL -o esr.zip https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip;
  unzip -o -q -j esr.zip 'models/realesrgan-x4plus-anime.*' -d .; rm esr.zip; }
[ -f isnet-anime.onnx ] || curl -sSL -o isnet-anime.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-anime.onnx
ls -la "$M"
