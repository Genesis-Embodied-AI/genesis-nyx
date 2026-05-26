# Installation

The Nyx renderer plugin is distributed as the `gs-nyx` Python wheel. TODO: Update this with the official published name

## Requirements

- Python 3.10, 3.11, or 3.12
- Linux (manylinux 2.39+) or Windows 10/11
- A CUDA-capable GPU (NVIDIA, compute capability 7.0+)
- A working CUDA driver, the wheels bundle their CUDA runtime, but the driver must be installed on the host

## Installing the wheel

```bash
pip install gs-nyx-plugin
```

To pin a specific version (recommended for reproducibility):

```bash
pip install "gs-nyx-plugin==0.1.0"
```

## Verifying the install

```python
import gs_nyx
print(gs_nyx.__version__)
```

If the import fails with a CUDA-related error, confirm that `nvidia-smi` runs successfully, the wheel cannot fall back to a CPU renderer.

## Next steps

- Walk through the {doc}`quickstart` to render your first frame.
- Read {doc}`concepts` for the mental model behind scenes, assets, and render modes.
