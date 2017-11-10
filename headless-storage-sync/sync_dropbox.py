import dropbox
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
        - Loop through each local directory listed in config.log. Walk through each subdirectory and download a list of the corresponding
        dropbox directory files.
        - If local file is containined in list of remote files, check stats and upload file again if stats
        do not match.
        - If local file is not containied in list of remote files, upload it
        """
        for directory in self.config['directories']:
            for root, directories, files in os.walk(directory['local'], topdown=True):
                sub_directory = root[len(directory['local']):].strip(os.path.sep)
                listing = self.list_directory_content(root=directory['remote'], sub_directory=sub_directory)
                for name in files:
                    fullname = os.path.join(root, name)
                    name = unicodedata.normalize('NFC', name)
                    if name in listing:
                        meta_data = listing[name]
                        mtime = os.path.getmtime(fullname)
                        mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                        size = os.path.getsize(fullname)
                        if (isinstance(meta_data, dropbox.files.FileMetadata) and
                                mtime_dt == meta_data.client_modified and size == meta_data.size):
                            self.logger.info('{} is already synced [stats match]'.format(name))
                        else:
                            self.logger.info('local file: {} exists but has different stats. Downloading remote file'.format(name))
                            res = self.download(directory['remote'], sub_directory, name)
                            with open(fullname) as f:
                                data = f.read()
                            if res == data:
                                self.logger.info('{} is already synced [stats match]'.format(name))
                            else:
                                self.logger.info('{} local file changed since last sync. Uploading local file.'.format(name))
                                self.upload(fullname, directory['remote'], sub_directory, name, overwrite=True)
                    else:
                        self.upload(fullname, directory['remote'], sub_directory, name)

    def list_directory_content(self, root, sub_directory):
        path = '/{}/{}'.format(root, sub_directory.replace(os.path.sep, '/'))
        while '//' in path:
            path = path.replace('//', '/')
        path = path.rstrip('/')
        try:
            result = self.dbx.files_list_folder(path)
        except dropbox.exceptions.ApiError as err:
            return {}  # directory does not exist in dropbox
        else:
            return {entry.name: entry for entry in result.entries}

    def download(self, root, sub_directory, name):
        """Download a file.
        Return the bytes of the file, or None if it doesn't exist.
        """
        path = '/{}/{}/{}'.format(root, sub_directory.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        try:
            meta_data, result = self.dbx.files_download(path)
        except dropbox.exceptions.HttpError as err:
            self.logger.error('Http error: unable to download file name: {}'.format(path))
            return None
        data = result.content
        return data

    def upload(self, fullname, root, sub_directory, name, overwrite=False):
        """Upload a file.
        Return the request response, or None in case of error.
        """
        path = '/%s/%s/%s' % (root, sub_directory.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(fullname)
        with open(fullname, 'rb') as f:
            data = f.read()
        try:
            result = self.dbx.files_upload(data, path, mode,
                                           client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                                           mute=True)
        except dropbox.exceptions.ApiError as err:
            self.logger.error('API error: unable to upload file name: {}'.format(fullname))
            return None
        return result
