set -euo pipefail

MODEL_PATH="${MODEL_PATH:-Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled}"
MODEL_NAME="${MODEL_NAME:-qwen3.5-27b-opus-distilled}"
PORT="${PORT:-8000}"
PROVIDER="${PROVIDER:-openai}"

echo "Starting sglang server with model '$MODEL_PATH' (served as '$MODEL_NAME') on port $PORT..."
python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --tp-size 4 \
  --mem-fraction-static 0.8 \
  --served-model-name "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port "$PORT" &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null" EXIT

echo "Waiting for server to be ready..."
until curl -s http://localhost:"$PORT"/v1/models > /dev/null 2>&1; do
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "Server died."; exit 1; }
    sleep 2
done

echo "Server ready. Launching agent loop..."
python3 __main__.py --provider "$PROVIDER" --model "$MODEL_NAME" --base-url http://localhost:"$PORT"/v1
