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
    backup_info = objects.Volume.get_backup_by_backup_id(ctx, backup_id)
    # backup_info is None when there is no entry of the backup id in backup_table.
    if backup_info is None:
        LOG.info("No record of backup in storage. Checking cloud for backup")
        try:
            backup = conn.block_storage.get_backup(backup_id)
        except exc.ResourceNotFound:
            return Response(
                "Backup Resource not found for the provided backup id.",
                status=404,
                mimetype="text/plain",
            )
        except:
            return Response("Internal Server Error.", status=500, mimetype="text/plain")
        metadata = backup.metadata
        if metadata is not None:
            if metadata["__automated_backup"] is True:
                return Response("Deny", status=401, mimetype="text/plain")

        return Response(
            "True",
            status=200,
            mimetype="text/plain",
        )
    metadata = backup_info.backup_metadata
    if metadata["__automated_backup"] is True:
        return Response("Deny", status=401, mimetype="text/plain")
    else:
        return Response("True", status=200, mimetype="text/plain")


def run(host, port, ssl_context):
    app.run(host=host, port=port, ssl_context=ssl_context)
