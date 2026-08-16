"""
Modal deployment for a self-hosted, OpenAI-compatible Qwen2.5 inference server.

Serves Qwen/Qwen2.5-7B-Instruct via vLLM's built-in OpenAI-compatible API server,
running inside a Modal container with a GPU attached.

Deploy:
    modal deploy deploy_modal.py

Dev/hot-reload:
    modal serve deploy_modal.py

Requires a Modal secret named "laptop-recommender-vllm-key" containing VLLM_API_KEY,
e.g.:
    modal secret create laptop-recommender-vllm-key VLLM_API_KEY=<your-chosen-key>
"""

import modal

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = "main"

VLLM_PORT = 8000
GPU_CONFIG = "A10G"  # bump to "A100-40GB" if you need more headroom/throughput
MAX_MODEL_LEN = 8192

vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm==0.6.3.post1",
        "huggingface_hub[hf_transfer]==0.25.2",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

hf_cache_vol = modal.Volume.from_name("laptop-rec-hf-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("laptop-rec-vllm-cache", create_if_missing=True)

app = modal.App("laptop-recommender-llm")


@app.function(
    image=vllm_image,
    gpu=GPU_CONFIG,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    secrets=[modal.Secret.from_name("laptop-recommender-vllm-key")],
    scaledown_window=15 * 60,  # keep container warm 15 min after last request
    timeout=10 * 60,
    min_containers=0,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * 60)
def serve():
    import os
    import subprocess

    api_key = os.environ["VLLM_API_KEY"]

    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_NAME,
        "--revision", MODEL_REVISION,
        "--served-model-name", "qwen2.5-7b-instruct",
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--api-key", api_key,
        "--max-model-len", str(MAX_MODEL_LEN),
        "--gpu-memory-utilization", "0.90",
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",
    ]
    subprocess.Popen(cmd)


@app.local_entrypoint()
def health_check():
    """Run with: modal run deploy_modal.py"""
    print(f"App '{app.name}' configured to serve {MODEL_NAME} on GPU={GPU_CONFIG}.")
    print("Deploy with: modal deploy deploy_modal.py")
    print("Then find the endpoint URL with: modal app list")
