##########################################################################################
# common.py: common classes and functions
##########################################################################################
import argparse
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pdslogger
from filecache import FCPath

import metadata_tools.label_support as lab
import metadata_tools.util as util

##########################################################################################
# Logger management
##########################################################################################

# Define the global logger with streamlined output, no handlers so printing to stdout
_LOGGER = pdslogger.PdsLogger.get_logger('metadata', digits=0, lognames=False,
                               pid=False, indent=True, blanklines=False, level='info')
SYSTEM_NULL = "NONE"

#=========================================================================================
def init_logger(log_dir: FCPath, log_type: str) -> None:
    """Initialize logger.
    Args:
        log_dir: Directory to log.
        log_type: Type of log to create.
    Returns:
        None
    """
    name = '%s_%s-log.txt' % (log_dir.name, log_type)
    path = log_dir / name
    path.unlink(missing_ok=True)

    _LOGGER.add_handler(pdslogger.file_handler(path, level='normal'))
    _LOGGER.add_handler(pdslogger.STDOUT_HANDLER)
    _LOGGER.log('header', 'Initialized %s log for %s', log_type, log_dir.name)

#=========================================================================================

def get_logger() -> pdslogger.PdsLogger:
    """The global PdsLogger for the metadata tools."""
    return _LOGGER


##########################################################################################
# Cloud task management
##########################################################################################
task_list: list[dict[str, Any]] = []

#==========================================================================
def task_source() -> Iterator[dict[str, Any]]:
    """Task source generator for cloud_tasks.
    Args:
        None.
    Returns:
        None
    """
    yield from task_list

#==========================================================================
def add_task(volume_id: str, index_type: str) -> None:
    """Add a task to the task list.
    Args:
        volume_id: ID of volume to add.
        index_type: 'index' or 'geometry'.

    Returns:
        None
    """
    logger = get_logger()
    logger.info('Adding task for %s.', volume_id)

    task_id = index_type + '-task-' + volume_id
    task_args = {'volume_id' : volume_id}

    task_list.append({'task_id':task_id, 'data':task_args})

#==========================================================================
def write_task_file(task_file: str | None) -> None:
    """Write the tasks file.
    Args:
        task_file: Name of file to write.
    Returns:
        None
    """
    if not task_file:
        return
    FCPath(task_file).write_text(json.dumps(task_list, indent=2), encoding="utf-8")


##########################################################################################
# Argument parser
##########################################################################################

##########################################################################################
# PathAction class
##########################################################################################
class PathAction(argparse.Action):
    """Action method for path arguments.
    """
    def __call__(self, parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Any,
                 _option_string: str | None = None) -> None:
        if isinstance(values, list):
            values = values[0]
        vals = re.sub('://', '<<token>>', values)
        vals = re.sub('/+', '/', vals)
        vals = re.sub('<<token>>', '://', vals)
        setattr(namespace, self.dest, vals)

#=========================================================================================
def get_common_args(host: str | None = None,
                    volume_arg: str | None = 'volume_tree',
                    metadata_arg: str | None = 'metadata_tree',
                    output_arg: str | None = 'output_tree') -> argparse.ArgumentParser:
    """Common argument parser for metadata tools.

        Args:
            host: Host name, e.g. 'GOISS'.
            volume_arg: Name of volume_tree arg or None to skip this argument.
            metadata_arg: Name of volume_tree arg or None to skip this argument.
            output_arg: Name of volume_tree arg or None to skip this argument.

         Returns:
            Parser containing the common argument specifications.
   """

    # Define parser
    parser = argparse.ArgumentParser(
                    description='Metadata table generation utility%s.'
                                % ('' if not host else
                                   ' for ' + host))
    gr = parser.add_argument_group('Common Arguments')

    if volume_arg:
        parser.add_argument(volume_arg, type=str, metavar=volume_arg,
                            help='''Path to the top of the tree containing the
                                    volume data files.''', action=PathAction)
    if metadata_arg:
        gr.add_argument(metadata_arg, type=str, metavar=metadata_arg,
                        help='''Path to the top of the tree containing the
                                metadata files.''', action=PathAction)
    if output_arg:
        gr.add_argument(output_arg, type=str, metavar=output_arg,
                        help='''Path to the top of the tree in which to place the
                                new files.''', action=PathAction)

    gr.add_argument('--volumes', '-vv', type=str, metavar='volumes', nargs='*',
                    help='''If given, only these volumes are processed.''')
    gr.add_argument('--labels', '-l', action='store_true',
                    help='''If given, labels are generated for existing files.''')
    gr.add_argument('--pattern', '-p', type=str, metavar='pattern',
                    help='''Glob pattern to select files.''')
    gr.add_argument('--task-output', '-to', type=str, metavar='task_output',
                    help='''If given, a task file is written and no processing is performed.''')

    # Return parser
    return parser

##########################################################################################
# Table class
##########################################################################################
class Table:
    """Class describing a single table for a single volume.
    """

    #=====================================================================================
    def __init__(self, output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 volume_id: str | None = None, level: str | None = None,
                 qualifier: str | None = None, prefix: str | None = None,
                 suffix: str | None = None, use_global_template: bool = False) -> None:
        """Constructor for a table object.

        Args:
            output_dir:
                Directory in which to write the index files.
            template_path: Path to the host template.
            volume_id: Volume ID.
            level:
                Processing level: "summary", "detailed", or "index".
            qualifier:
                "sky", "sun", "ring", "body", "inventory", or "supplemental".
            prefix: File path prefix.
            suffix: File name suffix.
            use_global_template:
                If True, the label template is to be found in the global
                template directory.

        """
        self.template_path: FCPath | None = None
        if template_path:
            self.template_path = FCPath(template_path)
        self.volume_id = volume_id
        self.level = level
        self.qualifier = qualifier
        self.use_global_template = use_global_template
        self.rows: list[str] = []
        self.filename: FCPath

        if not output_dir:
            return

        if not suffix:
            suffix = "_%s_%s.tab" % (self.qualifier, self.level)
        prefix = FCPath(output_dir).joinpath(self.volume_id).as_posix()
        self.filename = FCPath(prefix + suffix)


    #=====================================================================================
    def write(self, labels_only: bool = False) -> None:
        """Write a table and its label.

        Args:
            labels_only:
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
            assert table_type is not None  # nosec B101 - type-narrowing invariant, not validation
            table_type += '_' + self.level
        lab.create(self.filename, self.template_path,
                   table_type=table_type, use_global_template=self.use_global_template)

##########################################################################################
