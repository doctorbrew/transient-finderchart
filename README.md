# TransientFinderchart

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Qt GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20PyQt6-green.svg)](findingchart_guiplotter/qt_compat.py)
[![macOS SwiftUI](https://img.shields.io/badge/macOS%2014%2B-SwiftUI-black.svg)](findingchart_macapp)
[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

Finding-chart tool for supernovae and other transients, available as a Qt desktop GUI and a native macOS app. Resolve TNS or add manual targets, fetch archival survey cutouts or open an observed FITS image, add observing overlays (slit and blind offset star), then export the finding chart as PNG, JPEG, or PDF charts. Fake-source injection is optional and starts off.

The chart design is inspired by Sean Brennan's [`Astro-Sean/finder_chart`](https://github.com/Astro-Sean/finder_chart).

![Template finding chart](docs/assets/findingchartGUI_2024ggi.jpg)

## Features

- **Images:** Pan-STARRS, Legacy Survey, DSS2, and 2MASS cutouts with survey filters and supported color composites, plus local observed FITS images. Images without WCS can be solved locally when SExtractor, Astrometry.net, and index files are installed.
- **Charts:** WCS-aware inset, slit PA, parallactic angle, compass, scale bar, crosshair, contrast controls, and color maps.
- **Fake source:** automatic FWHM estimation plus Moffat and empirical PSF models with adjustable brightness.
- **Catalogs:** Gaia DR3 and Pan-STARRS DR2 overlays with magnitude/distance cuts and selectable markers.
- **Blind offsets:** delta RA/Dec, PA east of north, magnitude, and available Gaia parallax and proper motion.
- **Export:** PNG, JPEG, and PDF; the macOS app also provides high-DPI presets.

## Quick start

Python 3.9 or newer is required. For editable development:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e .
```

Alternatively, install the runtime requirements with `python3 -m pip install -r requirements.txt`.

### Desktop GUI

```bash
python3 run_finding_chart.py
# or, after an editable install:
findingchart-guiplotter
```

If a conda environment already uses PyQt6:

```bash
FINDING_CHART_QT_API=pyqt6 python3 run_finding_chart.py
```

### Development web interface

```bash
python3 -m findingchart_guiplotter.web --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. The server has no production hardening, so keep it bound to `127.0.0.1` and do not expose it to an untrusted network.

### Native macOS interface

Requires macOS 14+, Swift 5.9+, and a Python environment containing the project dependencies.

```bash
cd findingchart_macapp
export FINDING_CHART_PYTHON="/absolute/path/to/.venv/bin/python"
export FINDING_CHART_REPO="/absolute/path/to/transient-finderchart"
swift run findingchart_macapp
```

See the [native interface README](findingchart_macapp/README.md) for bridge and storage details.

## Workflow

1. Resolve a TNS/IAU/ZTF name or enter custom coordinates.
2. Choose the survey, filter, field size, and pixel scale and load a cutout, or open a two-dimensional observed FITS image. Observed images are aligned north up and east left by default; this resamples and crops the chart view to a fully covered rectangle while leaving the FITS file unchanged. Turn off **Align observed image north up, east left** to retain detector orientation. The observed chart uses the same renderer and typography as archival charts; its title takes the telescope, instrument, and filter from the FITS header when available. For an image without usable celestial WCS, select **Solve WCS with SExtractor + Astrometry.net** and enter an approximate pixel scale before opening it. The target must be in the image.
3. Optionally query Gaia DR3 or Pan-STARRS DR2 and select a star for blind-offset details.
4. Adjust the slit, parallactic angle, overlays, optional fake source, inset, observatory/time, and contrast.
5. Export the chart.

## Configuration and notes

For authenticated TNS queries, set these variables. Credentials are never stored in the repository.

```bash
export TNS_API_KEY="..."
export TNS_BOT_ID="..."
export TNS_BOT_NAME="..."
export TNS_TYPE="bot"  # optional; this is the default
```

Without credentials, the app uses public TNS search where possible.

- Online lookups depend on third-party services; Pan-STARRS 3π coverage is principally north of −30°.
- Failed Legacy Survey FITS requests fall back to JPEG with approximate centered TAN WCS.
- Gaia proper motion is displayed but is not propagated to the observing epoch.
- Slit and blind-offset PA are measured east of north.
- The fake source is visual only, not a calibrated photometric simulation.
- Local WCS solving uses AstrOmatic SExtractor for source detection and Astrometry.net `solve-field` for the astrometric solution; SCAMP is not required. It searches within 2° of the target and within a factor of two of the pixel-scale hint, with a 120-second timeout. The input FITS file is never modified. Solving can fail for sparse fields or missing index coverage. See the [Astrometry.net solver documentation](https://astrometry.net/doc/readme.html#source-extractor) and [index-file documentation](https://astrometry.net/doc/build-index.html).
- The development web interface accepts observed FITS uploads up to 64 MB; desktop interfaces open local FITS files directly.
- Web exports accumulate in `web_exports/`; native outputs and caches use `findingchart_macapp/rendered_charts/`.
- Run `python3 -m pytest -q` for the offline suite.
- Run `python3 tests/psf_diagnostics.py` to regenerate plots in `tests/figures/`.
- See [docs/IMPLEMENTATION_LOG.md](docs/IMPLEMENTATION_LOG.md) for the implementation history, audit, roadmap, and detailed limitations.
