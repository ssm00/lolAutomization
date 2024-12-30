import json
import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MetaData:

    def __init__(self, config_dir='./MyMetaData'):
        self.db_info = None
        self.config_dir = Path(config_dir)
        self.load_all_json()

    def load_json(self, file_name):
        file_path = self.config_dir / file_name
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_all_json(self):
        self.db_info = self.load_json('db_info.json')

