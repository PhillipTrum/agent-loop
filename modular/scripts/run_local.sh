set -euo pipefail

MODEL_PATH="${MODEL_PATH:-Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled}"
MODEL_NAME="${MODEL_NAME:-qwen3.5-27b-opus-distilled}"
PORT="${PORT:-8000}"
PROVIDER="${PROVIDER:-openai}"

echo "Starting sglang server with model '$MODEL_PATH' (served as '$MODEL_NAME') on port $PORT..."
python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --trust-remote-code &

echo "Waiting for server to be ready..."
until curl -s http://localhost:"$PORT"/v1/models > /dev/null 2>&1; do
    sleep 2
done

echo "Server ready. Launching agent loop..."
python3 __main__.py --provider "$PROVIDER" --model "$MODEL_NAME" --base-url http://localhost:"$PORT"/v1
