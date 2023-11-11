"""
Reads config.yaml when imported.
This means that config.yaml will be read multiple times. Welcome to Python.

Exits if the config is not found or invalid.
"""

from ruamel.yaml import YAML
from pathlib import Path

class Config(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Config, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        path = Path('config.yaml')
        if not path.exists():
            print("Error:", path, "not found!")
            exit(-1)
        try:
            yaml=YAML(typ='safe')
            self.config = yaml.load(path)
        except Exception as exc:
            print(exc)
            exit(-1)
        # Some basic config verification:
        if(self.config['acquisition_rate'] < self.config['bin_size']):
            print("")
            print("Error: Trying to show more samples than acquired")
            print("Please choose acquisition_rate >= bin_size")
            exit(0)
        # Type conversions:
        # Unfortunately the easier scientific (1e10) notation is float by default..
        self.config['acquisition_rate'] = int(self.config['acquisition_rate'])
        self.config['bin_size'] = int(self.config['bin_size'])
        self.config['buffer_size'] = int(self.config['buffer_size'])

def get_config():
    return Config().config

# Export config with the legacy names:

CHANNELS = get_config()['channels']
START_CTR = get_config()['start_ctr']
END_CTR = get_config()['end_ctr']

ACQUISITION_RATE = get_config()['acquisition_rate']
BUFFER_SIZE = get_config()['buffer_size']
CANVAS_SIZE = (get_config()['canvas_width'], get_config()['canvas_height'])
BIN_SIZE = get_config()['bin_size']

# derived values:
PLAIN_BUFFER_SIZE = BUFFER_SIZE * CHANNELS
SAMPLES_PER_BIN = ACQUISITION_RATE // BIN_SIZE
