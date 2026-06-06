# Modal Deployment — Performance & Cost

Performance and cost characteristics of the daylight-factor model server running
on Modal with an **Nvidia L4** GPU (see `modal_app/`).

Setup: one L4 GPU container, model `df_default_2.0.2` baked into the image with a
pre-built optimized ONNX graph (`.opt.onnx`), preloaded in `@modal.enter()`.
`scaledown_window = 300s`, `min_containers = 0` (scale to zero).

---

## Measured latency (L4)

| Scenario             | Cold-start | Execution | Total wall | Notes                                   |
|----------------------|-----------:|----------:|-----------:|-----------------------------------------|
| Warm                 |     0.000s |    0.243s |     0.243s | container already running               |
| Cold #1              |     9.418s |    0.951s |    10.369s | first container boot + first inference  |
| Cold #2              |     4.743s |    0.716s |     5.459s | subsequent cold boot                    |
| Prod cold (1st deploy) |  ~12s     |    1.06s  |    13.2s   | includes image pull onto a fresh worker |
| Prod warm            |     0.000s |    0.234s |     0.829s | 0.829s total incl. JSON transfer        |

- **Cold-start** = container boot + CUDA init + `@modal.enter()` (model preload).
  Only the first request after scale-to-zero pays it.
- **Execution** includes inference *and* serialization of the response (the full
  384×384 grid as a JSON array of floats — several MB of text). Warm inference
  proper is ~0.24s.

---

## Pricing inputs

Modal usage-based rates (from modal.com/pricing, retrieved 2026-06-06):

| Resource        | Rate                       |
|-----------------|----------------------------|
| Nvidia L4 GPU   | $0.000222 / sec ($0.7992/hr) |
| CPU (per core)  | $0.0000131 / core / sec    |
| Memory          | $0.00000222 / GiB / sec    |

Modal bills for the **wall-clock time the container is allocated** — including
cold-start boot and the `scaledown_window` idle period after the last request —
not just inference time. GPU dominates; CPU + memory add only a few percent on a
single-L4 container. The figures below are **GPU-only estimates**.

---

## Cost per request (GPU-only)

| Event                         | Billed time | Cost        |
|-------------------------------|------------:|------------:|
| Warm inference                |     0.243s  | ~$0.000054  |
| Cold request #1               |    10.369s  | ~$0.0023    |
| Cold request #2               |     5.459s  | ~$0.0012    |
| **Idle tail** (scaledown 300s)|      300s   | ~$0.067     |

Throughput (warm, sequential): ~4.1 inferences/sec → ≈ **$0.000054 per warm
inference** (~14,800 inferences per $0.80).

**Key insight:** for low/bursty traffic the *idle tail* dominates, not compute.
Every time the service spins up and then goes quiet, it stays billed for the full
`scaledown_window` (300s ≈ $0.067) before scaling to zero.

### Build-time GPU cost

The `optimize_baked_models` build step runs on an **L4** (to target the CUDA
provider), so it is billed at the GPU rate **once per image rebuild**. During
heavy `modal serve` iteration this recurs on every rebuild and can dominate dev
spend.

> **Observed:** ~$0.08 for the first 3 requests during development. The 3
> inferences were ~16s of L4; the rest was the GPU build step (re-run on each
> rebuild) plus 300s idle tails after each `modal serve` reload. This is expected
> — per-request cost collapses toward ~$0.000054 under steady traffic.

**Dev/test tips:** stop `modal serve` (Ctrl-C) when not actively testing so
containers scale down; lower `scaledown_window` while iterating; avoid
unnecessary image rebuilds (each re-runs the GPU optimization step).

---

## Monthly scenarios (estimates, GPU-only)

Assumptions stated per row; real cost depends on how clustered the traffic is.

| Scenario | Traffic | Dominant cost | Est. / month |
|----------|---------|---------------|-------------:|
| **Sporadic, scale-to-zero** | ~500 inferences/day in ~50 separate bursts | 50 idle tails/day × 300s | ~$100 |
| **Sporadic, shorter idle** | same, but `scaledown_window = 60s` | 50 idle tails/day × 60s | ~$23 |
| **Batchy, scale-to-zero** | requests arrive together, few cold starts | compute + a few idle tails | ~$5–15 |
| **Always warm** | `min_containers = 1`, any volume | 1 L4 running 24/7 | **~$583** |

Always-warm math: $0.7992/hr × 730 hr ≈ **$583/month** for one L4, with zero
cold starts and headroom for ~10M warm inferences/month.

---

## Cold-start mitigation: memory snapshots

`enable_memory_snapshot=True` is set on the inference class. Modal runs the
CPU-side init once, snapshots the container's memory, and **restores the
snapshot** on cold start instead of re-running it — cutting cold-start latency
with no idle cost. The init is split (`modal_app/app.py`):

- `@modal.enter(snap=True)` → CPU-only wiring (imports of onnxruntime/cv2,
  `ServerBootstrap.from_env`). Captured in the snapshot.
- `@modal.enter()` → GPU verify + ONNX CUDA session creation. Runs after each
  restore, since snapshots run without a GPU attached.

A CPU-only snapshot brought the restored cold start from **13.5s → ~8.9s**. The
remaining time is the GPU phase that ran post-restore: GPU re-attach + CUDA
session creation (~2.4s) + first-inference warm-up (~1.8s).

### GPU memory snapshots (alpha) — tried, disabled

Capturing the CUDA session too (`experimental_options={"enable_gpu_snapshot":
True}` + GPU warm-up in `@modal.enter(snap=True)`) was tested and **does not work
with onnxruntime-CUDA**: restoring the snapshot **segfaults** (`SIGSEGV, exit
139`). Modal retries without snapshots, but the failed restore makes the cold
start *worse* (~30s observed) before falling back.

`config.ENABLE_GPU_SNAPSHOT` is therefore **False**. We keep the clean CPU-only
snapshot (~8.9s restored cold start). To go below that, the realistic options are
`min_containers=1` (always warm, ~$583/mo) or accepting the ~8.9s cold start
(warm requests are ~0.3–0.5s).

## Tuning levers

- **`scaledown_window`** (currently 300s) — biggest cost lever for low volume.
  Lower it (e.g. 60s) to cut idle-tail cost; the trade-off is more frequent cold
  starts.
- **`min_containers`** — set to 1 only if ~9s cold starts are unacceptable and
  traffic justifies ~$583/month. For sporadic traffic, keep 0.
- **Response payload** — returning the grid as compact binary (float16 `.npy` or
  gzip) instead of a JSON float array would cut the per-request "execution" time
  (serialization + transfer), independent of GPU. Not yet implemented.
- **GPU class** — L4 is the cost/throughput sweet spot here; a smaller/cheaper
  GPU is unlikely to help given the model already runs in ~0.24s.

All numbers are estimates for capacity planning, not a billing guarantee.
