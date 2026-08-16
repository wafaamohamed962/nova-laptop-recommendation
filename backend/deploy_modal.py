"""
Modal deployment for a self-hosted, OpenAI-compatible Qwen3 inference server.

Serves Qwen/Qwen3-4B-Instruct-2507 via vLLM's built-in OpenAI-compatible API
server, running inside a Modal container with a GPU attached. The 4B size is
deliberate: it's plenty for the Evaluator Agent's slot-extraction workload
(see app/agents/evaluator.py), fits comfortably on a single A10G, and is far
cheaper to run than a 7B+ model.

Deploy:
    modal deploy deploy_modal.py

Dev/hot-reload:
    modal serve deploy_modal.py

Requires a Modal secret named "laptop-recommender-vllm-key" containing VLLM_API_KEY,
e.g.:
    modal secret create laptop-recommender-vllm-key VLLM_API_KEY=<your-chosen-key>
"""

import modal

MODEL_NAME = "Qwen/Qwen3-4B-Instruct-2507"
MODEL_REVISION = "main"

VLLM_PORT = 8000
GPU_CONFIG = "A10G"  # bump to "A100-40GB" if you need more headroom/throughput
MAX_MODEL_LEN = 8192

vllm_image = (
    # Not debian_slim: pip-installed torch/nvidia-* packages only provide CUDA
    # *runtime* libraries. vLLM's JIT kernel compilation needs the actual nvcc
    # compiler (RuntimeError: Could not find nvcc and default cuda_home
    # ='/usr/local/cuda' doesn't exist), which only a CUDA "devel" base image
    # provides. 12.4 matches the cu124 wheels vllm/torch resolve to.
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
    .pip_install(
        # NOT pinned to an exact old version: vllm==0.8.5 avoids the flashinfer
        # crash below, but its tokenizer code is incompatible with the modern
        # `transformers` this environment's index resolves alongside it
        # (AttributeError: Qwen2Tokenizer has no attribute
        # all_special_tokens_extended) -- old vllm + new transformers don't
        # match. Left as an open floor so pip resolves a vllm/transformers
        # pair that's actually mutually compatible; the flashinfer issue is
        # handled separately below instead of by downgrading vllm.
        "vllm>=0.8.5,<1.0",
        "huggingface_hub[hf_transfer]",
    )
    # flashinfer (a vllm dependency) is NOT safely removable: vLLM's sampler
    # init unconditionally imports it to check availability, with no
    # graceful fallback if it's missing (confirmed -- removing it entirely
    # just moves the crash to `ModuleNotFoundError: No module named
    # 'flashinfer'` in vllm/v1/sample/ops/topk_topp_sampler.py instead).
    #
    # The actual bug is narrower: some flashinfer files use `array.array[int]`
    # as a runtime-evaluated type annotation, which needs Python 3.13's
    # subscriptable array.array and raises `TypeError: type 'array.array' is
    # not subscriptable` on this container's Python 3.11 (first seen in
    # flashinfer/comm/fd_exchange.py, imported transitively from an unrelated
    # model's warmup code). `from __future__ import annotations` defers all
    # annotation evaluation in a module to strings, sidestepping this without
    # needing the actual multi-GPU comm feature it guards (irrelevant on our
    # single A10G anyway). Patched into every flashinfer file with this
    # pattern, not just the one seen so far, since there may be others.
    .run_commands(
        "for f in $(grep -rl 'array\\.array\\[' "
        "/usr/local/lib/python3.11/site-packages/flashinfer/ 2>/dev/null); do "
        "sed -i '1i from __future__ import annotations' \"$f\"; done"
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
        "--served-model-name", "qwen3-4b-instruct",
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--api-key", api_key,
        "--max-model-len", str(MAX_MODEL_LEN),
        "--gpu-memory-utilization", "0.90",
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",
        # Skips vLLM's torch.compile-based graph compilation. Needed here
        # because that path eagerly imports flashinfer's all-reduce fusion
        # pass, which is broken on Python 3.11 (uses array.array[int]
        # subscripting, a Python 3.13+ feature) -- and irrelevant anyway on
        # a single GPU with no multi-rank all-reduce to fuse.
        "--enforce-eager",
    ]
    subprocess.Popen(cmd)


@app.local_entrypoint()
def health_check():
    """Run with: modal run deploy_modal.py"""
    print(f"App '{app.name}' configured to serve {MODEL_NAME} on GPU={GPU_CONFIG}.")
    print("Deploy with: modal deploy deploy_modal.py")
    print("Then find the endpoint URL with: modal app list")
