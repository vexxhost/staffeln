from flask import Flask
from flask import Response
from flask import request
from staffeln import objects
from staffeln.common import context
from oslo_log import log


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
    backup = objects.Volume.get_backup_by_backup_id(ctx, request.args["backup_id"])
    # backup_info is None when there is no entry of the backup id in backup_table.
    # So the backup should not be the automated backup.
    if backup is None:
        return Response(
            "True",
            status=200,
            mimetype="text/plain",
        )
    else:
        return Response("False", status=401, mimetype="text/plain")


def run(host, port, ssl_context):
    app.run(host=host, port=port, ssl_context=ssl_context)
