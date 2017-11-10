import json
from sync_dropbox import SyncDropbox


def load_config():
    try:
        with open('config.json') as json_data:
            return json.load(json_data)
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    config = load_config()
    if config is not None:
        sync_dropbox = SyncDropbox(config=config['Dropbox'])
        sync_dropbox.sync()
