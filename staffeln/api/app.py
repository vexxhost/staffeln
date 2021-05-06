from flask import Flask
from flask import Response
from flask import jsonify
from flask import request
from staffeln import objects
from staffeln.common import context
from staffeln.common import auth
from oslo_log import log
from openstack import exceptions as exc


ctx = context.make_context()
app = Flask(__name__)

LOG = log.getLogger(__name__)

conn = auth.create_connection()


@app.route("/v1/backup", methods=["GET"])
def backup_id():
    if "backup_id" not in request.args:
        # Return error if the backup_id argument is not provided.
        return "Error: No backup_id field provided. Please specify backup_id."

    backup_id = request.args["backup_id"]
    # Retrive the backup object from backup_data table with matching backup_id.
    backup = objects.Volume.get_backup_by_backup_id(ctx, backup_id)
    # backup_info is None when there is no entry of the backup id in backup_table.
    # So the backup should not be the automated backup.
    if backup is None:
        return Response(
            "True",
            status=200,
            mimetype="text/plain",
        )
    else:
        return Response("Deny", status=401, mimetype="text/plain")


def run(host, port, ssl_context):
    app.run(host=host, port=port, ssl_context=ssl_context)
