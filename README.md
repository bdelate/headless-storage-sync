# headless-storage-sync
Cloud storage sync for headless Linux servers

Currently only supports Dropbox.

### Features
* Monitor multiple folders on the server
* Upload new or modified files from server to Dropbox
* Download modified files from Dropbox to server (if the files already exist on the server)
* Optionally delete files older than X days on the server and Dropbox

### Requirements
* dropbox-sdk-python (pip install dropbox)

### Usage
1. Have a valid Dropbox account
2. Register a new dropbox app for your account: https://www.dropbox.com/developers/apps
3. Generate an access token for the app
4. Make a copy of the `config_template.json` file and rename it as `config.json`
`$ cp ./config_template.json ./config.json`
```
{
	"Dropbox": {
		"token": "insert_OAuth_token_here",
		"directories": [{
			"local": "full_path_to_local_directory",
			"remote": "full_path_to_dropbox_directory",
			"delete_old_days": 0
		}]
	}
}
```
5. Edit 'config.json' and enter the relevant local and dropbox directories to sync
  * All sub directories and files will be synced
  * To sync multiple root directories (and all sub directories), create additional json blocks within the directories list. Each directories item requires the fields: `local`, `remote`, `delete_old_days`
6. Use the `delete_old_days` field to indicate when old files (locally and on Dropbox) should be deleted. A value of 0 means files will not be deleted.
7. Enter the app token generated in step 3 into the `token` field

Use cron to run this on a schedule. If using a virtualenv, ensure cron uses the python installed in the virtualenv. The following example will run daily at 1am:
> 00 01 * * * cd /full/path/to/headless-storage-sync && /full/path/to/venv/bin/python run.py
