################################################################################
# GOSSI supplemental index: START_TIME/STOP_TIME when the label has no IMAGE_TIME
################################################################################
"""Times for labels with IMAGE_TIME = UNK come from the spacecraft clock count."""

from typing import Any

import julian
import pytest
from oops.hosts.galileo import Galileo

from metadata_tools.hosts.GO_0xxx import index_config

# These tests furnish the leapseconds and Galileo SCLK kernels (see the integration
# marker in pyproject.toml).
pytestmark = pytest.mark.integration

# GO_0002/RAW_CAL/C0003061200R.LBL: a post-launch checkout frame with no IMAGE_TIME
UNKNOWN_TIME_LABEL: dict[str, Any] = {
    'SPACECRAFT_CLOCK_START_COUNT': '00030612.00',
    'IMAGE_TIME': 'UNK',
    'EXPOSURE_DURATION': 800.0,
}

# GO_0002/VENUS/C0018062600R.LBL: a frame that gives both fields
KNOWN_TIME_LABEL: dict[str, Any] = {
    'SPACECRAFT_CLOCK_START_COUNT': '00180626.00',
    'IMAGE_TIME': '1990-02-10T05:12:17.082Z',
    'EXPOSURE_DURATION': 800.0,
}

LABEL_PATH = 'GO_0002/RAW_CAL/C0003061200R.LBL'   # not read by the key functions


def _tai(iso: str) -> float:
    return float(julian.tai_from_iso(iso))


#===============================================================================
def test_unknown_image_time_comes_from_sclk() -> None:
    """With IMAGE_TIME = UNK, START_TIME is the clock count and STOP_TIME adds the
    exposure."""

    start = index_config.key__start_time(LABEL_PATH, dict(UNKNOWN_TIME_LABEL))
    stop = index_config.key__stop_time(LABEL_PATH, dict(UNKNOWN_TIME_LABEL))

    assert start != 'UNK'
    assert stop != 'UNK'
    assert start.startswith('1989-10-27T21:11:3')        # nine days after launch
    assert _tai(stop) - _tai(start) == pytest.approx(0.8, abs=1.e-6)


#===============================================================================
def test_known_image_time_is_untouched() -> None:
    """A label with IMAGE_TIME keeps the half-exposure offsets from the midtime."""

    start = index_config.key__start_time(LABEL_PATH, dict(KNOWN_TIME_LABEL))
    stop = index_config.key__stop_time(LABEL_PATH, dict(KNOWN_TIME_LABEL))

    midtime = _tai(KNOWN_TIME_LABEL['IMAGE_TIME'])
    assert _tai(start) == pytest.approx(midtime - 0.4, abs=1.e-6)
    assert _tai(stop) == pytest.approx(midtime + 0.4, abs=1.e-6)

    # The clock count agrees with IMAGE_TIME to seconds on a frame that has both
    from_sclk = julian.tai_from_tdb(
                    Galileo.tdb_from_sclk(KNOWN_TIME_LABEL['SPACECRAFT_CLOCK_START_COUNT']))
    assert abs(from_sclk - midtime) < 10.


#===============================================================================
def test_unknown_time_and_count_pass_through() -> None:
    """With neither field available, UNK is still written."""

    label = dict(UNKNOWN_TIME_LABEL)
    del label['SPACECRAFT_CLOCK_START_COUNT']
    assert index_config.key__start_time(LABEL_PATH, label) == 'UNK'
    assert index_config.key__stop_time(LABEL_PATH, label) == 'UNK'
