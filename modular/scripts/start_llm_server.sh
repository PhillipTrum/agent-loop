set -euo pipefail

MODEL_PATH="${MODEL_PATH:-Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled}"
MODEL_NAME="${MODEL_NAME:-qwen3.5-27b-opus-distilled}"
PORT="${PORT:-8000}"

echo "Starting sglang server with model '$MODEL_PATH' (served as '$MODEL_NAME') on port $PORT..."
python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --trust-remote-code

# In another terminal...
# 
# curl http://localhost:8000/v1/chat/completions \
#   -H "Content-Type: application/json" \
#   -d '{
#     "model": "qwen3.5-27b-opus-distilled",
#     "messages": [
#       {"role": "system", "content": "You are a helpful assistant. Answer concisely and do not add extra reasoning unless asked."},
#       {"role": "user", "content": "Hello!"}
#     ]
#   }'