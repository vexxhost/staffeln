# Staffeln

## Project Description

This solution is a volume-level scheduled backup to implement a non-intrusive
automatic backup for Openstack VMs.

All volumes attached to the specified VMs are backed up periodically.

File-level backup will not be provided. The volume can be restored and attached
to the target VM to restore any needed files. Users can restore through Horizon
or the cli in self-service.

## Staffeln Conductor Functions

Staffeln conductor manage all perodic tasks like backup, retention, and
notification. It's possible to have multiple staffeln conductor services
running. There will only be one service pulling volume and server information
from OpenStack and schedule backups. All conductor on the other hand, will be
able to take scheduled backup tasks and run backups and also check for backup
to completed. For single volume, only one backup task will be generated, and
only one of staffeln conductor service will be able to pick up that task that
the same time. Same as retention tasks.

### Backup

Staffeln is a service to help perform backup. What it does is with provided
authorization, Staffeln find a volume list with go through instance list from
OpenStack, and find instances has `backup_metadata_key` (which configured under
`[conductor]` section in `/etc/staffeln/staffeln.conf`) defined in metadata and
got volume attached. Collect those attached volumes into a list. Follow by
using that volume list to generate volume backup tasks in Staffeln. And do
backups, check work-in-progress backups accordingly. With role control, there
is only one Staffeln service that can perform volume collection and backup task
schedules at the same time. But all services can do backup action, and check
progress in parallel. Backup schedule trigger time is controlled by periodic
jobs separately across all Staffeln nodes. It’s possible a following backup
plan starts from a different node near previous success backup (with less than
`backup_service_period` of time) in Staffeln V1, but it’s fixed with
`backup_min_interval` config. And in either case, the Full and Incremental
backup order (config with `full_backup_depth`) is still be honored.
`backup_min_interval` is value that you config for how many seconds you like as
minimum interval between backups for same volume from Staffeln. The
configuration `full_backup_depth` under `[conductor]` section in
`/etc/staffeln/staffeln.conf` will decide how incremental backups are going to
perform. If `full_backup_depth` is set to 1. For each Full backup will follow
by only one incremental backup(not counting ). And 2 incremental if
`full_backup_depth` set to 2. Set to `0` if want all full backups.

To avoid long stucking backup action, config `backup_cycle_timout` should be
set with a reasonable time that long enough for backups to complete but good
enough to judge the backup process is stucking. When a backup process reach
this timeout, it will remove the backup task and try to delete the volume
backup. A followup backup object (marked as not completed) will be create and
set the create time to 10 years old so the remove progress will be observe and
retry on next retention job.

`backup_service_period` is no longer the only fector that reflect how long
volume should backup. It’s recommended to set `backup_min_interval` and
`report_period`(see in Report part) and config a related shorter
`backup_service_period`. For example if we set `backup_min_interval` to 3600
seconds and set `backup_service_period` to 600 seconds, the backup job will
trigger roughly every 10 minutes, and only create new backup when previous
backup for same volume created for more than 1 hours ago.

### Retention

On retention, backups which has creation time longer than retention time
(defined by `retention_time` from `/etc/staffeln/staffeln.conf` or
`retention_metadata_key` which added to metadata of instances) will put in list
and try to delete by Staffeln. Note: the actual key-value of
`retention_metadata_key` is customizable. Like in test doc, you can see
following property been added to instance
`--property __staffeln_retention=20min`.
Customized `retention_metadata_key` has larger
priority than `retention_time`. If no `retention_metadata_key` defined for
instance, `retention_time` will be used. With incremental backup exist,
retention will honored full and incremental backup order. That means some
backups might stay longer than it’s designed retention time as there are
incremental backups depends on earlier backups. The chain will stop when next
full backup created. Now retention only delete backup object from Staffeln DB
when backup not found in Cinder backup service.

