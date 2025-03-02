import json
from pathlib import Path

class MetaData:

    def __init__(self):
        self.db_info = None
        self.basic_info = None
        self.prompt = None
        self.key = None
        self.image_modifier_info = None
        self.config_dir = Path(__file__).parent
        self.load_all_json()

    def load_json(self, file_name):
        file_path = self.config_dir / file_name
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_all_json(self):
        self.db_info = self.load_json('db_info.json')
        self.basic_info = self.load_json('basic_info.json')
        self.prompt = self.load_json('prompt.json')
        self.key = self.load_json('key.json')
        self.image_modifier_info = self.load_json('image_modifier_info.json')

