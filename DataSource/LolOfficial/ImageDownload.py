import requests as re
import re as regex
from pathlib import Path


class ImageDownload:

    def __init__(self, database):
        self.image_path = Path(__file__).parent.parent.parent / "Assets" / "Image"
        self.database = database
        self.header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
                'sec-ch-ua-mobile': '?0',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'Referer': 'https://www.google.com/'
            }

    def champion_background(self, champion_name):
        champion_name = champion_name+"_0"
        url = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champion_name}.jpg"
        response = re.get(url, headers=self.header)
        if response.status_code == 200:
            file_name = f"{self.image_path}/champion/{champion_name}.jpg"
            with open(file_name, 'wb') as file:
                file.write(response.content)
        else:
            print(f"로컬 파일 저장 에러: {champion_name} \n {response}")

    def all_champion_background(self):
        name_df = self.database.get_official_image_name()
        name_list = name_df["lol_official_image_name"]
        for name in name_list:
            self.champion_background(name)

