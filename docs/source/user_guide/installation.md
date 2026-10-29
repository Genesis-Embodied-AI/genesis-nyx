# Installation

The Nyx renderer plugin is distributed as two Python wheels: `gs-nyx`, the compiled renderer and scene SDK, and `gs-nyx-plugin`, the Genesis integration layer. Installing the plugin pulls in the renderer.

## Requirements

- Python 3.10, 3.11, 3.12, or 3.13
- Windows 11, or x86-64 Linux (validated on Ubuntu 22.04; manylinux 2.34+ wheels)
- [Genesis World](https://genesis-world.readthedocs.io/) 1.4.x (installed automatically by the plugin)
- A GPU build of PyTorch that matches your GPU vendor (see below). PyTorch is **not** installed automatically: Genesis leaves the choice of CUDA / ROCm variant to you.
- A GPU and driver exposing the Vulkan ray-tracing extensions (`VK_KHR_acceleration_structure`, `VK_KHR_ray_query`, `VK_KHR_ray_tracing_pipeline`). Nyx renders through Vulkan and hands its frame buffers to PyTorch through the compute API of your torch build.

### Supported GPUs

| Vendor | Compute API | PyTorch build | Notes |
|---|---|---|---|
| NVIDIA | CUDA | `torch` CUDA wheel (e.g. `cu128`) | GeForce RTX / RTX professional GPUs with a driver recent enough for the CUDA version your torch build targets. |
| AMD | ROCm (HIP) | `torch` ROCm wheel (ROCm 6.x or 7.x) | Radeon GPUs with hardware ray tracing (RDNA 2 or newer) that are on the ROCm support list. Validated on Windows 11 and Linux. On Linux the system `libdrm` / `libdrm_amdgpu` libraries must be present; the wheel preloads them at interpreter start. On Windows the wheel ships the HIP SDK runtime it needs. |

ROCm support is new in `gs-nyx` 0.1.9 / `gs-nyx-plugin` 0.1.10 and is validated on both Windows 11 and Linux. The renderer no longer bundles a CUDA runtime: the only compute API it talks to is the one already loaded by PyTorch, so a ROCm torch build drives AMD GPUs and a CUDA torch build drives NVIDIA GPUs with no change in user code. See {doc}`advanced/gpu_backends` for how the GPU is picked and paired with torch.

```{note}
Nyx cannot fall back to a CPU renderer. A CPU-only PyTorch build fails at `scene.build()` with `NyxCameraSensor requires a GPU torch build (CUDA or ROCm)`.
```

## Installing

### 1. Install PyTorch for your GPU

Pick the index that matches your vendor on the [PyTorch "get started" page](https://pytorch.org/get-started/locally/). For example:

```bash
# NVIDIA, CUDA 12.8
pip install torch --index-url https://download.pytorch.org/whl/cu128

# AMD, ROCm 6.4
pip install torch --index-url https://download.pytorch.org/whl/rocm6.4
```

### 2. Install the plugin

```bash
pip install gs-nyx-plugin
```

This installs `gs-nyx`, `genesis-world` (1.4.x), `numpy` and `pydantic` as dependencies.

To pin a specific version (recommended for reproducibility):

```bash
pip install "gs-nyx-plugin==0.1.10"
```

### 3. Headless Linux extras

Genesis touches OpenGL during scene setup even when every frame is rendered by Nyx. On a headless Ubuntu machine install the Mesa user-space libraries once:

```bash
sudo apt-get install -y libglu1-mesa libegl-mesa0 libgl1-mesa-dev
```

## Verifying the install

```python
import torch
import gs_nyx

print(gs_nyx.__version__)
print("GPU backend:", "ROCm" if torch.version.hip else "CUDA", torch.cuda.is_available())
```

`torch.cuda.is_available()` must print `True` on both vendors: PyTorch exposes ROCm devices through the same `torch.cuda` namespace. If it prints `False`, the installed torch is a CPU build, or the driver is missing.

For a full end-to-end check, run the smallest example:

```bash
python examples/01_hello_nyx.py
```

## Choosing a GPU on multi-GPU machines

By default Nyx renders on the GPU with the most dedicated memory and pairs the matching torch device with it. On a machine that mixes vendors, or where the largest GPU is not the one torch should drive, set {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.gpu_vendor`:

```python
import gs_nyx.nyx_py_sdk as nps

cam = scene.add_sensor(NyxCameraOptions(
    ...,
    gpu_vendor = nps.EGPUVendor.AMD,   # or nps.EGPUVendor.Nvidia
))
```

The value set on the first Nyx sensor of the scene applies to the shared renderer.

## Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `NyxCameraSensor requires a GPU torch build (CUDA or ROCm).` | CPU-only PyTorch. | Reinstall torch from the CUDA or ROCm index. |
| `No HIP runtime is loaded in the process; is this torch a ROCm build?` | An AMD GPU was picked by Nyx but torch is not a ROCm build. | Install the ROCm torch wheel, or point `gpu_vendor` at an NVIDIA GPU. |
| `no CUDA device matches the GPU Nyx renders on` / `no HIP device matches ...` | Nyx picked a GPU torch cannot see (for example an NVIDIA GPU on a ROCm torch). | Set `gpu_vendor` so Nyx renders on the vendor your torch build drives. |
| `RuntimeError` from `NyxRenderer.startup` | No usable Vulkan device. The log line above it names the cause. | Check `vulkaninfo` lists your GPU and that the driver exposes ray tracing. |

## Next steps

- Walk through the {doc}`quickstart` to render your first frame.
- Read {doc}`concepts` for the mental model behind scenes, assets, and render modes.
- See {doc}`changelog` for what changed between releases, including the breaking changes of this one.
