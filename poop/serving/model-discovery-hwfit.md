# Cookbook Model Discovery / Hardware Fit Notes

## Relevant files

- `routes/hwfit_routes.py`
- `services/hwfit/hardware.py`
- `services/hwfit/fit.py`
- `services/hwfit/models.py`
- `services/hwfit/profiles.py`
- `static/js/cookbook-hwfit.js`
- `static/js/cookbook.js`
- tests around `tests/test_hwfit_*`

## Current behavior

Cookbook has a strong model discovery UX, but hardware detection/ranking can be wrong for this workstation.

Observed user state:
- RTX 4090 is available to Docker and llama.cpp/vLLM can use it.
- UI hardware autodetect did not reliably detect/filter as expected.
- Manual hardware override was set to 24 GB VRAM, but recommendations still did not feel well-filtered.

## Route behavior to understand

`/api/hwfit/system`:
- returns detected hardware from `services.hwfit.hardware.detect_system(...)`.
- supports `fresh=true` to bypass cache.

`/api/hwfit/models`:
- starts with detected system.
- can apply manual hardware via query params:
  - `manual_mode=gpu|ram`
  - `manual_gpu_count`
  - `manual_vram_gb`
  - `manual_ram_gb`
  - `manual_backend=cuda|rocm|metal|cpu_x86|cpu_arm`
- can ignore detected GPU/RAM.
- then ranks via `services.hwfit.fit.rank_models(...)`.

Manual GPU mode is intended to REPLACE detected hardware, not add to it.

## Hypotheses for bad filtering

1. The frontend may not be passing manual override params to all discovery calls.
2. Detection cache may be stale unless `fresh=true` or Rescan is used.
3. Ranking may still include partial-offload models that technically fit via RAM/CPU even when user expects GPU-only fit.
4. VRAM fit math may use total VRAM vs per-GPU VRAM differently depending on `gpu_count`, `gpu_group`, or `gpu_only`.
5. Catalog metadata may be too optimistic or not aligned with real GGUF/vLLM memory behavior.

## Commands / checks

Inside repo:

```bash
# Raw detected hardware
curl 'http://127.0.0.1:7000/api/hwfit/system?fresh=true'

# Manual 1x 24GB CUDA ranking
curl 'http://127.0.0.1:7000/api/hwfit/models?manual_mode=gpu&manual_gpu_count=1&manual_vram_gb=24&manual_backend=cuda&fresh=true&limit=20'

# Profiles for a specific model
curl 'http://127.0.0.1:7000/api/hwfit/profiles?model=unsloth/gemma-4-31B-it-GGUF&fresh=true'
```

Authenticated browser/session may be required for these API calls.

## Desired behavior

- Hardware panel should clearly say whether it is using detected or manual/simulated hardware.
- Manual 24 GB CUDA should strongly prioritize models that actually fit/usefully run on a 24 GB 4090.
- Filters should distinguish:
  - fully GPU-resident
  - partial offload
  - CPU/RAM only
  - likely too slow / not recommended
- Serve profile generation should produce conservative llama.cpp defaults for 24 GB cards.

## Next test plan

1. Capture the actual JSON from `/api/hwfit/system?fresh=true` on this machine.
2. Capture `/api/hwfit/models` with manual 24 GB CUDA and compare top 20 recommendations.
3. Trace frontend params from `static/js/cookbook-hwfit.js` to make sure manual settings are sent.
4. If ranking is too permissive, adjust UI labels/filters before changing fit math.
