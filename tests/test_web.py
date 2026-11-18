import base64

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from findingchart_guiplotter.catalog import DEFAULT_CATALOG_MAX_DISTANCE_ARCSEC
from findingchart_guiplotter.models import ImageData
from findingchart_guiplotter.web import payload_bool, render_from_payload


def test_payload_bool_accepts_browser_and_api_values():
    assert payload_bool({"x": True}, "x", False) is True
    assert payload_bool({"x": "on"}, "x", False) is True
    assert payload_bool({"x": "false"}, "x", True) is False
    assert payload_bool({}, "x", True) is True


def test_render_from_payload_defaults_catalog_distance_cut(monkeypatch, tmp_path):
    captured = {}

    def fake_query_catalog_sources(target, radius_arcmin, catalog, limit=200, max_magnitude=None, max_distance_arcsec=None):
        captured["catalog"] = catalog
        captured["max_distance_arcsec"] = max_distance_arcsec
        return []

    monkeypatch.setattr("findingchart_guiplotter.web.query_catalog_sources", fake_query_catalog_sources)
    monkeypatch.setattr("findingchart_guiplotter.web.fetch_image", lambda target, request: ImageData(data=[], wcs=None, survey=request.survey, band=request.band, mode=request.mode))  # type: ignore[arg-type]
    monkeypatch.setattr("findingchart_guiplotter.web.measured_image_fwhm_arcsec", lambda image, target: (None, None))
    def fake_export(path, image, target, settings):
        captured["inject"] = settings.show_injected_source
        path.write_text("ok")
    monkeypatch.setattr("findingchart_guiplotter.web.export_chart", fake_export)
    monkeypatch.setattr("findingchart_guiplotter.web.WEB_OUTPUT_DIR", tmp_path)

    image_url = render_from_payload({"ra_deg": 210.0, "dec_deg": 54.0, "catalog": "Gaia DR3"})

    assert image_url.startswith("/exports/finding_chart_")
    assert captured == {"catalog": "Gaia DR3", "max_distance_arcsec": DEFAULT_CATALOG_MAX_DISTANCE_ARCSEC, "inject": False}


def test_render_from_uploaded_observed_fits_exports_a_chart(monkeypatch, tmp_path):
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [8, 8]
    wcs.wcs.cdelt = [-0.0001, 0.0001]
    wcs.wcs.crval = [210, 54]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    path = tmp_path / "observed.fits"
    fits.PrimaryHDU(np.arange(256, dtype=float).reshape(16, 16), header=wcs.to_header()).writeto(path)
    monkeypatch.setattr("findingchart_guiplotter.web.WEB_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("findingchart_guiplotter.web.fetch_image", lambda *args: (_ for _ in ()).throw(AssertionError("archive fetched")))
    url = render_from_payload({"ra_deg": 210, "dec_deg": 54, "image_source": "observed", "observed_fits_base64": base64.b64encode(path.read_bytes()).decode(), "observed_filename": path.name})
    with Image.open(tmp_path / url.rsplit("/", 1)[-1]) as chart:
        assert chart.format == "PNG"
        assert min(chart.size) > 500


def test_web_passes_wcs_solve_option_for_observed_fits(monkeypatch, tmp_path):
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [8, 8]
    wcs.wcs.cdelt = [-0.0001, 0.0001]
    wcs.wcs.crval = [210, 54]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    path = tmp_path / "no-wcs.fits"
    fits.PrimaryHDU(np.arange(256, dtype=float).reshape(16, 16)).writeto(path)
    captured = {}
    def fake_solve(payload, target, extension, scale):
        captured["scale"] = scale
        return wcs
    monkeypatch.setattr("findingchart_guiplotter.wcs_solving.solve_fits_wcs", fake_solve)
    monkeypatch.setattr("findingchart_guiplotter.web.WEB_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("findingchart_guiplotter.web.export_chart", lambda path, image, target, settings: path.write_text("ok"))
    render_from_payload({
        "ra_deg": 210, "dec_deg": 54, "image_source": "observed", "solve_observed_wcs": True,
        "pixel_scale_arcsec": 0.36, "observed_fits_base64": base64.b64encode(path.read_bytes()).decode(),
    })
    assert captured == {"scale": 0.36}


def test_web_can_keep_observed_detector_orientation(monkeypatch, tmp_path):
    angle = np.deg2rad(30)
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [51, 51]
    wcs.wcs.crval = [210, 54]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.cd = 0.25 / 3600 * np.array([
        [-np.cos(angle), np.sin(angle)], [np.sin(angle), np.cos(angle)],
    ])
    path = tmp_path / "rotated.fits"
    fits.PrimaryHDU(np.ones((101, 101)), header=wcs.to_header()).writeto(path)
    captured = {}
    monkeypatch.setattr("findingchart_guiplotter.web.WEB_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("findingchart_guiplotter.web.measured_image_fwhm_arcsec", lambda image, target: (None, None))
    def fake_export(path, image, target, settings):
        captured["shape"] = image.data.shape
        captured["rotation"] = image.wcs.pixel_scale_matrix[0, 1]
        path.write_text("ok")
    monkeypatch.setattr("findingchart_guiplotter.web.export_chart", fake_export)
    render_from_payload({
        "ra_deg": 210, "dec_deg": 54, "image_source": "observed",
        "observed_fits_base64": base64.b64encode(path.read_bytes()).decode(),
        "align_observed_north_up": False,
    })
    assert captured["shape"] == (101, 101)
    assert captured["rotation"] != 0
