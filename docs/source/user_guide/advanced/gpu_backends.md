# GPU backends: CUDA and ROCm

Nyx renders through Vulkan. The compute side, the tensors your training loop reads, lives in PyTorch, and PyTorch may be a CUDA build (NVIDIA) or a ROCm build (AMD). This page explains how the two halves are connected, how the GPU is chosen, and what differs per vendor.

## Zero-copy interop

The renderer holds no compute-API code of its own. Instead, it allocates every buffer the plugin needs to drive it (rigid transforms, camera poses, deformable vertices and indices, and the packed colour output) and **exports** each one as an OS handle:

| Platform | Handle type ({py:class}`~gs_nyx.nyx_py_sdk.EExternalMemoryHandleType`) |
|---|---|
| Linux (Vulkan) | `OpaqueFd`, a file descriptor consumed by the import |
| Windows (Vulkan) | `OpaqueWin32`, an NT handle closed after the import |
| Windows (DX12) | `D3D12Heap`, an NT handle to a shared heap |

The plugin imports those handles into the compute API already loaded by torch with {py:class}`~gs_nyx.nyx_external_memory.NyxExternalMemoryImporter`. The importer talks to the CUDA driver API (`libcuda` / `nvcuda.dll`) or the HIP runtime (`libamdhip64` / `amdhip64.dll`) through `ctypes`, so no extra Python package is required, and wraps each mapped pointer as a torch tensor through the CUDA array interface. Every per-frame tensor the plugin writes, and every image you read back, aliases Nyx's own memory. Nothing is copied between the simulator and the renderer.

Synchronization happens on the CPU: the plugin waits for torch's pending GPU work before telling Nyx the buffers changed, and Nyx waits for its own GPU work before a render returns.

## Which GPU renders

{py:class}`~gs_nyx.nyx_py_renderer.BridgeStartupParams` carries a pick strategy ({py:class}`~gs_nyx.nyx_py_sdk.EPickStrategy`):

| Strategy | Behaviour | Exposed by the plugin |
|---|---|---|
| `VRAMSize` | The GPU with the most dedicated memory. | Default |
| `VendorID` | The first GPU of a given vendor ({py:class}`~gs_nyx.nyx_py_sdk.EGPUVendor`). | {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.gpu_vendor` |
| `AdapterID` | The GPU at a given index in the API's enumeration order. | Not surfaced |

After startup the renderer reports a {py:class}`~gs_nyx.nyx_py_sdk.DeviceIdentity` (an adapter LUID on Windows, a PCI bus location on Linux). The importer walks the devices torch can see and picks the one with the same identity. The plugin then makes that device torch's current device and logs `Nyx renders on torch device N, selecting it` if it had to switch, so tensors you create afterwards land next to the images by default. Once built, {py:attr}`NyxPyRenderer.device <gs_nyx_plugin.nyx_renderer.NyxPyRenderer.device>` names that device.

If no torch device matches, for example because Nyx picked an NVIDIA GPU on a machine where torch is a ROCm build, the build fails with `no CUDA device matches the GPU Nyx renders on` (or the HIP equivalent). Set `gpu_vendor` so Nyx renders on the vendor your torch build drives.

## NVIDIA (CUDA)

- Any CUDA build of PyTorch works. The CUDA version must be supported by your driver; Nyx itself has no CUDA version requirement anymore.
- The OpenImageDenoise CUDA device is used when `denoise=True`.

## AMD (ROCm)

ROCm rendering is validated on both Windows 11 and Linux.

- Install a ROCm build of PyTorch (ROCm 6.x or 7.x). The importer reuses the HIP runtime torch loaded (`libamdhip64.so.7`, `.so.6`, or `amdhip64_7.dll` / `amdhip64_6.dll` on Windows); a second runtime instance could not share torch's mappings.
- On Linux the wheel installs a `.pth` hook that loads the system `libdrm.so.2` and `libdrm_amdgpu.so.1` into the global namespace at interpreter start, so the Vulkan driver and the HIP runtime bind to the same copy. Install your distribution's `libdrm` packages if they are missing.
- On Windows the wheel ships the HIP SDK runtime (`amdhip64_7.dll`, `amd_comgr_3.dll`) next to the modules and preloads it unless torch already holds one.
- The OpenImageDenoise HIP device is used when `denoise=True`.
- `torch.cuda.is_available()`, `torch.cuda.synchronize()` and `torch.device("cuda", i)` all refer to ROCm devices on a ROCm build. User code is identical on both vendors.

## Where the tensors live

| Tensor | Device |
|---|---|
| `cam.read().rgb` | The torch device paired with the renderer (`NyxPyRenderer.device`). |
| Per-frame interop buffers (rigid transforms, camera poses, deformable geometry) | Same device, written by the plugin. |

`cam.read().rgb` is a strided view into the renderer's packed output buffer. It is refreshed in place by every render; call `.clone()` or `.cpu()` to keep a frame across steps.

## See also

- {doc}`../installation`: vendor-specific install steps and troubleshooting.
- {doc}`sensor_lifecycle`: when the buffers are imported and when they are written.
