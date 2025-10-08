# Brush Selection Tool for QGIS

![Brush Selection Tool Logo](BrushSelectionTool/icons/paintbrush_64x64.png)

[![QGIS 3.40+](https://img.shields.io/badge/QGIS-3.40%2B-green.svg)](https://qgis.org)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Brush Selection Tool provides an intuitive "painting" interface for selecting vector features in QGIS.
Drag a circular brush across the map canvas—every feature the brush touches becomes selected. Works with points, lines, polygons, and multipolygons.

---

## Features
- **Supports all vector geometry types**: points, lines, polygons, and multipolygons
- Adjustable pixel-based brush radius (1–200 px) for consistent behavior across all projections
- Real‑time visual feedback: translucent cursor circle and brush‑stroke rubber band
- Choose to add to existing selections or replace them
- **Shift + Mouse Wheel**: Dynamic radius adjustment while tool is active
- **Shift + Click**: Add to selection mode (overrides default setting)
- Optimized for QGIS **3.40+**

---

## Installation

### From QGIS Plugin Manager
1. Open QGIS.
2. Go to **Plugins ➔ Manage and Install Plugins**.
3. Search for **"Brush Selection Tool"** and click **Install Plugin**.

### From Source
1. Clone or download this repository.
2. Copy the `brush-tool-selection` folder to your QGIS plugins directory
   (e.g., `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`).
3. Restart QGIS and enable the plugin via **Plugins ➔ Manage and Install Plugins ➔ Installed**.

---

## Usage
1. Activate the tool from the toolbar icon (paintbrush icon).
2. Click and drag with the left mouse button to "paint" over features.
3. Release the mouse button to finalize the selection.
4. **Controls:**
   - **Shift + Mouse Wheel**: Adjust brush radius (1–200 px) in real-time
   - **Shift + Click/Drag**: Add to existing selection instead of replacing
5. **Note:** Works on the active layer by default. Supports all vector geometry types (points, lines, polygons, multipolygons).


## Demo

[![Brush Selection Tool Demo](https://img.youtube.com/vi/S-qwbJLPPV0/0.jpg)](https://www.youtube.com/watch?v=S-qwbJLPPV0)

---

## Development

Built with QGIS Plugin Builder and Qt Designer.

---

## Support & Contributing
- **Issues / Feature Requests:** [GitHub Issues](https://github.com/amanbagrecha/brush-tool-selection/issues)
- Pull requests are welcome! Please open an issue first to discuss major changes.

---

## License
Released under the [GPL-2.0-or-later](LICENSE) license.

---

## Credits
- **Author:** Aman Bagrecha
- Built using QGIS Plugin Builder and Qt Designer

---

## Changelog
See the `changelog` entry in [metadata.txt](metadata.txt) for version history.

---

## Release
This project uses [qgis-plugin-ci](https://github.com/opengisch/qgis-plugin-ci) to package and publish the plugin.

### Required secrets
The GitHub release workflow requires the following repository secrets:

- `OSGEO_USERNAME` – OSGeo username with permission to publish the plugin
- `OSGEO_PASSWORD` – Password for the OSGeo account

### Procedure
1. Update `metadata.txt` with a new version number.
2. Commit and push your changes.
3. Create and push a tag for the new version, e.g. `git tag -a 1.0.0 -m "Release 1.0.0"` and `git push origin 1.0.0`.
4. GitHub Actions packages the plugin and uploads it to the QGIS Plugin Repository.

