import json
import requests as re
from bs4 import BeautifulSoup
import cloudscraper

class ChampionScore:

    def __init__(self, database):
        #협곡, 칼바람
        self.database = database
        self.main_page_url = "https://lol.ps/statistics"
        self.score_url = "https://lol.ps/api/statistics/tierlist.json?region=0&version={}&tier={}&lane={}"
        self.howling_abyss_score_url = "https://lol.ps/api/champ/897/graphs.json?region=0&version={}&tier={}&lane={}&range=two_weeks"
        #
        self.tier_num = {"master":"3", "diamond":"13", "emerald":"2", "under_emerald":"1"}
        self.line_num = {"top":"0", "jungle":"1", "mid":"2", "bottom":"3", "support":"4", "all":"-1"}
        self.howling_abyss_line_num = {"top":"0", "jungle":"1", "mid":"2", "bottom":"3", "support":"4", "all":"5"}
        self.headers = {
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
        self.main_headers = {
            'Cookie': '_ga=GA1.1.871779289.1730685550; _sharedid=2cd18c6d-95ad-41e5-8476-492fd1170541; *sharedid*cst=zix7LPQsHA%3D%3D; *au*1d=AU1D-0100-001730685551-46CLIKS7-NH3U; *cc*id=8e87e7827e41db064326628767616155; __gads=ID=609556a6ff4a288b:T=1730685568:RT=1730685568:S=ALNI_Mb34NIMRWU-BCBwxvograh464xg3g; __eoi=ID=588b544ab5cfc9f3:T=1730685568:RT=1730685568:S=AA-AfjZLB-4ZrB5ToKSD12hetxJz; *lr*env_src_ats=false; Refresh=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJkYzM3NDkyYy01MzQ4LTRjMWMtODk4MS0xMTllOGM4NDA2MDgiLCJpYXQiOjE3MzMyMDc5NzgsImV4cCI6MTczNTc5OTk3OH0.zcFITf44opvg_3C0ohsO-k93AhGNruoGlUU3MElPDpU; __cf_bm=wHCbZd6poZq.piuoQqAV73fNjWX352FggShAiR8FBck-1735551449-1.0.1.1-OwC.N7ENj9dCuLuB5J9Ot6Xwx6rjKWtw2Gt6dPATUYJ3DpfK.YbqCFVHCuVUhf_6zImxlUbCtRyHOCpuvN6RJw; Authentication=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuaWNrTmFtZSI6IuydtOy8gOyLnOyVhCDstpzsi6Ag65Oc66CI7J2067iQIiwidXNlcm5hbWUiOiJwYmtkZjJfc2hhMjU2JDIxNjAwMCRkdzBjbnJCd1A1emokM3RFcHhkV2IrR20zckk1QWFxcGR2NHJ3V0x0aThKUjQ1QnJSMWNzY0x6VT0iLCJ1c2VySWQiOiJkYzM3NDkyYy01MzQ4LTRjMWMtODk4MS0xMTllOGM4NDA2MDgiLCJpc0FkbWluIjpmYWxzZSwiaXNQYXJ0bmVyIjpmYWxzZSwidmFsaWRhdGVkQnkiOiJtYWlsIiwiaW1nIjoibWVkaWEvcXVlc3QvaW1hZ2UvMjAyMC8wNS8yOS_hhIjhhaHhhq_hhIDhhaHhhqtf4YSG4YWh4Ya84YSQ4YWpX-GEi-GFouGEguGFtTMwMF9ncmF5LmpwZyIsInBvaW50IjowLCJpc0FjdGl2ZSI6dHJ1ZSwiaXNWZXJpZmllZCI6dHJ1ZSwibWVtYmVyVXNlciI6eyJ1c2VybmFtZSI6InRpdGFuMDcyNGV4MkBnbWFpbC5jb20iLCJ1c2VySWQiOiJkYzM3NDkyYy01MzQ4LTRjMWMtODk4MS0xMTllOGM4NDA2MDgiLCJpc0FkbWluIjpmYWxzZSwiaXNQYXJ0bmVyIjpmYWxzZSwiaXNWaXAiOmZhbHNlLCJwbGFuSWQiOjAsInZpcEV4cGlyZURhdGUiOm51bGwsInZhbGlkYXRlZEJ5IjoiZ29vZ2xlIiwiaXNBY3RpdmUiOnRydWUsImlzVmVyaWZpZWQiOnRydWUsInB1dWlkIjpudWxsfSwibGlnaHRNb2RlIjpmYWxzZSwiaWF0IjoxNzM1NTUxNTk0LCJleHAiOjE3MzU1NTI3OTR9.-b0w2ZqQ7wB0fF2kWfdoWqQoK-2rZGkVxDGTx3khVIg; ExpiredAt=1735552794727; cf_clearance=obhdplA7UAyyNc0pj8plyFPms8GSQ9WqQDAM8BK1W90-1735551595-1.2.1.1-TRRlib43R8TIhG5avzRVaPtQvBDMeDYRVTAFObjxkDcEfZvwiGPnuYikeyPDjoc9JQBovM8GhErtyPtD8vea4IcZR6Dg5r2eVvji8CZ5TmiU8eTbdavmVTJfDWjUpJWNWH44LfIY7Gl2YDrp_Bp_oAvKgtXo5sR97FgVH0_muXCQO9IsqIGc2gtc2wOWqY7Xe2okIec2CtvMSqAGFl07n0vaMbQj_fxc7twUpilmRZi81v_jhQJGVVocljASubQ0.KWnpRPzw3Y7pu8jPqygKQVZiwS21s6qudco0RKKjxYKOIJkcSV9iA3EdKKMkX7UGDDc6_m9SoWX0D_v6nX3orzatNgLGQt_Mlhnf.7S6PF3f4jIKMvjrKJF3CUC_eFiIB8dcLgE9XMps7NiOa0SWA; *ga*9QN8SSPG32=GS1.1.1735551594.9.1.1735551595.0.0.0; *lr*retry_request=true; cto_bundle=0RQFLl9PMElQT2RxSDY0eXBqaVpGJTJCeGdSZFhHV2ZuSkpOaXQwcDNVa0glMkZEcyUyRlNyaE5ydTVhOXcyeG5UWm1Ra3hmVGVpVGtvV0gwVFBta1kwUFhWWGhZVDVmbFVmT0dzdnlLWVUzdzNPamlld3BlVDhGOUM1JTJGTjd6djBSMERIRmpzUmhuckVFdVZKWFNmTXQ5eHVWQWZJNzROa1lVdnZ5RWt5OE4xVnNjJTJCUkNpa1Y0SFRHcGhZNVBxQjhBU0tuWHhtM2ZBOXlVYm1YVjVzNCUyRjNGWFBLVzdZZXJ4NTViV2NrQlBibWJRUHBBNjZsRGpyUmt6MGI5R0UwcUVxR2h2Y2Y1UkJk; cto_bidid=DBuJu19UVlA5SU1MWHFIWHhiRnZSd2JWQ002ZUFPd2JzRFhBTmlwQlZzRFdtZURoSndJd3k4N3JuU3JGYUJvSjNaRE9wQlRHMmk3b0RwdlVyTXg0TTJVUjJWU2FaYnFWZFlxbFNiZkxKdk96ZFJERSUzRA; FCNEC=%5B%5B%22AKsRol9ncgS-ydDR54DKDJNE9RGxzyOrvA2QNzhmysWcw-vNT7IbTShflqpF6Sjzg0bTD3yx0MpX3pdGmtu2Pn92F8-pOMYGUmSTl6L_-58NJiLYOddg4i8DpkowuTayUhsWrbp3RfKKed0VzhgHC1VA2eMgmKep1g%3D%3D%22%5D%5D',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

    def update_score(self):
        try:
            for line_str, line_num in self.line_num.items():
                url = self.score_url.format(112, 3, line_num)
                get_score = re.get(url, headers=self.headers)
                score_info = get_score.json()
                self.database.insert_champion_score(line_str, 14.24, "master", "korea", score_info.get('data'))
        except re.exceptions.JSONDecodeError:
            print(f"PS 챔피언 스코어 가져오기 JSON 인코딩 에러 URL : {url} \n text : {get_score}")


