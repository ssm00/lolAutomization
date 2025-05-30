import gdown
import pandas as pd

class OracleElixirDownloader:

    def __init__(self, database):
        self.database = database

    def download_csv(self):
        file_id = "1v6LRphp2kYciU4SXp0PCjEMuev1bDejc"
        url = f"https://drive.google.com/uc?id={file_id}"
        output = "2025_LoL_esports_match_data.csv"
        gdown.download(url, output, quiet=False)

    def update_oracle_elixirs(self):
        file_id_2025 = "1v6LRphp2kYciU4SXp0PCjEMuev1bDejc"
        file_id_2024 = "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN"
        url = f"https://drive.google.com/uc?id={file_id_2025}"
        chunksize = 10000
        last_date = self.database.get_last_date_from_db()
        for chunk in pd.read_csv(url, dtype={'url': 'str'}, chunksize=chunksize):
            chunk = chunk.rename(columns={
                'year': 'game_year',
                'date': 'game_date',
                'dragons (type unknown)': 'dragons_type_unknown',
                'team kpm': 'team_kpm',
                'earned gpm': 'earned_gpm',
                'total cs': 'total_cs',
                'champion': 'name_us'
            })
            position_mapping = {
                'sup': 'support',
                'jng': 'jungle',
                'bot': 'bottom'
            }
            chunk['position'] = chunk['position'].replace(position_mapping)
            if 'patch' in chunk.columns:
                chunk['patch'] = chunk['patch'].astype(str).str.replace(r'^15\.(\d+)$', r'25.\1', regex=True)
            if not pd.api.types.is_datetime64_any_dtype(chunk['game_date']):
                chunk['game_date'] = pd.to_datetime(chunk['game_date'])
            chunk = chunk[chunk['game_date'] > last_date]
            self.database.insert_oracle_elixir(chunk)

