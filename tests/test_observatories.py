from datetime import timezone

import astropy.units as u
import pytest
from astropy.coordinates import AltAz, SkyCoord
from astropy.time import Time
from astropy.utils import iers

from findingchart_guiplotter.observatories import OBSERVATORIES, parallactic_angle_deg
from findingchart_macapp.bridge.findingchart_bridge import _settings
from findingchart_guiplotter.models import Target


@pytest.fixture(autouse=True)
def offline_iers():
    with iers.conf.set_temp("auto_download", False):
        yield


def target_at_altitude(altitude):
    when = Time("2025-10-30T01:00:00", scale="utc")
    obs = OBSERVATORIES["La Palma"]
    target = SkyCoord(alt=altitude * u.deg, az=90 * u.deg,
                      frame=AltAz(obstime=when, location=obs.location, pressure=0 * u.hPa))
    return target.icrs, obs, when


@pytest.mark.parametrize("altitude", [-30, -0.01])
def test_pa_rejects_below_horizon(altitude):
    target, obs, when = target_at_altitude(altitude)
    with pytest.raises(ValueError, match="horizon"):
        parallactic_angle_deg(target, obs, when)


def test_visible_pa_still_matches_zenith_position_angle():
    target, obs, when = target_at_altitude(40)
    zenith = SkyCoord(alt=90*u.deg, az=0*u.deg,
                     frame=AltAz(obstime=when, location=obs.location)).icrs
    expected = target.position_angle(zenith).wrap_at(180*u.deg).deg
    assert parallactic_angle_deg(target, obs, when) == pytest.approx(expected, abs=0.5)


def test_bridge_propagates_below_horizon_error():
    coord, _, _ = target_at_altitude(-30)
    target = Target(display_name="Hidden", ra_deg=coord.ra.deg, dec_deg=coord.dec.deg)
    with pytest.raises(ValueError, match="horizon"):
        _settings({"useParallacticPA": True, "observationTimeISO": "2025-10-30T01:00:00Z"}, target, [])


@pytest.mark.parametrize("raw_time", ["2025-10-30T01:00:00", ""])
def test_bridge_requires_explicit_time_zone_for_parallactic_pa(raw_time):
    target = Target(display_name="SN", ra_deg=0, dec_deg=0)
    with pytest.raises(ValueError, match="[Uu][Tt][Cc]|timezone"):
        _settings({"useParallacticPA": True, "observationTimeISO": raw_time}, target, [])


def test_bridge_normalizes_offset_timestamp_to_utc():
    target = Target(display_name="SN", ra_deg=0, dec_deg=0)
    result = _settings({"observationTimeISO": "2025-10-30T03:00:00+02:00"}, target, [])
    assert result.observation_time.tzinfo == timezone.utc
    assert result.observation_time.hour == 1
