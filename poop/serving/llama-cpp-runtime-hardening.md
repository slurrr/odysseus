# llama.cpp Runtime Hardening Notes

## Current sane baseline

For Gemma 31B GGUF on RTX 4090 24 GB, start conservative and then raise context/vision.

### Text-only smoke test

```bash
MODEL_FILE=/app/.cache/huggingface/hub/models--unsloth--gemma-4-31B-it-GGUF/snapshots/3f07b20fc8e73cec677713305971e534fe8c4ce3/gemma-4-31B-it-UD-Q3_K_XL.gguf
CUDA_VISIBLE_DEVICES=0 llama-server \
  --model "$MODEL_FILE" \
  --host 0.0.0.0 \
  --port 8001 \
  -ngl 99 \
  -c 4096 \
  --flash-attn on \
  --fit on \
  --cache-ram 0 \
  --parallel 1
```

### 4090 daily text profile

Good default after smoke test passes:

- Context: `32768`
- GPU layers: `99`
- GPU: `0`
- Flash attention: on
- Fit: on
- KV cache: `q8_0` for quality/stability, `q4_0` only if chasing context/VRAM
- Parallel: `1` for predictable single-user local operation
- Extra args:

```text
--parallel 1 --cache-ram 0
```

### 4090 vision profile

For image input, load the mmproj and keep microbatch large enough for image tokens:

- Context: `32768` or lower
- UBatch: `1024` if `--image-max-tokens 1024`
- Batch: `2048` is okay
- Vision: on
- KV cache: start with `q8_0`; use `q4_0` only if VRAM is tight
- Extra args:

```text
--parallel 1 --cache-ram 0 --image-max-tokens 1024
```

If keeping UBatch at `512`, then image tokens must also be lowered:

```text
--parallel 1 --cache-ram 0 --image-max-tokens 512
```

`llama-server` can abort on images when `n_ubatch < image-max-tokens`:

```text
GGML_ASSERT((cparams.causal_attn || cparams.n_ubatch >= n_tokens_all) && "non-causal attention requires n_ubatch >= n_tokens") failed
```

Known healthy signs:
- `/health` returns OK.
- `/v1/models` lists the GGUF basename.
- GPU memory is around 18-19 GiB for Q3_K_XL baseline.
- Logs show `CUDA0` and CUDA backend in `system_info`.

## Why this is less solid than vLLM

llama.cpp is very flexible, but the launch surface is more manual:
- GPU offload depends on native build flags and runtime library paths.
- Context/KV settings can silently explode memory if a fallback goes CPU-only.
- Python `llama_cpp.server` can be CPU-only even when dependency checks are green.
- Endpoint model id for GGUF is the file basename, not the HF repo id.

## Runtime rules

1. Prefer native `llama-server` over `python3 -m llama_cpp.server`.
2. Treat fallback to Python server as suspect unless it is known CUDA-built.
3. Avoid huge context until KV/cache settings are known-good.
4. Keep a saved Serve recipe for every known-good command.
5. Use `--cache-ram 0` while testing to avoid prompt-cache RAM confusion.
6. Confirm GPU use with `nvidia-smi`, not just UI green checks.

## Context and KV

- `-c 4096` is the baseline.
- `-c 32768` can work with KV quantization, but failure modes are worse.
- If trying larger contexts, record exact flags:
  - `--cache-type-k ...`
  - `--cache-type-v ...`
  - `--parallel ...`
  - `--flash-attn on/off`
  - `--fit on/off`

## Concurrency

llama-server may auto-select multiple slots:

```text
n_parallel = 4
kv_unified = true
```

This is useful for UI/research concurrency, but can increase KV memory. For Deep Research or heavy agent tool use, watch:
- VRAM
- RAM
- prompt cache
- slot count
- request failures after a long session

If unstable, test a lower parallel setting and/or lower research extraction concurrency.

## Commands

```bash
# health
docker compose exec -u odysseus odysseus curl -fsS http://127.0.0.1:8001/health

# model list
docker compose exec -u odysseus odysseus curl -fsS http://127.0.0.1:8001/v1/models

# GPU process
docker compose exec -u odysseus odysseus nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits

# startup logs
ls -ltr logs/startup | tail
```

## Open cleanup ideas

- Add a preflight guard that refuses CPU fallback when user requested GPU/offload.
- Add a UI warning if llama-server fails and command is about to fall back to `llama_cpp.server`.
- Standardize model id mapping: display friendly repo name but store/use actual `/v1/models` id.
- Add a small health card later: endpoint URL, model id, context, parallel, GPU memory, log path.
