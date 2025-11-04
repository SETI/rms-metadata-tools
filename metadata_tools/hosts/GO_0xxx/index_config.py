##########################################################################################
# host_config.py for GLL SSI
#
#  Host-specific utilites and key functions for index file generation.
#
##########################################################################################
import julian
import vicar
import warnings

from filecache import FCPath

import metadata_tools.util as util
import host_config as hconf


##########################################################################################
# Key functions (optional)
##########################################################################################

#=========================================================================================
def _event_tai(label_path, label_dict, stop=False):
    """Utility function for start/stop times.  FOR GOSSI, IMAGE_TIME refers to the center
       of the exposure.

    Args:
        label_path        path to the PDS label.
        label_dict        dictionary containing the PDS label fields.
        stop              If False, the start time is returned.

    Returns:
        float: The requested TAI time.
    """
    # get IMAGE_TIME; pass though any NULL value
    image_time = label_dict['IMAGE_TIME']
    if image_time == 'UNK':
        return image_time
    image_tai = julian.tai_from_iso(image_time)

    # compute offset from IMAGE_TIME
    exposure = label_dict['EXPOSURE_DURATION'] / 1000
    sign = 2*(int(stop)-0.5)

    # offset to requested time
    return image_tai + sign*0.5*exposure

#=========================================================================================
def _spacecraft_clock_start_count_from_label(label_dict):
    """Function for SPACECRAFT_CLOCK_START_COUNT using the SPACECRAFT_CLOCK_START_COUNT
       field.

    Args:
        label_dict (dict):  Dictionary containing the PDS label fields.

    Returns:
        str: SCLK start count.
    """
    start_count = label_dict['SPACECRAFT_CLOCK_START_COUNT']
    start_fields = util.sclk_split_count(start_count)
    return util.sclk_format_count(start_fields, 'nnnnnnnn:nn:n:n')

#=========================================================================================
def _spacecraft_clock_stop_count_from_label(label_dict):
    """Function for SPACECRAFT_CLOCK_STOP_COUNT using the SPACECRAFT_CLOCK_START_COUNT

       The stop count is computed by adding the exposure time (in ticks) to the
       SPACECRAFT_CLOCK_START_COUNT field.  THe exposure time is rounded up to the next
       tick.

    Args:
        label_dict        dictionary containing the PDS label fields.

    Returns:
        str: SCLK start count.
    """
    start_count = label_dict['SPACECRAFT_CLOCK_START_COUNT']
    start_fields = util.sclk_split_count(start_count)

    exposure = label_dict['EXPOSURE_DURATION'] / 1000
    exposure_ticks = exposure*120
    exposure_fields, over = util.rebase(exposure_ticks, hconf.SCLK_BASES, ceil=True)

    stop_fields = util.add_by_base(start_fields, exposure_fields, hconf.SCLK_BASES)
    return util.sclk_format_count(stop_fields[1:], 'nnnnnnnn:nn:n:n')

#=========================================================================================
def key__product_creation_time(label_path, label_dict):
    """Key function for PRODUCT_CREATION_TIME.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under PRODUCT_CREATION_TIME.
    """
    # Get path for VICAR image
    label_path = FCPath(label_path)
    image_path = label_path.with_suffix('.IMG')

    # Read the VICAR label and take the latest DAT_TIM value
    try:
        local_path = image_path.retrieve()
#        viclab = vicar.VicarLabel.from_file(local_path)
        viclab = vicar.VicarLabel(local_path, strict=False)
    except FileNotFoundError:
        raise FileNotFoundError(image_path)
    except vicar.VicarError as err:
        warnings.warn(f'VICAR error in file {image_path}, '
                      f'PRODUCT_CREATION_TIME cannot be determined: {err}', RuntimeWarning)
        return None

    pct = viclab['DAT_TIM', -1]

    # Convert to ISO format
    pct = pct[20:] + pct[3:20]

    return julian.iso_from_tai(
                julian.tai_from_day_sec(
                *julian.day_sec_in_strings(pct, first=True)), digits=3, suffix='Z')

#=========================================================================================
def key__start_time(label_path, label_dict):
    """Key function for START_TIME.  For GOSSI, IMAGE_TIME refers to the center of the
       exposure.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under START_TIME.
    """
    label_path = FCPath(label_path)

    # get start tai; pass though any NULL value
    start_tai = _event_tai(label_path, label_dict)
    if start_tai == 'UNK':
        return start_tai
    start_time = julian.iso_from_tai(start_tai, digits=6, suffix='Z')

    return start_time

#=========================================================================================
def key__stop_time(label_path, label_dict):
    """Key function for STOP_TIME.  For GOSSI, IMAGE_TIME refers to the center of the
       exposure.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under STOP_TIME.
    """
    label_path = FCPath(label_path)

    # get stop tai; pass though any NULL value
    stop_tai = _event_tai(label_path, label_dict, stop=True)
    if stop_tai == 'UNK':
        return stop_tai
    stop_time = julian.iso_from_tai(stop_tai, digits=6, suffix='Z')

    return stop_time

#=========================================================================================
def key__spacecraft_clock_start_count(label_path, label_dict):
    """Key function for SPACECRAFT_CLOCK_START_COUNT.  Note this definition supercedes
       that in the default index file.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under SPACECRAFT_CLOCK_START_COUNT.
    """
    return _spacecraft_clock_start_count_from_label(label_dict)

#=========================================================================================
def key__spacecraft_clock_stop_count(label_path, label_dict):
    """Key function for SPACECRAFT_CLOCK_STOP_COUNT.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under SPACECRAFT_CLOCK_STOP_COUNT.
    """
    return _spacecraft_clock_stop_count_from_label(label_dict)

#=========================================================================================
def key__on_chip_mosaic_flag(label_path, label_dict):
    """Key function for SPACECRAFT_CLOCK_STOP_COUNT.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under SPACECRAFT_CLOCK_STOP_COUNT.
    """
    # Return Y for all SL9 images
    image_time = label_dict['IMAGE_TIME']
    if image_time != 'UNK':
        image_tai = julian.tai_from_iso(image_time)
        start_time = '1994-07-19T09:46:37.667Z'
        stop_time = '1994-07-22T07:45:16.781Z'
        start_tai = julian.tai_from_iso(start_time)
        stop_tai = julian.tai_from_iso(stop_time)

        if start_tai <= image_tai <= stop_tai:
            return 'Y'

    # Return None if keyword not present
#    if not 'ON_CHIP_MOSAIC_FLAG' in label_dict:
    if 'ON_CHIP_MOSAIC_FLAG' not in label_dict:
        return None

    # Return value if keyword present
    return label_dict['ON_CHIP_MOSAIC_FLAG']

#=========================================================================================
def key__compression_quantization_table_id(label_path, label_dict):
    """Key function for CMPRS_QUANTZ_TBL_ID.

    Args:
        label_path  (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Value to write in the index file under SPACECRAFT_CLOCK_STOP_COUNT.
    """
#    if not 'CMPRS_QUANTZ_TBL_ID' in label_dict:
    if 'CMPRS_QUANTZ_TBL_ID' not in label_dict:
        return None
    return label_dict['CMPRS_QUANTZ_TBL_ID']
##########################################################################################
