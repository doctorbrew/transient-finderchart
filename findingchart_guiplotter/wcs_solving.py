"""Local plate solving for observed FITS images."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS

from .models import Target


class WcsSolveError(RuntimeError):
    pass


def solve_fits_wcs(
    payload: bytes,
    target: Target,
    image_extension: int,
    pixel_scale_arcsec: float | None = None,
) -> WCS:
    """Solve the image in a temporary directory using SExtractor and Astrometry.net."""
    solver = shutil.which("solve-field")
    extractor = shutil.which("sex") or shutil.which("source-extractor")
    if not solver or not extractor:
        raise WcsSolveError("Local WCS solving needs both Astrometry.net solve-field and AstrOmatic SExtractor (sex).")
    if pixel_scale_arcsec is not None and (not math.isfinite(pixel_scale_arcsec) or pixel_scale_arcsec <= 0):
        raise WcsSolveError("Approximate pixel scale must be a positive number of arcseconds per pixel.")

    with tempfile.TemporaryDirectory(prefix="findingchart-wcs-") as directory:
        work = Path(directory)
        source = work / "observed.fits"
        solution = work / "observed.wcs"
        source.write_bytes(payload)
        command = [
            solver, "--use-source-extractor", "--source-extractor-path", extractor,
            "--no-plots", "--overwrite", "--no-verify", "--new-fits", "none",
            "--dir", str(work), "--wcs", str(solution),
            "--extension", str(image_extension),
            "--ra", str(target.ra_deg), "--dec", str(target.dec_deg), "--radius", "2",
            "--cpulimit", "90",
        ]
        if pixel_scale_arcsec is not None:
            command.extend([
                "--scale-units", "arcsecperpix",
                "--scale-low", str(pixel_scale_arcsec / 2.0),
                "--scale-high", str(pixel_scale_arcsec * 2.0),
            ])
        command.append(str(source))
        try:
            result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=120, check=False)
        except subprocess.TimeoutExpired as exc:
            raise WcsSolveError("WCS solving timed out after 120 seconds. Check the scale hint and image stars.") from exc
        if result.returncode != 0 or not solution.is_file():
            detail = (result.stdout or result.stderr).strip().splitlines()
            reason = f" Last solver message: {detail[-1][:240]}" if detail else ""
            raise WcsSolveError(
                "Local WCS solver could not solve this image. Check the target coordinates, approximate pixel scale, "
                f"image stars, and installed index coverage.{reason}"
            )
        try:
            wcs = WCS(fits.getheader(solution))
        except (OSError, ValueError) as exc:
            raise WcsSolveError(f"WCS solver returned an unreadable solution: {exc}") from exc
        if not wcs.has_celestial or wcs.pixel_n_dim != 2:
            raise WcsSolveError("WCS solver returned a solution without two-dimensional celestial coordinates.")
        return wcs.celestial
