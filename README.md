# OpenSim Render

A visualization and animation tool for OpenSim biomechanical models in Python.

## Quick Start

### Prerequisites

- Conda (Miniconda or Anaconda)
- Windows: Visual Studio 2022 Build Tools with the C++ workload — only needed to
  build the optional native extension. CMake and SWIG come from `environment.yml`.

### Setup

1. **Create the environment** (installs OpenSim, CMake, SWIG, then the Python
   dependencies via Poetry):

   ```bash
   tools\devtool.bat bootstrap
   ```

   Equivalent manual steps:

   ```bash
   conda env create -f environment.yml
   conda activate osim-render
   poetry install
   ```

2. **Run the application**:

   ```bash
   tools\devtool.bat run
   ```

   or, with the environment active, `python main.py [model.osim] [-g GEOMETRY_DIR]`.

That is enough to launch the GUI. The two steps below are optional.

### Optional: shared OpenSim geometry

Models that reference meshes by name (`arm26.osim` and most `resources/` models)
need OpenSim's shared `Geometry/` directory (~22 MB), which is not checked in.
It lives in the `opensim-models` repository. Clone it at the path the default
geometry root expects:

```bash
git clone --depth 1 https://github.com/opensim-org/opensim-models.git \
    vendor/opensim-gui/opensim-models
```

Do not clone `opensim-gui` for this: `opensim-models` is a submodule of it, so a
plain clone does not fetch the meshes, and the full checkout is several GB.

Alternatively point `OSIM_RENDER_OPENSIM_GEOMETRY_DIR` at any existing OpenSim
`Geometry` directory. Copy `.env.example` to `.env` to set it. Tests that need
those meshes skip themselves when it is absent; the GUI also takes `-g <dir>`.

### Optional: native mesh loader

A SWIG/C++ mesh loader can replace the default VTK reader. The application runs
without it — `mesh_loader` falls back to VTK — so build it only if you need it:

```bash
tools\devtool.bat build
```

CMake compiles against the `osim-render` environment's interpreter and writes
`osim_render/_osim_render.pyd` directly into the package. Building against a
different Python produces a module that cannot be imported; pass
`-DPython3_EXECUTABLE=<python>` to override the interpreter explicitly.

### Load a Model

1. File → Open Model
2. Select an `.osim` file from `models/` directory
3. The model will load and display in the 3D viewer
4. Use the coordinate sliders to manipulate joint angles
5. Toggle visualization components in the toolbar

## Key Components

### Core API (`osim_render/api/`)

- **Managers**: Event bus, model management, settings persistence
- **Loaders**: OpenSim model and motion data loading
- **Rendering**: VTK-based 3D visualization
- **Animation**: Timeline and keyframe animation system
- **Geometry**: Mesh and shape data structures

### User Interface (`osim_render/ui/`)

- Main window with toolbar and menus
- Coordinate slider panel for joint control
- VTK rendering widget
- Animation scripting panel
- Properties inspector

### Documentation (`docs/`)

Start with [AGENTS.md](docs/AGENTS.md) for architectural guidelines.

Key documents:
- [GETTING_STARTED.md](docs/GETTING_STARTED.md) - Setup guide
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [FEATURES_COMPLETED.md](docs/FEATURES_COMPLETED.md) - Implementation status

## Code Quality

The project follows strict architectural guidelines:

- **No defensive programming**: All errors propagate with full stack traces (see AGENTS.md)
- **Type safety**: Full type hints and mypy compliance
- **Protocol-based**: Duck-typing with explicit type protocols
- **Fail-fast**: Explicit error handling at system boundaries only

Run checks:
```bash
tools\devtool.bat lint     # ruff check + mypy
tools\devtool.bat test     # pytest
```

or directly, with the environment active:

```bash
mypy osim_render
ruff check osim_render tests main.py
pytest
```

## Render Scripts

`scripts/` holds offline render drivers, e.g. `render_animation_scripts.py`,
which runs the examples in `animation_scripts/` and writes frames or video.

## Extending

### Adding Features

1. Implement in appropriate API module
2. Integrate into managers (event bus, model manager, etc.)
3. Add UI components if needed
4. Update type stubs if using OpenSim API
5. Follow AGENTS.md guidelines

### Creating Animations

Use the manim-style Scene API:

```python
from osim_render.api.animation.scene import Scene

scene = Scene(model_manager, scene_manager, event_bus)
scene.animate_coordinate("knee_r", 0, 45, duration=2.0)
timeline = scene.build_timeline()
```

## License

The Software is MIT licensed, See LICENSE for further details.
