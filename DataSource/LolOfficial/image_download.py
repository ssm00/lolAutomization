import requests as re
import re as regex
from pathlib import Path
from PIL import Image
import io
from bs4 import BeautifulSoup
import os

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
        self.lol_eSport_header = {
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
            'origin': 'https://lolesports.com',
            'referer': 'https://lolesports.com/',
            'x-api-key': '0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z'
        }
        self.lck_standing_url = "https://esports-api.lolesports.com/persisted/gw/getStandings?hl=ko-KR&tournamentId=113480665704729522"


    def champion_background(self, official_name, ps_name):
        official_name = official_name + "_0"
        url = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{official_name}.jpg"
        response = re.get(url, headers=self.header)
        if response.status_code == 200:
            file_name = f"{self.image_path}/champion/{ps_name}.jpg"
            with open(file_name, 'wb') as file:
                file.write(response.content)
        else:
            print(f"로컬 파일 저장 에러: {official_name} \n {response}")

    def all_champion_background(self):
        name_df = self.database.get_champion_name()
        name_list = name_df[["lol_official_image_name", "ps_name"]]
        for index, row in name_list.iterrows():
            official_name = row['lol_official_image_name']
            ps_name = row['ps_name']
            self.champion_background(official_name, ps_name)

    def champion_icon(self):
        response = re.get("https://www.fow.lol/stats", headers=self.header)
        name_df = self.database.get_champion_name()
        kr_name_list = name_df['name_kr'].to_list()
        champion_codes = self.find_champion_codes(response.content, kr_name_list)
        name_mapping = dict(zip(name_df['name_kr'], name_df['ps_name']))

        for name_kr, champion_code in champion_codes.items():
            print(champion_code)
            response = re.get(f"https://z.fow.lol/champ/{champion_code}")
            print(response)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
                ps_name = name_mapping.get(name_kr)
                file_name = f"{self.image_path}/champion_icon/{ps_name}.jpg"
                image.save(file_name, 'JPEG', quality=95)
            else:
                print(f"로컬 파일 저장 에러: {name_kr} \n {response}")

    def find_champion_codes(self, html_content, champion_list):
        soup = BeautifulSoup(html_content, 'html.parser')
        champion_codes = {}
        champion_rows = soup.find_all('tr', class_='champ_filter_target')

        for row in champion_rows:
            champion_name = row.find('span').text
            if champion_name in champion_list:
                img_src = row.find('img')['src']
                champion_code = img_src.split('/')[-1]
                champion_codes[champion_name] = champion_code
        return champion_codes

    def player_photo(self, team):
        url = f"https://esports-api.lolesports.com/persisted/gw/getTeams?hl=ko-KR&id={team}"
        team_info = re.get(url, headers=self.lol_eSport_header).json()
        team_data = team_info['data']['teams'][0]
        team_name = team_data['name']
        team_image = team_data['image']

        team_icon_path = self.image_path / "team_icon"
        player_path = self.image_path / "player"

        team_filename = team_icon_path / f"{team_name}.jpg"
        response = re.get(team_image)
        if response.status_code == 200:
            with open(team_filename, 'wb') as f:
                f.write(response.content)
        for player in team_data['players']:
            summonerName = player['summonerName'].lower()
            player_image_url = player['image']
            if 'default-headshot' in player_image_url:
                continue
            player_filename = player_path / f"{summonerName}.jpg"
            try:
                response = re.get(player_image_url)
                if response.status_code == 200:
                    with open(player_filename, 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                print(f"이미지 저장 실패 ({summonerName}): {str(e)}")
        print("DONE")

    def opgg_champion_icon(self):
        url_list = self.get_opgg_icon_urls()
        save_dir = self.image_path / "champion_icon"
        for champion_name, url in url_list.items():
            response = re.get(url)
            if response.status_code != 200:
                print(f"챔피언 아이콘 opgg 다운 실패 {champion_name}: HTTP {response.status_code}")
                continue
            image_data = io.BytesIO(response.content)
            with Image.open(image_data) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                save_path = save_dir / f"{champion_name}.jpg"
                img.save(save_path, 'JPEG', quality=95)

    def get_opgg_icon_urls(self):
        response = re.get("https://www.op.gg/champions")
        html_content = response.content.decode('utf-8')
        processed_champions = set()
        results = {}
        pattern = r'href="(https://opgg-static\.akamaized\.net/meta/images/lol/[^"]+/champion/([^.]+)\.png[^"]*)"'
        matches = regex.finditer(pattern, html_content)
        for match in matches:
            url = match.group(1)
            champion = match.group(2).lower()
            if champion in processed_champions:
                continue
            processed_champions.add(champion)
            results[champion] = url
        return results


    def download_team_icons(self, url):
        response = re.get(url, headers=self.lol_eSport_header)
        data = response.json()
        output_dir = Path(__file__).parent.parent.parent / "Assets" / "Image" / "team_icon"
        teams = {}
        stages = data['data']['standings'][0]['stages']
        for stage in stages:
            for section in stage['sections']:
                if 'rankings' in section and section['rankings']:
                    for ranking in section['rankings']:
                        for team in ranking['teams']:
                            team_id = team['id']
                            if team_id not in teams:
                                teams[team_id] = {
                                    'name': team['name'],
                                    'code': team['code'],
                                    'image': team['image']
                                }
                if 'matches' in section:
                    for match in section['matches']:
                        for team in match['teams']:
                            team_id = team['id']
                            if team_id not in teams:
                                teams[team_id] = {
                                    'name': team['name'],
                                    'code': team['code'],
                                    'image': team['image']
                                }

        print(f"총 {len(teams)}개 팀 아이콘을 다운로드합니다.")

        downloaded_count = 0
        for team_id, team_info in teams.items():
            team_name = team_info['name']
            team_code = team_info['code']
            image_url = team_info['image']
            team_slug = team_info['slug']

            file_name = f"{team_name}.png"
            file_path = os.path.join(output_dir, file_name)

            try:
                if image_url.startswith('//'):
                    image_url = 'http:' + image_url

                response = re.get(image_url)
                response.raise_for_status()

                with open(file_path, 'wb') as img_file:
                    img_file.write(response.content)

                print(f"다운로드 완료: {team_name} ({team_code}) -> {file_path}")
                downloaded_count += 1
                sql_query = f"""
                            INSERT INTO esport_team_info (name, team_id, slug, code, image_url) 
                            VALUES ('{team_name.replace("'", "''")}', '{team_id}', '{team_slug}', '{team_code}', '{image_url}')
                            ON DUPLICATE KEY UPDATE 
                                name = '{team_name.replace("'", "''")}',
                                code = '{team_code}',
                                slug = '{team_slug}',
                                image_url = '{image_url}';
                            """
                self.database.fetch_one(sql_query)
                self.database.commit()
            except Exception as e:
                print(f"다운로드 실패: {team_name} - {e}")

        print(f"\n총 {downloaded_count}개 팀 아이콘 다운로드 완료.")


    def get_all_groups(self):


    # 1. 그룹 명 모두 가져오기
    # 2. db에 없으면 팀 명, 팀 아이콘 저장
    # 3. 팀원 이미지 수집
    def run(self):
        "https://esports-api.lolesports.com/persisted/gw/getStandings?hl=ko-KR&tournamentId=113684769985506946"

