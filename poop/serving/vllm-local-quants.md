# vLLM Local Quant Notes

## gemma-4-12b-it-fp8-block failure

Log: `logs/startup/gemma-4-12b-it-fp8-block-serve-70f8efe6.log`

Observed launch:

```text
vLLM 0.22.0 in that log
model=/models/local/quants/llm-compressor-artifacts/gemma-4-12b-it-fp8-block
max_model_len=8192
gpu_memory_utilization=0.9
kv_cache_dtype=fp8
max_num_seqs=8
quantization=compressed-tensors
architecture=TransformersMultiModalForCausalLM / Gemma4UnifiedForConditionalGeneration
```

Key warnings/errors:

```text
TransformersMultiModalForCausalLM has no vLLM implementation, falling back to Transformers implementation.
Selected TritonFp8BlockScaledMMKernel for CompressedTensorsW8A8Fp8
AssertionError: assert A.shape[-1] == B.shape[-1]
```

Interpretation:
- This is not an OOM and not primarily a dependency install issue.
- vLLM is falling back to Transformers for Gemma4 unified multimodal architecture.
- The compressed-tensors W8A8 FP8 block kernel then asserts during startup profiling/dummy run.
- Updating vLLM may help eventually, but current local stack still reports this path as unsupported/brittle.

Immediate things to try:
1. Try the dynamic FP8 artifact instead of block FP8: `gemma-4-12b-it-fp8-dynamic`.
2. If testing block FP8 again, use conservative args:
   ```text
   --enforce-eager --max-num-seqs 1 --kv-cache-dtype auto --gpu-memory-utilization 0.85
   ```
   This may avoid compile/cudagraph issues, but may not fix the underlying block kernel shape assert.
3. If vLLM still fails, use a vLLM-native supported model/quant or a GGUF build through llama.cpp.

Note: After updating packages, create a fresh serve log; the old log shows vLLM `0.22.0`, while current installed package may be newer.
