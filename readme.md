# Brush Selection Tool for QGIS

![Brush Selection Tool Logo](paintbrush.png)

[![QGIS 3.28+](https://img.shields.io/badge/QGIS-3.28%2B-green.svg)](https://qgis.org)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](LICENSE)

Brush Selection Tool provides an intuitive "painting" interface for selecting polygon features in QGIS.  
Drag a circular brush across the map canvas—every polygon the brush touches becomes selected.

---

## Features
- Adjustable pixel-based brush radius (1–200 px) for consistent behavior across all projections  
- Real‑time visual feedback: translucent cursor circle and brush‑stroke rubber band  
- Efficient selection using spatial indexing with bounding‑box pre‑filtering  
- Choose to add to existing selections or replace them  
- Target the active polygon layer only (default) or all polygon layers  
- Optimized for QGIS **3.28+**

---

## Installation

### From QGIS Plugin Manager
1. Open QGIS.
2. Go to **Plugins ➔ Manage and Install Plugins**.
3. Search for **“Brush Selection Tool”** and click **Install Plugin**.

### From Source
1. Clone or download this repository.
2. Copy the `brush-tool-selection` folder to your QGIS plugins directory  
   (e.g., `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`).
3. Restart QGIS and enable the plugin via **Plugins ➔ Manage and Install Plugins ➔ Installed**.

---

## Usage
1. Activate the tool from **Plugins ➔ Brush Selection Tool** (or the toolbar icon).
2. Adjust the brush radius via the slider (1–200 px).
3. Click and drag with the left mouse button to “paint” over polygons.
4. Release the mouse button to finalize the selection.
5. Options:
   - **Active layer only** – restricts selection to the current polygon layer.
   - **Add to selection** – add to existing selection instead of replacing it.

![Demo GIF](docs/17-26-19-Clip20250903172818.gif)  
[Download demo video](docs/17-26-19-Clip20250903172818.mp4)

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