For honor backups dependencies. When collected retention list for one volumes,
retention will start delete the later created one. And go through that order
till the very early created one. However, as Cinder might not honor the delete
request order. It’s possible that some of delete request in that situation
might failed. In Staffeln, will try to delete those failed request in next
periodic time.

It’s recommended to config `retention_time` according your default retention
needs, and well setup `retention_metadata_key` and update instance metadata to
schedule for the actual rentnetion for volumes from each instance.
`retention_service_period` is only for trigger checking if there are any
backups should be delete. So no need to set it to a too long period of time.

### Report

Report process is part of backup cron job. When one of Staffeln service got
backup schedule role and finish with backup schedule, trigger, and check work
in progress backup are done in this period. It will check if any successed or
failed backup task has not been reported for `report_period` seconds after it
created. It will trigger the report process. `report_period` is defined under
`[conductor]` with unit to seconds. Report will generate an HTML format of
string with quota, success and failed backup task list with proper HTML color
format for each specific project that has success or failed backup to report.
As for how the report will sent is base on your config and environment.

And if email sending failed, it will not send that report but provide message
for email failed in log. Staffeln will try to regenerate and resent report on
next periodic cycle. On the other hand, you can avoid config `sender_email`
from above, and make the report goes to logs directly. If you have specific
email addresses you wish to send to instead of using project name. You can
provide `receiver` config so it will send all project report to receiver list
instead. And if neither `recveiver` or `project_receiver_domain` are set, the
project report will try to grap project member list and gather user emails to
send report to. If no user email can be found from project member, Staffeln
will ignore this report cycle and retry the next cycle. Notice that, to
improve Staffeln performance and to reduce old backup result exist in Staffeln
DB, properly config email is recommended. Otherwise, not config any sender
information and make the reports goes to logs can be considered. When report
successfully sent to email or logs for specific project. all success/failed
tasks for that project will be purged from Staffeln.

The report interval might goes a bit longer than `report_period` base on the
backup service interval and previous backup works. For example on each backup
schedule role granted, it start all the backup schedule works also check bacup
in progress tasks with other staffeln services. And counting cron job sleep
interval, the report time might take longer than what configed in
`report_period`. But it will never goes earlier than `report_period`.

For report format. It’s written in HTML format and categorized by projects.
Collect information from all projects into one report, and sent it through
email or directly to log. And in each project, will provide information about
project name, quote status, backup succeeded list, and backup failed list. And
follow by second project and so on.

### Staffeln-API

Staffeln API service allows we defined cinder policy check and make sure all
Cinder volume backups are deleted only when that backup is not makaged by
Staffeln. Once staffeln API service is up. You can define similar policy as
following to `/etc/cinder/policy.yaml`:
```
"backup:delete" : "rule:admin_api or (project_id:%(project_id)s and
http://Staffeln-api-url:8808/v1/backup?backup_id=%(id)s)"
```

And when backup not exist in staffeln, that API will return TRUE and make the
policy allows the backup delete. Else will return False and only allow backup
delete when it's admin in above case.

## Settings

Users can configure the settings to control the backup process. Most of
functions are controlled through configurations. You will be able to find all
configurations under `staffeln/conf/*`

And defined them in `/etc/staffeln/staffeln.conf` before restart
staffeln-conductor service.

## User Interface

Users can get the list of backup volumes on the Horizon cinder-backup panel.
This panel has filtering and pagination functions which are not default ones of
Horizon. Users cannot delete the volumes on the UI if “Delete Volume Backup”
button is disabled on the cinder-backup panel from horizon.

## Service dependencies

* openstacksdk that can reach to Cinder, Nova, and Keystone

  Staffeln heavily depends on Cinder backup. So need to make sure that Cinder
  Backup service is stable. On the other hand, as backup create or delete
  request amount might goes high when staffeln processed with large amount of
  volume backup. It’s possible API request is not well processed or the request
  order is mixed. For delete backup, Staffeln might not be able to delete a
  backup right away if any process failed (like full backup delete request sent
  to Cinder, but it’s depends incremental backup delete request still not), but
  will keep that backup resource in Staffeln, and try to delete it again in
  later periodic job. Avoid unnecessary frequent of backup/retention interval
  will help to maintain the overall performance of Cinder.

  Make sure the metadata key that config through `backup_metadata_key` and
  `retention_metadata_key` are not conflict to any other services/ user who
  using Nova metadata.

