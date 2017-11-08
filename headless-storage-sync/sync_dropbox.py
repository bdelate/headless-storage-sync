import dropbox


class Sync:

    def __init__(self, config):
        self.config = config

    def list_content(self):
        dbx = dropbox.Dropbox(self.config['token'])
        for entry in dbx.files_list_folder('').entries:
            print(entry.name)
