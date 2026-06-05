# llama.cpp Serving Notes

## Current working target

Model:
- HF repo: `unsloth/gemma-4-31B-it-GGUF`
- GGUF: `gemma-4-31B-it-UD-Q3_K_XL.gguf`
- Container path: `/app/.cache/huggingface/hub/models--unsloth--gemma-4-31B-it-GGUF/snapshots/3f07b20fc8e73cec677713305971e534fe8c4ce3/gemma-4-31B-it-UD-Q3_K_XL.gguf`

Known-good runtime shape:

```bash
CUDA_VISIBLE_DEVICES=0 llama-server \
  --model "$MODEL_FILE" \
  --host 0.0.0.0 \
  --port 8001 \
  -ngl 99 \
  -c 4096 \
  --flash-attn on \
  --fit on \
  --cache-ram 0
```

Notes:
- `-c 32768` can work with aggressive KV quant settings, but the failed CPU fallback run OOM-killed with a 25.6 GiB CPU KV cache.
- `--cache-ram 0` avoids llama-server prompt-cache RAM growth after test turns.
- Agent/tool mode adds a large tool harness; context usage is expected to jump compared with plain chat.

## What broke

Initial UI launch showed llama.cpp dependency as installed because `llama-cpp-python` was importable. But native CUDA `llama-server` was not present. The Cookbook bootstrap tried to build it from source.

vLLM had installed pip CUDA wheels under:

```text
/app/.local/lib/python3.12/site-packages/nvidia/cu13
```

That provided `nvcc`, so Odysseus detected CUDA, but CMake could not find the toolkit because the PyPI CUDA wheel layout is not a normal CUDA toolkit layout:

- missing `lib64`
- missing unversioned libraries like `libcudart.so`, `libcublas.so`
- `nvcc` was 13.3 while CUDA runtime headers reported 13.0, causing CCCL header compatibility failure

Observed failures:

```text
Unable to find cudart library.
Could NOT find CUDAToolkit (missing: CUDA_CUDART)
CUDA Toolkit not found
llama-server: command not found
```

Then the command fell back to `python3 -m llama_cpp.server`, which was CPU-only:

```text
load_tensors: layer 0 assigned to device CPU
...
llama_kv_cache: CPU KV buffer size = 25600.00 MiB
Killed
```

## Code changes made

Files:
- `routes/cookbook_helpers.py`
- `routes/cookbook_routes.py`

Changes:
1. Before building llama.cpp with CUDA, create a compatibility view for pip CUDA wheels:
   - set `CUDA_HOME` and `CUDAToolkit_ROOT`
   - add CUDA bin to `PATH`
   - add CUDA lib and llama.cpp build bin to `LD_LIBRARY_PATH`
   - create `lib64 -> lib`
   - create unversioned symlinks for `libcudart`, `libcublas`, `libcublasLt`, `libnvrtc`, `libnvJitLink`
2. Pass `-DCUDAToolkit_ROOT=...` to CMake.
3. Add `-DCCCL_DISABLE_CTK_COMPATIBILITY_CHECK` to `CMAKE_CUDA_FLAGS` for the pip-wheel header/compiler version skew.
4. Set `LD_LIBRARY_PATH` on every future llama.cpp launch, not only during the first source build. Without this, a previously built CUDA `llama-server` fails later with `libcudart.so.13: cannot open shared object file`.
5. Auto-register OpenAI-compatible Cookbook serves (`llama-server`, `llama_cpp.server`, `vllm serve`, `sglang.launch_server`) as `ModelEndpoint` rows, so launched text servers should appear in the model selector without manual endpoint registration.

## Verification commands

Inside the repo on the Docker host:

```bash
docker compose exec -u odysseus odysseus tmux list-sessions
docker compose exec -u odysseus odysseus curl -fsS http://127.0.0.1:8001/health
docker compose exec -u odysseus odysseus curl -fsS http://127.0.0.1:8001/v1/models
docker compose exec -u odysseus odysseus nvidia-smi
```

Expected healthy signs:

```text
server is listening on http://0.0.0.0:8001
CUDA0 : NVIDIA GeForce RTX 4090
llama-server ... ~18 GiB VRAM
```

## UI bugs / behavior still under investigation

- Cookbook serve launches did not auto-register text endpoints before the local fix; manual registration made the model selectable.
- Fixed local behavior where normal Cookbook Stop removed/tombstoned the serve card. Stop now kills the server and removes the endpoint, but leaves a `stopped` card for relaunch/edit. Manual `⋮ → Remove` still deletes the card.
- Continuing an existing chat after changing launch command/context can fail while a fresh chat works. Hypotheses:
  - selected model id changed (`repo_id` vs GGUF basename from `/v1/models`)
  - endpoint id changed after manual re-registration
  - saved chat references stale endpoint/model metadata
- The context meter includes the agent/tool harness, not just user-visible characters.

## Next likely fixes

1. Make endpoint identity stable for a fixed host/port (`http://localhost:8001/v1`) and update cached model ids when the served model changes.
2. Check whether chat sessions persist endpoint id + model id and whether they survive endpoint re-registration.
3. Add a small UI note: text serves are OpenAI-compatible endpoints; Cookbook now auto-adds them, but old/manual endpoints may need refresh/probe.
4. Consider a proper preset/history model distinct from ephemeral Running tasks, so users can relaunch known-good configs even after clearing finished tasks.
