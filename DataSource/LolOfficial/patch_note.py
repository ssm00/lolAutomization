import json
from pathlib import Path
import requests as re
import re as regex
from bs4 import BeautifulSoup

class PatchNote:

    def __init__(self, database, postgres):
        self.patch_note_list_url = "https://www.leagueoflegends.com/ko-kr/news/tags/patch-notes/"
        self.database = database
        self.postgres = postgres
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'Referer': 'https://www.google.com/'
        }

    def extract_patch_notes(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            data = json.loads(script.string)
            patch_notes = []
            items = data['props']['pageProps']['page']['blades'][2]['items']

            for item in items:
                version = self.extract_version(item['title'])  # 버전 추출
                if version:
                    patch_info = {
                        'version': version,
                        'title': item['title'],
                        'date': item['publishedAt'],
                        'url': 'https://www.leagueoflegends.com' + item['action']['payload']['url'],
                        'description': item['description']['body']
                    }
                    patch_notes.append(patch_info)
            return patch_notes
        return []

    def extract_version(self, title):
        patterns = [
            r'(\d+\.(?:\d+\.?)+)',
        ]
        for pattern in patterns:
            match = regex.search(pattern, title)
            if match:
                version = match.group(1)
                parts = version.split('.')
                if len(parts) >= 2:
                    major = parts[0]
                    minor = parts[1].zfill(2)
                    if minor.startswith('S'):
                        minor = minor[1:].zfill(2)
                    return f"{major}.{minor}"
        return None

    def update_patch_list(self):
        response = re.get(self.patch_note_list_url, headers=self.header)
        patch_notes = self.extract_patch_notes(response.content)
        for info in patch_notes:
            self.database.update_patch_info(info)

    def update_patch_note(self):
        url_list = self.database.get_patch_url_list()
        get_one = url_list[0]
        url = get_one['url']
        html = re.get(url, headers=self.header)
        soup = BeautifulSoup(html.text, 'html.parser')
        text = soup.find("div", {"data-testid": "rich-text"}).get_text()
        print(text)