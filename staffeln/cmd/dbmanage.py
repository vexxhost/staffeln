"""
Run storage database migration.
"""

import sys

from oslo_config import cfg
from staffeln import conf
from staffeln.common import service
from staffeln.db import migration

CONF = conf.CONF


class DBCommand(object):
    @staticmethod
    def create_schema():
        migration.create_schema()

    @staticmethod
    def do_upgrade():
        migration.upgrade(CONF.command.revision)


def add_command_parsers(subparsers):

    parser = subparsers.add_parser("create_schema", help="Create the database schema.")
    parser.set_defaults(func=DBCommand.create_schema)

    parser = subparsers.add_parser("upgrade", help="Upgrade the database schema.")
    parser.add_argument("revision", nargs="?")
    parser.set_defaults(func=DBCommand.do_upgrade)


command_opt = cfg.SubCommandOpt(
    "command", title="Command", help="Available commands", handler=add_command_parsers
)


def register_sub_command_opts():
    cfg.CONF.register_cli_opt(command_opt)


def main():
    register_sub_command_opts()

    valid_commands = set(
        [
            "create_schema",
            "do_upgrade",
        ]
    )
    if not set(sys.argv).intersection(valid_commands):
        sys.argv.append("create_schema")
        sys.argv.append("do_upgrade")

    service.prepare_service(sys.argv)
    CONF.command.func()
