import json
import os
from sync_dropbox import Sync


def load_config():
    home_path = os.path.expanduser('~')
    try:
        with open('{}/.headless-storage-sync/config.json'.format(home_path)) as json_data:
            return json.load(json_data)
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    config = load_config()
    if config is not None:
        sync_dropbox = Sync(config=config['Dropbox'])
        sync_dropbox.list_content()
