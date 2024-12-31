import gdown
import pandas as pd

class OracleElixirDownloader:

    def __init__(self, database):
        self.database = database

    def download_csv(self):
        file_id = "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN"
        url = f"https://drive.google.com/uc?id={file_id}"
        output = "2024_LoL_esports_match_data.csv"
        gdown.download(url, output, quiet=False)

    def read_csv(self):
        file_id = "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN"
        url = f"https://drive.google.com/uc?id={file_id}"
        csv = pd.read_csv(url,dtype={'url': 'str'})
        return csv

    def save_all_db(self):
        df = self.read_csv()
        df = df.rename(columns={'year':'game_year','date':'game_date','dragons (type unknown)':'dragons_type_unknown', 'team kpm':'team_kpm', 'earned gpm':'earned_gpm', 'total cs':'total_cs'})
        self.database.insert_oracle_elixir(df)





