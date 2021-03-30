# Staffeln

## Project Description

This solution is a volume-level scheduled backup to implement a non-intrusive automatic backup for Openstack VMs.  

All volumes attached to the specified VMs are backed up periodically.

File-level backup will not be provided. The volume can be restored and attached to the target VM to restore any needed files. Users can restore through Horizon or the cli in self-service.

## Functions

### Function Overview

The solution backs up all volumes attached to VMs which have a pre-defined metadata set, for
example, `backup=yes`.
First, it gets the list of VMs which have backup metadata and the list of volumes attached to the
VMs in the given project by consuming the Openstack API (nova-api and cinder-api). Once the
volume list is prepared, then it consumes cinder-backup API to perform the backup.
Once the backup is successful, the backup time is updated in the metadata - `last-backup-time` of
the VM.

* *Filtering volumes:* It skips specific volumes if the volume metadata includes a specific
`skip-volume-backup` flag.
* *Limitation:* The number of volumes which users can backup is limited. Once the backup
count exceeds the quota which is defined per project, the backup job would fail.
* *Naming convention:* The backup volume name would be
{VOLUME_NAME}-{BACKUP_DATE}.
* Compression: all backup volumes are compressed at the ceph level. The compression
mode, compression algorithm and required parameters are configured by the user.

### Retention

Based on the configured retention policy, the volumes are removed.
Openstack API access policies are customized to make only the retention service be able to delete
the backups and users not.

### Scheduling

Backup and retention processes are scheduled by Crontab. It will be completing this in batches.
It can be scheduled at a specific time and also every specified period.

### Scaling

Cinder backup service is running on the dedicated backup host and it can be scaled across multiple
backup hosts.

### Notification

Once the backup is finished, the results are notified to the specified users by email regardless of
whether it was successful or not (the email will be one digest of all backups).
Backup result HTML Template
- Backup time
- Current quota usage(Quota/used number/percentage) with proper colors
  - 50% > Quota usage : Green
  - 80% > Quota 50% usage : Yellow
  - Quota usage > 80% : Red
- Volume list
- Success/fail: true/false with proper colors
  - Fail: Red
  - Success: Green
- Fail reason

### Settings

Users can configure the settings to control the backup process. The parameters are;
- Backup period
- Volume filtering tag
- Volume skip filter metadata tag
- Volume limit number
- Retention time
- Archival rules
- Compression mode, algorithm and parameters
- Notification receiver list
- Notification email HTML template
- Openstack Credential

### User Interface

- Users can get the list of backup volumes on the Horizon cinder-backup panel. This panel
has filtering and pagination functions which are not default ones of Horizon.
- Users cannot delete the volumes on the UI. “Delete Volume Backup” button is disabled on
the cinder-backup panel.

## Dependencies

* openstacksdk (API calls)
* Flask (HTTP API)
* oslo.service (long-running daemon)
* pbr (using setup.cfg for build tooling)
* oslo.db (database connections)
* oslo.config (configuration files)


## Architecture

### HTTP API (staffeln-api)

This project will need a basic HTTP API.  The primary reason for this is because when a user will attempt to delete a backup, we will use [oslo.policy via HTTP](https://docs.openstack.org/oslo.policy/victoria/user/plugins.html) to make sure that the backup they are attempting to delete is not an automated backup.

This API will be unauthenticated and stateless, due to the fact that it is simply going to return the plain-text string True or fail with 401 Unauthorized.  Because of the simplicity of this API, [Flask](https://flask.palletsprojects.com/en/1.1.x/) is an excellent tool to be able to build it out.

The flow of the HTTP call will look like the following:

1. HTTP request received through oslo.policy when backup being deleted with ID
2. Server look up backup ID using OpenStack API
3. If backup metadata contains `__automated_backup=True` then deny, otherwise allow.

With that flow, we’ll be able to protect automated backups from being deleted automatically.  In order to build a proper architecture, this application will be delivered as a WSGI application so it can be hosted via something like uWSGI later.

### Daemon (staffeln-conductor)

The conductor will be an independent daemon that will essentially scan all the virtual machines (grouped by project) which are marked to have automatic backups and then automatically start queueing up backups for them to be executed by Cinder.

Once backups for a project are done, it should be able to start running the rotation policy that is configured on all the existing volumes and then send out a notification email afterwards to the user.

The daemon should be stateful and ensure that it has its own state which is stored inside of a database.
