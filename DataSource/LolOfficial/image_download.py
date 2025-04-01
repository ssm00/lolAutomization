from datetime import datetime
from urllib.parse import urlparse

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

    def download_player_image_by_team(self, team_official_slug):
        url = f"https://esports-api.lolesports.com/persisted/gw/getTeams?hl=ko-KR&id={team_official_slug}"
        team_info = re.get(url, headers=self.lol_eSport_header).json()
        team_data = team_info['data']['teams'][0]
        player_path = self.image_path / "player"
        for player in team_data['players']:
            summonerName = player['summonerName'].lower()
            player_image_url = player['image']
            if 'default-headshot' in player_image_url:
                continue
            player_filename = player_path / f"{summonerName}.png"
            if player_filename.exists():
                continue
            try:
                response = re.get(player_image_url)
                if response.status_code == 200:
                    with open(player_filename, 'wb') as f:
                        f.write(response.content)
                print(f"{team_official_slug} , {summonerName} 이미지 다운 완료")
            except Exception as e:
                print(f"플레이어 이미지 저장 실패 ({summonerName}): {str(e)}")

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

    def run_league(self):
        try:
            url = "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=ko-KR"
            get = re.get(url, headers=self.lol_eSport_header)
            league_info = get.json()
            leagues = league_info.get('data', {}).get('leagues', [])
            save_dir = os.path.join(self.image_path, "league_icon")
            self.download_league_icon(save_dir, leagues)
            self.database.save_league_info(save_dir, leagues)
        except Exception as e:
            print(f"리그 정보 처리 중 오류 발생: {str(e)}")

    def download_league_icon(self, save_dir, leagues):
        for league in leagues:
            league_slug = league.get('slug', '')
            league_image_url = league.get('image', '')
            if league_image_url:
                os.makedirs(save_dir, exist_ok=True)
                local_filename = f"{league_slug}.png"
                full_path = os.path.join(save_dir, local_filename)
                response = re.get(league_image_url, stream=True)
                response.raise_for_status()
                with open(full_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"리그 아이콘 다운로드 성공: {league_slug}")

    def download_team_image(self, image_url, team_slug):
        icon_dir = os.path.join(self.image_path, "team_icon")
        os.makedirs(icon_dir, exist_ok=True)
        local_filename = f"{team_slug}.png"
        full_path = os.path.join(icon_dir, local_filename)
        response = re.get(image_url, stream=True)
        response.raise_for_status()
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"팀 이미지 다운로드 성공: {team_slug}")
        return full_path

    # 팀 정보 업데이트, 사진 다운
    def run_team(self):
        league_info_list = self.database.get_league_id()
        for league_info in league_info_list:
            league_id = league_info.get('official_site_id')
            league_seq = league_info.get('seq')
            tournament_url = f"https://esports-api.lolesports.com/persisted/gw/getTournamentsForLeague?hl=ko-KR&leagueId={league_id}"
            response = re.get(tournament_url, headers=self.lol_eSport_header)
            json_data = response.json()
            leagues = json_data.get('data', {}).get('leagues', [])
            if not leagues:
                print(f"리그 ID {league_id}에 대한 정보가 없습니다.")
                continue
            tournaments = leagues[0].get('tournaments', [])
            if not tournaments:
                print(f"리그 ID {league_id}에 대한 토너먼트 정보가 없습니다.")
                continue
            latest_tournament = None
            latest_date = None
            for tournament in tournaments:
                start_date_str = tournament.get('startDate')
                if not start_date_str:
                    continue
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    if latest_date is None or start_date > latest_date:
                        latest_date = start_date
                        latest_tournament = tournament
                except ValueError:
                    print(f"날짜 형식 오류: {start_date_str}")
                    continue

            if latest_tournament:
                self.database.save_tournament_info(latest_tournament, league_seq)
                tournament_id = latest_tournament.get('id')
                standings_url = f"https://esports-api.lolesports.com/persisted/gw/getStandingsV3?hl=ko-KR&tournamentId={tournament_id}"
                standings_response = re.get(standings_url, headers=self.lol_eSport_header)
                json_data = standings_response.json()
                standings = json_data.get('data', {}).get('standings', [])

                if not standings or len(standings) == 0:
                    print("팀 순위 정보가 없습니다.")
                    continue

                tournament = standings[0]
                teams = []
                for stage in tournament.get('stages', []):
                    for section in stage.get('sections', []):
                        for ranking in section.get('rankings', []):
                            for team_data in ranking.get('teams', []):
                                teams.append(team_data)

                if not teams:
                    print(f"토너먼트 {tournament.get('slug', '알 수 없음')}에 대한 팀 정보가 없습니다.")
                    continue

                for team in teams:
                    image_url = team.get('image', '')
                    if image_url:
                        team_slug = team.get('slug', '')
                        local_image_path = self.download_team_image(image_url, team_slug)
                    self.database.save_team_info(team, local_image_path, league_seq)
                print(f"총 {len(teams)}개 팀 정보 처리 완료")

    def run_player(self):
        slug_list = self.database.get_team_slug()
        for slug_info in slug_list:
            team_slug = slug_info.get('official_site_slug')
            self.download_player_image_by_team(team_slug)


    # 1. 그룹 명 모두 가져오기
    # 2. db에 없으면 팀 명, 팀 아이콘 저장
    # 3. 팀원 이미지 수집
    def run_esport_data(self):
        self.run_league()
        self.run_team()
        self.run_player()
    
    # 챔피언 아이콘
    # 배경
    def run_champion_data(self):
        pass