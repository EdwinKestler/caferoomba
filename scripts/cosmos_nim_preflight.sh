#!/usr/bin/env bash
# Decide whether this host can run nvcr.io/nim/nvidia/cosmos3-reasoner (nano).
# Never prints secret values. Exit 0 = allowed; 2 = blocked.
set -euo pipefail

MIN_VRAM_MIB=48000
MIN_DISK_GIB=40
NEED_CC_MAJOR=8
NEED_CC_MINOR_FOR_FP8=9

fail() { echo "BLOCKED: $*" >&2; exit 2; }

command -v nvidia-smi >/dev/null || fail "nvidia-smi missing"
command -v docker >/dev/null || fail "docker missing"

vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
cc=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1)
cc_major=${cc%.*}
cc_minor=${cc#*.}
disk_gib=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')

echo "gpu=$name"
echo "vram_mib=$vram"
echo "compute_cap=$cc"
echo "disk_free_gib=$disk_gib"

if [ "${vram:-0}" -lt "$MIN_VRAM_MIB" ]; then
  fail "VRAM ${vram} MiB < ${MIN_VRAM_MIB} MiB (Cosmos3-Nano NIM floor is >56 GiB BF16 or 48 GiB FP8)"
fi
if [ "${cc_major:-0}" -lt 8 ] || { [ "$cc_major" -eq 8 ] && [ "${cc_minor:-0}" -lt "$NEED_CC_MINOR_FOR_FP8" ]; }; then
  echo "NOTE: CC $cc cannot use FP8 profiles (need >= 8.9); BF16 needs >56 GiB"
fi
if [ "${disk_gib:-0}" -lt "$MIN_DISK_GIB" ]; then
  fail "free disk ${disk_gib} GiB < ${MIN_DISK_GIB} GiB needed for NIM cache+image"
fi

echo "preflight_ok=true"
echo "still set NIM_MODEL_SIZE=nano; do not use :latest Super weights"
exit 0
