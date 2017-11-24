import dropbox
from dropbox_content_hasher import DropboxContentHasher
import os
import unicodedata
import datetime
import time
import logging


class SyncDropbox:

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    file_handler = logging.FileHandler('errors.log')
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    def __init__(self, config):
        self.config = config
        self.dbx = dropbox.Dropbox(self.config['token'])

    def sync(self):
        """
        - Loop through local directories listed in config.json.
        - Walk through each subdirectory and download a list of the corresponding dropbox files.
        - If local file is in the list of remote files: compare meta data and sync
            - else: upload new file (which will create the relevant directory if it doesn't already exist in Dropbox)
        """
        for directory in self.config['directories']:
            for local_root, local_directories, local_files in os.walk(directory['local'], topdown=True):
                subdirectory = local_root[len(directory['local']):].strip(os.path.sep)
                remote_listing = self.list_remote_directory_content(remote_root=directory['remote'], subdirectory=subdirectory)
                for local_file in local_files:
                    local_file_path = os.path.join(local_root, local_file)
                    local_file = unicodedata.normalize('NFC', local_file)
                    if local_file in remote_listing:
                        self.compare_meta_data(local_file_path=local_file_path,
                                               remote_file_meta_data=remote_listing[local_file],
                                               remote_root=directory['remote'],
                                               subdirectory=subdirectory,
                                               file_name=local_file)
                    else:
                        self.logger.info('{} new local file. Uploading to Dropbox'.format(local_file_path))
                        self.upload(local_file_path=local_file_path,
                                    remote_root=directory['remote'],
                                    subdirectory=subdirectory,
                                    file_name=local_file)

    def compare_meta_data(self, local_file_path, remote_file_meta_data, remote_root, subdirectory, file_name):
        """
        - compare local and remote files according to modified date/time, size and hash to determine if any
        files are out of sync. Upload / download accordingly.
        """
        local_file_mtime = os.path.getmtime(local_file_path)
        local_file_mtime_dt = datetime.datetime(*time.gmtime(local_file_mtime)[:6])
        local_file_size = os.path.getsize(local_file_path)
        if (isinstance(remote_file_meta_data, dropbox.files.FileMetadata) and
                local_file_mtime_dt == remote_file_meta_data.client_modified and local_file_size == remote_file_meta_data.size):
            self.logger.info('{} is already synced [stats match]'.format(local_file_path))
        else:
            if (local_file_mtime_dt > remote_file_meta_data.client_modified
                    and not self.compare_file_hash(local_file_path=local_file_path, remote_file_meta_data=remote_file_meta_data)):
                print('{} changed locally after remote file. Uploading new version to dropbox'.format(local_file_path))
                self.upload(local_file_path=local_file_path,
                            remote_root=remote_root,
                            subdirectory=subdirectory,
                            file_name=file_name,
                            overwrite=True)
            elif (local_file_mtime_dt < remote_file_meta_data.client_modified
                    and not self.compare_file_hash(local_file_path=local_file_path, remote_file_meta_data=remote_file_meta_data)):
                print('{} changed remotely after local file. Downloading new version from dropbox'.format(local_file_path))
                downloaded_file = self.download(remote_root=remote_root, subdirectory=subdirectory, file_name=file_name)
                if downloaded_file is not None:
                    with open(local_file_path, 'wb') as local_file:
                        local_file.write(downloaded_file)
                        local_file.close()

    def compare_file_hash(self, local_file_path, remote_file_meta_data):
        """
        - compute hash for local file and return true if it matches the already computed hash for the corresponding dropbox file
        """
        hasher = DropboxContentHasher()
        with open(local_file_path, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if len(chunk) == 0:
                    break
                hasher.update(chunk)
        local_file_hash = hasher.hexdigest()
        return remote_file_meta_data.content_hash == local_file_hash

    def list_remote_directory_content(self, remote_root, subdirectory):
        """
        - returns a dictionary containing meta data for each file in the specified remote subdirectory
        - if the remote subdirectory does not exist, return an empty dictionary
        """
        path = '/{}/{}'.format(remote_root, subdirectory.replace(os.path.sep, '/'))
        path = path.replace('//', '/')
        path = path.rstrip('/')
        try:
            result = self.dbx.files_list_folder(path)
        except dropbox.exceptions.ApiError as err:
            return {}  # directory does not exist in dropbox
        else:
            return {entry.name: entry for entry in result.entries}

    def download(self, remote_root, subdirectory, file_name):
        """
        - Download and return the bytes of a file, or None if it doesn't exist
        """
        path = '/{}/{}/{}'.format(remote_root, subdirectory.replace(os.path.sep, '/'), file_name)
        while '//' in path:
            path = path.replace('//', '/')
        try:
            meta_data, result = self.dbx.files_download(path)
        except dropbox.exceptions.HttpError as err:
            self.logger.error('Http error: unable to download file name: {}'.format(path))
            return None
        data = result.content
        return data

    def upload(self, local_file_path, remote_root, subdirectory, file_name, overwrite=False):
        """
        - Upload local file to corresponding dropbox location
        """
        path = '/%s/%s/%s' % (remote_root, subdirectory.replace(os.path.sep, '/'), file_name)
        while '//' in path:
            path = path.replace('//', '/')
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(local_file_path)
        with open(local_file_path, 'rb') as f:
            data = f.read()
        try:
            result = self.dbx.files_upload(data, path, mode, client_modified=datetime.datetime(*time.gmtime(mtime)[:6]), mute=True)
        except dropbox.exceptions.ApiError as err:
            self.logger.error('API error: unable to upload file name: {}'.format(local_file_path))
            return None
        return result
