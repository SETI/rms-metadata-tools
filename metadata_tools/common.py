##########################################################################################
# common.py: common classes and functions
##########################################################################################
import re
import argparse
import json

from filecache import FCPath
import pdslogger

import metadata_tools.util as util
import metadata_tools.label_support as lab

##########################################################################################
# Logger management
##########################################################################################

# Define the global logger with streamlined output, no handlers so printing to stdout
_LOGGER = pdslogger.PdsLogger.get_logger('metadata', digits=0, lognames=False,
                               pid=False, indent=True, blanklines=False, level='info')
SYSTEM_NULL = "NONE"

#=========================================================================================
def init_logger(dir, type):
    """Initialize logger.
    Args:
        dir (FCPath): Directory to log.
        type (str): Type of log to create.
    Returns:
        None
    """
    name = '%s_%s-log.txt' % (dir.name, type)
    path = dir / name
    path.unlink(missing_ok=True)
    _LOGGER.add_handler(pdslogger.file_handler(path, level='warning'))

    _LOGGER.add_handler(pdslogger.STDOUT_HANDLER)

#=========================================================================================

def get_logger():
    """The global PdsLogger for the metadata tools."""
    return _LOGGER


##########################################################################################
# Cloud task management
##########################################################################################
task_list = []

#==========================================================================
def task_source():
    """Task source generator for cloud_tasks.
    Args:
        None.
    Returns:
        None
    """
    yield from task_list

#==========================================================================
def add_task(volume_id, index_type):
    """Add a task to the task file.
    Args:
        volume_id (str): ID of volume to add.
        index_type (str): 'index' or 'geometry'.

    Returns:
        None
    """
    logger = get_logger()
    logger.info('Adding task for %s.' % volume_id)

    task_id = index_type + '-task-' + volume_id
    task_args = {'volume_id' : volume_id}

    task_list.append({'task_id':task_id, 'data':task_args})

#==========================================================================
def write_task_file(task_file):
    """Write the tasks file.
    Args:
        task_file(str): Name of file to write.
    Returns: 
        None
    """
    if not task_file:
        return
    with open(task_file, "w") as file:
        json.dump(task_list, file, indent=2)


##########################################################################################
# Argument parser
##########################################################################################

##########################################################################################
# PathAction class
##########################################################################################
class PathAction(argparse.Action):
    """Action method for path arguments.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if isinstance(values, list):
            values = values[0]
        vals = re.sub('://', '<<token>>', values)
        vals = re.sub('//*', '/', vals)
        vals = re.sub('<<token>>', '://', vals)
        setattr(namespace, self.dest, vals)

#=========================================================================================
def get_common_args(parser, no_metadata=False):
    """Common argument parser for metadata tools.

        Args:
            parser (argparse.Parser): Parser create by argparse.ArgumentParser().
            no_metadata (bool): If True, metadata_tree is not is not needed.

         Returns:
            argparser.ArgumentParser :
                Parser containing the common argument specifications.
   """

    # Generate parser
    gr = parser.add_argument_group('Common Arguments')

    if not no_metadata:
        gr.add_argument('metadata_tree', type=str, metavar='metadata_tree',
                        help='''File path to the top of the tree containing the
                                metadata files.''', action=PathAction)
    gr.add_argument('output_tree', type=str, metavar='output_tree',
                    help='''File path to the top of the tree in which to place the
                            new files.''', action=PathAction)

    gr.add_argument('--volumes', '-v', type=str, metavar='volumes',
                    help='''If given, only these volumes are processed.''')
    gr.add_argument('--labels', '-l', action='store_true',
                    help='''If given, labels are generated for existing files.''')
    gr.add_argument('--pattern', '-p', type=str, metavar='pattern',
                    help='''Glob pattern to select files.''')

    # Return parser
    return parser

##########################################################################################
# Table class
##########################################################################################
class Table:
    """Class describing a single table for a single volume.
    """

    #=====================================================================================
    def __init__(self, output_dir=None, template_path=None,
                 volume_id=None, level=None, qualifier=None, prefix=None,
                 suffix=None, use_global_template=False):
        """Constructor for a table object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the index files.
            template_path (str, Path, or FCPath): Path to the host template.
            volume_id (str): Volume ID.
            level (str, optional):
                Processing level: "summary", "detailed", or "index".
            qualifier (str):
                "sky", "sun", "ring", "body", "inventory", or "supplemental".
            prefix (str): File path prefix.
            suffix (str): File name suffix.
            use_global_template (bool):
                If True, the label template is to be found in the global
                template directory.

        """
        self.template_path = None
        if template_path:
            self.template_path = FCPath(template_path)
        self.volume_id = volume_id
        self.level = level
        self.qualifier = qualifier
        self.use_global_template = use_global_template
        self.rows = []

        if not output_dir:
            return

        if not suffix:
            suffix = "_%s_%s.tab" % (self.qualifier, self.level)
        prefix = output_dir.joinpath(self.volume_id).as_posix()
        self.filename = FCPath(prefix + suffix)


    #=====================================================================================
    def write(self, labels_only=False):
        """Write a table and its label.

        Args:
            labels_only (bool, optional):
                If True, labels are generated for any existing geometry
                tables.

        Returns:
            None.
        """
        logger = get_logger()

        if not labels_only:
            if not self.rows:
                return

            # Write table
            logger.info("Writing: %s", self.filename)
            util.write_txt_file(self.filename, self.rows)

        # Write label
        table_type = self.qualifier
        if self.level:
            table_type += '_' + self.level
        lab.create(self.filename, self.template_path,
                   table_type=table_type, use_global_template=self.use_global_template)

##########################################################################################