* kubernetes lease (default lock backend)

  Staffeln depends on kubernetes lease that allow multiple services cowork
  together.

## Authentication dependencies

Staffeln by default uses regular openstack authentication methods. File
`/etc/staffeln/openrc` is usually the authentication file. Staffeln heavily
depends on authentication. Make sure the authentication method you provide
contains the following authorization in OpenStack:
* token authentication get user ID set authentication project get project list
* get server list get volume get backup create backup create barbican secret
* (this might required for backup create) delete backup delete barbican secret
* (this might required for backup delete) get backup quota get volume quota get
* user get role assignments

Notice all authorization required by above operation in OpenStack services
might need to be also granted to login user. It’s possible to switch
authentication when restarting staffeln service, but which work might lead to
unstoppable backup failure (with unauthorized warning) that will not block
services to run. You can resolve the warning by manually deleting the backup.

Note: Don’t use different authorizations for multiple staffeln services across
nodes. That will be chances lead to unexpected behavior like all other
OpenStack services. For example, staffeln on one node is done with backup
schedule plan and staffeln on another node picks it up and proceeds with it.
That might follow with Create failed from Cinder and lead to warning log pop-up
with no action achieved.

## Commands

List of available commands: staffeln-conductor: trigger major staffeln backup
service. staffeln-api: trigger staffeln API service staffeln-db-manage
create_schema staffeln-db-manage upgrade head

## Simple verify

After Staffeln well installed. First thing is to check Staffeln service logs to
see it’s well running.

First we need is something to backup on: In test scenario we will use cirros or
any smaller image to observe behavor Prepare your test OpenStack environment
with following steps:

Make sure cinder backup service is running
Make sure your openrc under `/etc/staffeln/staffeln.conf`
provide required authorization shows in `Authentication` section.
Run

```
openstack volume create --size 1 --image {IMAGE_ID} test-volume
openstack server create --flavor {FLAVOR_ID} --volume {VOLUME_ID} \
--property __staffeln_backup=true --property __staffeln_retention=20min \
--network {NETWROK_ID} staffeln-test
openstack volume create --size 1 --image {IMAGE_ID} test-volume-no-retention
openstack server create --flavor {FLAVOR_ID} --volume {VOLUME_ID} \
--property __staffeln_backup=true --network {NETWROK_ID} staffeln-test-no-retention
```

Now you can watch the result with
`watch openstack volume backup list` to check and observe how backup going.

Staffeln majorly depends on how it’s configuration and authentication provides.
When testing, make sure reference configurations list above in each section.
And it required a service restart to make the configuration/authentication
change works. If using systemd, you can use this example: `systemctl restart
staffeln-conductor staffeln-api`

And awared that if you have multiple nodes that running staffeln on, the backup
or retention check might goes a bit randomly some time, because it’s totally
depends on how the periodic period config in each node, and also depends on how
long the node been process previous cron job.

The email report testing is heavily depends on how your email system works.
Staffeln might behave differently or even raise error if your system didn’t
support it’s current process. The email part can directly tests against gmail
if you like. You can use application password for allow python sent email with
google’s smtp. To directly test email sending process. You can directly import
email from staffeln and use it as directly testing method.

To verify the setting for staffeln-api. you can directly using API calls to
check if backup check is properly running through `curl -X POST
Staffeln-api-url:8808/v1/backup?backup_id=BACKUP_ID` or `wget --method=POST
Staffeln-api-url:8808/v1/backup?backup_id=BACKUP_ID`.

It should return TRUE when BACKUP_ID is not exist in staffeln, else FALSE.
