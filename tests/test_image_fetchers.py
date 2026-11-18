import numpy as np
import pytest
import subprocess
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from findingchart_guiplotter.image_fetchers import ImageFetchError, _legacy_jpeg_array, _legacy_placeholder_tile, load_observed_fits
from findingchart_guiplotter.models import Target
from findingchart_macapp.bridge.findingchart_bridge import _load_image, _settings


def _observed_fits(path, *, with_wcs=True):
    header = WCS(naxis=2)
    header.wcs.crpix = [16.0, 16.0]
    header.wcs.cdelt = [-0.0001, 0.0001]
    header.wcs.crval = [210.0, 54.0]
    header.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    image = fits.ImageHDU(data=np.arange(1024, dtype=float).reshape(32, 32), header=header.to_header() if with_wcs else None)
    fits.HDUList([fits.PrimaryHDU(), image]).writeto(path)


def test_observed_fits_loads_image_extension_and_sky_coordinates(tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path)
    image = load_observed_fits(path, Target("SN", 210.0, 54.0))
    assert image.data.shape == (32, 32)
    assert image.data[0, 1] == 1.0
    assert image.survey == "Observed image"
    assert image.local_path == path
    x, y = image.wcs.world_to_pixel_values(210.0, 54.0)
    assert (x, y) == pytest.approx((15.0, 15.0))


