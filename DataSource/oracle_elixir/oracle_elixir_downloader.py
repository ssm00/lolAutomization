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

    def read_csv(self):
        file_id = "1v6LRphp2kYciU4SXp0PCjEMuev1bDejc"
        url = f"https://drive.google.com/uc?id={file_id}"
        csv = pd.read_csv(url,dtype={'url': 'str'})
        return csv

    def update_oracle_elixirs(self):
        df = self.read_csv()
        df = df.rename(columns={'year':'game_year','date':'game_date','dragons (type unknown)':'dragons_type_unknown', 'team kpm':'team_kpm', 'earned gpm':'earned_gpm', 'total cs':'total_cs', 'champion':'name_us'})
        position_mapping = {
            'sup': 'support',
            'jng': 'jungle',
            'bot': 'bottom'
        }
        df['position'] = df['position'].replace(position_mapping)
        last_date = self.database.get_last_date_from_db()
        if not pd.api.types.is_datetime64_any_dtype(df['game_date']):
            df['game_date'] = pd.to_datetime(df['game_date'])
        df = df[df['game_date'] > last_date]
        self.database.insert_oracle_elixir(df)
        self.database.update_patch_url_number()

