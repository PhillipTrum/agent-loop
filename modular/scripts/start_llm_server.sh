set -euo pipefail

MODEL_PATH="${MODEL_PATH:-Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled}"
MODEL_NAME="${MODEL_NAME:-qwen3.5-27b-opus-distilled}"
PORT="${PORT:-8000}"

python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --tp-size 4 \
  --mem-fraction-static 0.8 \
  --served-model-name "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port "$PORT"
