# Modal deployment

Modal-native deployment of the daylight-factor inference server. It reuses the
core services in `src/` via `ServerBootstrap` — `modal_app/` is just an adapter,
the GPU equivalent of `main.py`.

## Endpoints

Same contract as the Flask server (only the base URL changes):

| Method | Path      | Container | Notes                                   |
|--------|-----------|-----------|-----------------------------------------|
| POST   | `/run`    | GPU (L4)  | multipart: `file`, `model`, `cond_vec?` |
| GET    | `/spec`   | CPU       | `?model=<name>`                         |
| GET    | `/status` | CPU       | health / version                        |

GPU inference and the cheap metadata endpoints run on separate containers, so a
spec lookup or health check never starts an L4.

## One-time setup

1. Install + authenticate:
   ```
   pip install modal && modal token new
   ```
2. Create the Scaleway secret (used at build time for baking models and at
   runtime for download-on-demand):
   ```
   modal secret create upskiller-scaleway \
     SCW_ACCESS_KEY=... \
     SCW_SECRET_KEY=... \
     MODEL_URL_TEMPLATE='s3://daylight-factor/models/{name}.onnx' \
     SPEC_URL_TEMPLATE='s3://daylight-factor/models/{name}/spec.json'
   ```
   The secret name must match `config.SECRET_NAME`.
3. List the models to bake into the image in `config.BAKED_MODELS`. Anything not
   baked still works via download-on-demand (slower first request).

## Deploy

Run from the repository root (paths in `image.py` are relative to cwd):

```
modal serve modal_app/app.py     # dev: temporary URL, hot reload
modal deploy modal_app/app.py    # production
```

## Storage model (hybrid)

Baked models are downloaded into `/models` at build time for fast cold starts.
At runtime `checkpoints_dir` points at `/models`; non-baked models are fetched
on demand into the same (writable, ephemeral) directory and LRU-cached in memory
per container — identical semantics to the Flask `./checkpoints` cache.

**Pre-built optimized graph.** After baking, a second build step runs ORT graph
optimization (`ORT_ENABLE_ALL`) on a GPU and writes `{name}.opt.onnx` next to
each model. At runtime the optimized graph is loaded with optimizations disabled,
so session init skips the transformation passes — this only shortens init; the
per-inference CUDA memory transfer is unchanged. The optimized graph is
hardware-specific: regenerate it (rebuild the image) if `config.GPU` changes.
Non-baked (download-on-demand) models have no `.opt.onnx` and are optimized at
load time as before.

## To verify on first deploy

- **CUDA provider loads.** `@modal.enter()` logs `ONNX providers available: [...]`
  and warns if it falls back to CPU. If `CUDAExecutionProvider` is missing, the
  `onnxruntime-gpu` wheel's CUDA/cuDNN libs aren't resolving — pin a matching
  `onnxruntime-gpu` version or add the CUDA libs to the image.
- **Proxy auth.** Endpoints use `requires_proxy_auth=True`; create a proxy-auth
  token in the Modal dashboard and send it as `Modal-Key` / `Modal-Secret`
  headers. Set `config.REQUIRES_PROXY_AUTH = False` for open endpoints.
- **Output parity.** Compare `/run` output against the Docker server using the
  images in `example/`.
