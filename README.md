# Nyx for Genesis

![Path-traced render of dual robot arms on a tabletop](docs/source/_static/images/landing.png)

[![PyPI version](https://img.shields.io/pypi/v/gs-nyx-plugin.svg)](https://pypi.org/project/gs-nyx-plugin/)
[![Documentation](https://img.shields.io/badge/docs-online-blue.svg)](https://genesis-embodied-ai.github.io/genesis-nyx/)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE.txt)

Documentation and runnable examples for the **Nyx renderer plugin** for the [Genesis World](https://genesis-world.readthedocs.io/) simulator.

Nyx is a GPU-accelerated path tracer that plugs into Genesis as a camera sensor. It supports PBR materials, HDRI and analytic lighting, 3D Gaussian splat assets, attached / multi-camera setups, multi-environment rendering, and per-pixel object picking.

Prebuilt wheels are available for x86-64 Linux (manylinux 2.34+, validated on Ubuntu 22.04) and Windows 11 on Python 3.10–3.13. An NVIDIA GPU with CUDA 12.9+ and driver 575+ is required.

## What's in this repository

```
docs/        Sphinx documentation source (user guide + auto-generated API reference)
examples/    Runnable Python scripts demonstrating the plugin
```

The scripts under [examples/](examples/) are the canonical, runnable versions. The user-guide example pages embed them via `literalinclude`, so what's on the docs site is exactly what runs here.

## Running an example

```bash
pip install gs-nyx-plugin
python examples/01_hello_nyx.py
```

## Building the docs locally

```bash
cd docs
pip install -r requirements.txt
pip install gs-nyx-plugin
make html
```

Then open `docs/build/html/index.html`. The API reference is generated from the docstrings and `.pyi` stubs shipped inside the installed `gs-nyx-plugin` wheel — no source checkout of the renderer is required.

## Contributing

Issues and pull requests are welcome once the project is public. Until then, please reach out to the maintainers directly.
