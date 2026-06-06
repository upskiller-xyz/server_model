# Modal deployment

Modal-native deployment of the daylight-factor inference server. It reuses the
core services in `src/` via `ServerBootstrap` — `modal_app/` is just an adapter,
the GPU equivalent of `main.py`.

## Endpoints

Single ASGI app under one host, same contract as the Flask server (clients only
change the base URL):

| Method | Path      | Notes                                   |
|--------|-----------|-----------------------------------------|
| POST   | `/run`    | multipart: `file`, `model`, `cond_vec?` |
| GET    | `/spec`   | `?model=<name>`                         |
| GET    | `/status` | health / version                        |

All routes share one GPU (L4) container. Serving them under one host keeps a
downstream caller (e.g. the `server_lux` orchestrator, which builds
`{MODEL_SERVICE_URL}/run` and `/spec`) a config-only change — just point
`MODEL_SERVICE_URL` at the Modal URL. The trade-off is that `/spec` and `/status`
also run on the GPU container (cheap, but they start an L4).

## One-time setup

1. Install + authenticate (writes credentials to `~/.modal.toml`):
   ```
   pip install modal && modal token new
   ```
2. Configure URLs and baked models in `config.py`:
   - `BAKED_MODELS` — models to bake into the image (default: `df_default_2.0.2`).
   - `MODEL_URL_TEMPLATE` — defaults to the public Scaleway bucket over HTTPS.
   - `SPEC_URL_TEMPLATE` — set to where `spec.json` actually lives (the `/spec`
     endpoint needs this; `/run` does not).

   The default bucket is public HTTPS, so **no Scaleway credentials are needed**.

3. *(Only for a private `s3://` bucket.)* Create a Scaleway secret and point
   `config.SECRET_NAME` at it:
   ```
   modal secret create upskiller-scaleway \
     SCW_ACCESS_KEY=... \
     SCW_SECRET_KEY=...
   ```
   Then set `MODEL_URL_TEMPLATE` / `BUILD_MODEL_URL_TEMPLATE` to `s3://...` forms.

## Deploy

Run from the repository root in **module mode** (`-m`) — the package uses
relative imports, and paths in `image.py` are relative to cwd:

```
modal serve -m modal_app.app     # dev: temporary URL, hot reload
modal deploy -m modal_app.app    # production
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
