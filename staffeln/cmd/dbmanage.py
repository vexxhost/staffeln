"""
Run storage database migration.
"""

import sys

from oslo_config import cfg

from staffeln.common import service
from staffeln import conf
from staffeln.db import migration


CONF = conf.CONF


class DBCommand(object):
    @staticmethod
    def create_schema():
        migration.create_schema()


def add_command_parsers(subparsers):

    parser = subparsers.add_parser('create_schema', help="Create the database schema.")
    parser.set_defaults(func=DBCommand.create_schema)


command_opt = cfg.SubCommandOpt(
    'command', title='Command', help='Available commands', handler=add_command_parsers
)


def register_sub_command_opts():
    cfg.CONF.register_cli_opt(command_opt)


def main():
    register_sub_command_opts()

    valid_commands = set(
        [
            'create_schema',
        ]
    )
    if not set(sys.argv).intersection(valid_commands):
        sys.argv.append('create_schema')

    service.prepare_service(sys.argv)
    CONF.command.func()
