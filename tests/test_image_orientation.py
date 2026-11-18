import numpy as np
import pytest
from astropy.wcs import WCS

from findingchart_guiplotter.image_orientation import align_north_up
from findingchart_guiplotter.models import ImageData


def test_rotated_observed_image_becomes_covered_north_up_rectangle():
    angle = np.deg2rad(30.0)
    scale = 0.25 / 3600.0
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [51.0, 51.0]
    wcs.wcs.crval = [75.0, -8.0]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.cd = scale * np.array([
        [-np.cos(angle), np.sin(angle)],
        [np.sin(angle), np.cos(angle)],
    ])
    yy, xx = np.mgrid[:101, :101]
    data = 1.0 + 100.0 * np.exp(-((xx - 70.0) ** 2 + (yy - 45.0) ** 2) / 8.0)
    original = data.copy()
    image = ImageData(data=data, wcs=wcs, survey="Observed image", band="test", mode="Single band")
    star_sky = wcs.pixel_to_world(70.0, 45.0)

    aligned = align_north_up(image)

    assert aligned.data.shape[0] < 101 and aligned.data.shape[1] < 101
    assert np.isfinite(aligned.data).all()
    assert aligned.wcs.pixel_scale_matrix[0, 0] < 0
    assert aligned.wcs.pixel_scale_matrix[1, 1] > 0
    assert aligned.wcs.pixel_scale_matrix[0, 1] == pytest.approx(0, abs=1e-12)
    assert aligned.wcs.pixel_scale_matrix[1, 0] == pytest.approx(0, abs=1e-12)
    expected_x, expected_y = aligned.wcs.world_to_pixel(star_sky)
    peak_y, peak_x = np.unravel_index(np.argmax(aligned.data), aligned.data.shape)
    assert (peak_x, peak_y) == pytest.approx((float(expected_x), float(expected_y)), abs=1.0)
    assert np.array_equal(data, original)


def test_already_aligned_image_keeps_pixels():
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [10.0, 10.0]
    wcs.wcs.cdelt = [-0.25 / 3600.0, 0.25 / 3600.0]
    wcs.wcs.crval = [75.0, -8.0]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    data = np.arange(400, dtype=float).reshape(20, 20)
    image = ImageData(data=data, wcs=wcs, survey="Observed image", band="test", mode="Single band")

    aligned = align_north_up(image)

    assert aligned is image
