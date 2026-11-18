"""Display-only reprojection of observed images onto celestial axes."""

from __future__ import annotations

import numpy as np
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from scipy.ndimage import map_coordinates

from .models import ImageData, Target


def align_north_up(image: ImageData, target: Target | None = None) -> ImageData:
    """Return a fully covered north-up, east-left rectangular cutout.

    Pixel interpolation is for chart display; the input pixels and FITS file are
    left untouched. The output keeps the input's approximate angular pixel scale.
    """
    ny, nx = image.data.shape
    matrix = image.wcs.pixel_scale_matrix
    scale_deg = float(np.sqrt(abs(np.linalg.det(matrix))))
    if not np.isfinite(scale_deg) or scale_deg <= 0:
        raise ValueError("Observed image WCS has no usable pixel scale.")
    if (
        matrix[0, 0] < 0 and matrix[1, 1] > 0
        and abs(matrix[0, 1]) <= scale_deg * 1e-6
        and abs(matrix[1, 0]) <= scale_deg * 1e-6
    ):
        return image

    center = (
        (target.ra_deg, target.dec_deg) if target is not None
        else image.wcs.pixel_to_world_values((nx - 1) / 2, (ny - 1) / 2)
    )
    pixel_scales = proj_plane_pixel_scales(image.wcs)
    scale_deg = float(np.mean(np.abs(pixel_scales)))

    def output_wcs(width: int, height: int) -> WCS:
        wcs = WCS(naxis=2)
        wcs.wcs.crpix = [(width + 1) / 2, (height + 1) / 2]
        wcs.wcs.cdelt = [-scale_deg, scale_deg]
        wcs.wcs.crval = center
        wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        return wcs

    def covered(width: int, height: int) -> bool:
        wcs = output_wcs(width, height)
        edge_x = np.linspace(0, width - 1, 33)
        edge_y = np.linspace(0, height - 1, 33)
        x = np.concatenate((edge_x, edge_x, np.zeros(33), np.full(33, width - 1)))
        y = np.concatenate((np.zeros(33), np.full(33, height - 1), edge_y, edge_y))
        ra, dec = wcs.pixel_to_world_values(x, y)
        source_x, source_y = image.wcs.world_to_pixel_values(ra, dec)
        return bool(
            np.isfinite(source_x).all() and np.isfinite(source_y).all()
            and np.min(source_x) >= 1 and np.max(source_x) <= nx - 2
            and np.min(source_y) >= 1 and np.max(source_y) <= ny - 2
        )

    low, high = 0.0, 1.0
    for _ in range(22):
        middle = (low + high) / 2
        width = max(2, int(nx * middle))
        height = max(2, int(ny * middle))
        if covered(width, height):
            low = middle
        else:
            high = middle
    width = max(2, int(nx * low))
    height = max(2, int(ny * low))
    if not covered(width, height):
        raise ValueError("No north-up rectangle fits inside the observed image around this target.")
    wcs = output_wcs(width, height)
    output_y, output_x = np.indices((height, width), dtype=float)
    ra, dec = wcs.pixel_to_world_values(output_x, output_y)
    source_x, source_y = image.wcs.world_to_pixel_values(ra, dec)
    data = map_coordinates(np.asarray(image.data, dtype=float), [source_y, source_x], order=1, mode="constant", cval=np.nan)
    return ImageData(
        data=data, wcs=wcs, survey=image.survey, band=image.band, mode=image.mode,
        source_url=image.source_url, local_path=image.local_path,
        chart_source_label=image.chart_source_label,
    )
