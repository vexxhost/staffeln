from __future__ import annotations

from flask import Flask
from flask import request
from flask import Response
from oslo_log import log

from staffeln.common import context
from staffeln import objects

ctx = context.make_context()
app = Flask(__name__)

LOG = log.getLogger(__name__)


@app.route("/v1/backup", methods=["POST"])
def backup_id():

    if "backup_id" not in request.args:
        # Return error if the backup_id argument is not provided.
        return Response(
            "Error: backup_id is missing.", status=403, mimetype="text/plain"
        )

    # Retrive the backup object from backup_data table with matching backup_id.
    backup = objects.Volume.get_backup_by_backup_id(  # pylint: disable=E1120
        context=ctx, backup_id=request.args["backup_id"]
    )
    # backup_info is None when there is no entry of the backup id in
    # backup_table. So the backup should not be the automated backup.
    if backup is None:
        return Response(
            "True",
            status=200,
            mimetype="text/plain",
        )
    return Response("False", status=200, mimetype="text/plain")


@app.route("/v1/health", methods=["GET"])
def health():
    # Make sure API service can access to DB with no error.
    objects.Volume.get_backup_by_backup_id(  # pylint: disable=E1120
        context=ctx, backup_id="api-health-check"
    )
    return Response(
        "True",
        status=200,
        mimetype="text/plain",
    )


def run(host, port, ssl_context):
    app.run(host=host, port=port, ssl_context=ssl_context)