def test_observed_chart_title_omits_open_filter_position(tmp_path):
    from findingchart_guiplotter.renderer import chart_title

    path = tmp_path / "acquisition.fits"
    _observed_fits(path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["TELESCOP"] = "NOT"
        hdul[0].header["INSTRUME"] = "ALFOSC_FASU"
        hdul[0].header["ALFLTNM"] = "Open"
    target = Target("SN", 210.0, 54.0)

    image = load_observed_fits(path, target)

    assert chart_title(image, target).startswith("NOT/ALFOSC: SN ")


def test_observed_chart_title_keeps_real_filter(tmp_path):
    from findingchart_guiplotter.renderer import chart_title

    path = tmp_path / "acquisition.fits"
    _observed_fits(path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["TELESCOP"] = "NOT"
        hdul[0].header["INSTRUME"] = "ALFOSC_FASU"
        hdul[0].header["ALFLTNM"] = "r"

    image = load_observed_fits(path, Target("SN", 210.0, 54.0))

    assert chart_title(image, Target("SN", 210.0, 54.0)).startswith("NOT/ALFOSC-r: SN ")


def test_observed_fits_rejects_missing_wcs(tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path, with_wcs=False)
    with pytest.raises(ImageFetchError, match="celestial WCS"):
        load_observed_fits(path, Target("SN", 210.0, 54.0))


def test_observed_fits_rejects_target_outside_frame(tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path)
    with pytest.raises(ImageFetchError, match="outside"):
        load_observed_fits(path, Target("SN", 211.0, 54.0))


def test_observed_fits_corrects_full_detector_wcs_for_window(tmp_path):
    path = tmp_path / "windowed.fits"
    header = WCS(naxis=2)
    header.wcs.crpix = [650.0 + 16.0, 655.0 + 16.0]
    header.wcs.cdelt = [-0.0001, 0.0001]
    header.wcs.crval = [210.0, 54.0]
    header.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    primary = fits.PrimaryHDU()
    primary.header["DETWIN1"] = "[650:681, 655:686]"
    image_hdu = fits.ImageHDU(data=np.ones((32, 32)), header=header.to_header())
    fits.HDUList([primary, image_hdu]).writeto(path)
    original = path.read_bytes()

    image = load_observed_fits(path, Target("SN", 210.0, 54.0))

    assert image.wcs.world_to_pixel_values(210.0, 54.0) == pytest.approx((16.0, 16.0))
    assert path.read_bytes() == original


def test_observed_fits_does_not_shift_wcs_already_in_window_coordinates(tmp_path):
    path = tmp_path / "windowed.fits"
    header = WCS(naxis=2)
    header.wcs.crpix = [16.0, 16.0]
    header.wcs.cdelt = [-0.0001, 0.0001]
    header.wcs.crval = [210.0, 54.0]
    header.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    primary = fits.PrimaryHDU()
    primary.header["DETWIN1"] = "[650:681, 655:686]"
    fits.HDUList([primary, fits.ImageHDU(data=np.ones((32, 32)), header=header.to_header())]).writeto(path)

    image = load_observed_fits(path, Target("SN", 210.0, 54.0))

    assert image.wcs.world_to_pixel_values(210.0, 54.0) == pytest.approx((15.0, 15.0))


def test_observed_fits_aligns_rotated_pixels_by_default_and_can_keep_detector_view(tmp_path):
    path = tmp_path / "rotated.fits"
    angle = np.deg2rad(25.0)
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [51.0, 51.0]
    wcs.wcs.crval = [210.0, 54.0]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.cd = 0.25 / 3600.0 * np.array([
        [-np.cos(angle), np.sin(angle)], [np.sin(angle), np.cos(angle)],
    ])
    fits.PrimaryHDU(np.ones((101, 101)), header=wcs.to_header()).writeto(path)
    target = Target("SN", 210.0, 54.0)

    aligned = load_observed_fits(path, target)
    detector = load_observed_fits(path, target, align_north_up=False)

    assert aligned.data.shape[0] < detector.data.shape[0]
    assert aligned.wcs.pixel_scale_matrix[0, 1] == pytest.approx(0, abs=1e-12)
    assert detector.wcs.pixel_scale_matrix[0, 1] != pytest.approx(0, abs=1e-12)


def test_observed_fits_can_solve_missing_wcs_without_editing_input(monkeypatch, tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path, with_wcs=False)
    original = path.read_bytes()
    solution = WCS(naxis=2)
    solution.wcs.crpix = [16.0, 16.0]
    solution.wcs.cdelt = [-0.0001, 0.0001]
    solution.wcs.crval = [210.0, 54.0]
    solution.wcs.ctype = ["RA---TAN", "DEC--TAN"]

    monkeypatch.setattr("findingchart_guiplotter.wcs_solving.shutil.which", lambda name: f"/usr/bin/{name}")
    def fake_run(command, **kwargs):
        assert command[0] == "/usr/bin/solve-field"
        assert command[command.index("--source-extractor-path") + 1] == "/usr/bin/sex"
        assert command[command.index("--extension") + 1] == "1"
        assert command[command.index("--scale-low") + 1] == "0.18"
        assert command[command.index("--scale-high") + 1] == "0.72"
        fits.PrimaryHDU(header=solution.to_header()).writeto(command[command.index("--wcs") + 1])
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr("findingchart_guiplotter.wcs_solving.subprocess.run", fake_run)

    image = load_observed_fits(path, Target("SN", 210.0, 54.0), solve_wcs=True, pixel_scale_arcsec=0.36)
    assert image.wcs.world_to_pixel_values(210.0, 54.0) == pytest.approx((15.0, 15.0))
    assert path.read_bytes() == original


def test_observed_fits_reports_unsolved_field(monkeypatch, tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path, with_wcs=False)
    monkeypatch.setattr("findingchart_guiplotter.wcs_solving.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("findingchart_guiplotter.wcs_solving.subprocess.run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    with pytest.raises(ImageFetchError, match="could not solve"):
        load_observed_fits(path, Target("SN", 210.0, 54.0), solve_wcs=True, pixel_scale_arcsec=0.36)


def test_mac_bridge_loads_observed_fits_and_defaults_injection_off(tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path)
    payload = {"resolveTNS": False, "targetName": "SN", "raText": "14:00:00", "decText": "+54:00:00", "observedImagePath": str(path)}
    result = _load_image(payload, tmp_path)
    assert result["survey"] == "Observed image"
    assert result["imageCachePath"]
    assert _settings({}, Target("SN", 210.0, 54.0), []).show_injected_source is False


def test_mac_bridge_passes_wcs_solve_option(monkeypatch, tmp_path):
    path = tmp_path / "science.fits"
    _observed_fits(path, with_wcs=False)
    solution = WCS(naxis=2)
    solution.wcs.crpix = [16.0, 16.0]
    solution.wcs.cdelt = [-0.0001, 0.0001]
    solution.wcs.crval = [210.0, 54.0]
    solution.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    captured = {}
    def fake_solve(payload, target, extension, scale):
        captured.update({"extension": extension, "scale": scale})
        return solution
    monkeypatch.setattr("findingchart_guiplotter.wcs_solving.solve_fits_wcs", fake_solve)
    request = {
        "resolveTNS": False, "targetName": "SN", "raText": "14:00:00", "decText": "+54:00:00",
        "observedImagePath": str(path), "solveObservedWCS": True, "pixelScaleArcsec": 0.36,
    }
    result = _load_image(request, tmp_path)
    assert result["survey"] == "Observed image"
    assert captured == {"extension": 1, "scale": 0.36}


def test_legacy_placeholder_tile_detects_constant_rgb_frame():
    data = np.zeros((16, 16, 3), dtype=float)
    data[..., 1] = 15.0 / 255.0
    data[..., 2] = 8.0 / 255.0

    assert _legacy_placeholder_tile(data) is True


def test_legacy_placeholder_tile_accepts_real_structure():
    yy, xx = np.mgrid[:16, :16]
    data = np.zeros((16, 16, 3), dtype=float)
    data[..., 0] = xx / 15.0
    data[..., 1] = yy / 15.0
    data[..., 2] = (xx + yy) / 30.0

    assert _legacy_placeholder_tile(data) is False


def test_legacy_jpeg_array_converts_single_band_fallback_to_grayscale():
    rgb = np.zeros((16, 16, 3), dtype=np.uint8)
    rgb[..., 1] = np.arange(16, dtype=np.uint8)
    image = Image.fromarray(rgb)

    data = _legacy_jpeg_array(image, "Single band")

    assert data.shape == (16, 16)
    assert np.nanmax(data) > np.nanmin(data)


def test_legacy_jpeg_array_rejects_placeholder_tile():
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[..., 0] = 24
    rgb[..., 1] = 15
    rgb[..., 2] = 32
    image = Image.fromarray(rgb)

    with pytest.raises(ImageFetchError, match="placeholder tile"):
        _legacy_jpeg_array(image, "Color composite")
