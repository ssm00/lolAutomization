import datetime
import traceback

from Db.mysql_db import Database
from MyMetaData.metadata import MetaData
from DataSource.oracle_elixir.oracle_elixir_downloader import OracleElixirDownloader
from DataSource.Lolps.champion_score import ChampionScore
from DataSource.Lolps.champion_info_update import ChampionInfo
from DataSource.LolOfficial.image_download import ImageDownload
from AnomalyDetection.champion_detection import ChampionDetection
from ImageModifier.pickrate import PickRate
from Ai.LangChain.article_generator import ArticleGenerator
import logging
from Db.mongo_db import MongoDB
from ImageModifier.match_result import MatchResult
from ImageModifier.interview import Interview
from DataSource.youtube.lck_official import LCKOfficial
from Aws.s3 import S3Manager
from Slack.SlackClient import SlackClient
from Instagram.instagram_uploader import InstagramUploader
from MyMetaData.patch_version import Patch

class Main:

    def __init__(self, database, mongo, meta_data, logger):
        self.database = database
        self.mongo = mongo
        self.meta_data = meta_data
        self.logger = logger
        self.patch = Patch(database, meta_data)
        self.oracle_elixirs_downloader = OracleElixirDownloader(database)
        self.champion_score = ChampionScore(database)
        self.detection = ChampionDetection(database, meta_data, self.patch)
        self.image_download = ImageDownload(database)
        self.article_generator = ArticleGenerator(database, mongo, meta_data, self.patch)
        self.match_result = MatchResult(database, meta_data, self.article_generator)
        self.interview = Interview(database, mongo, meta_data, self.article_generator)
        self.pick_rate = PickRate(database, meta_data, self.article_generator, self.patch)
        self.you_tube = LCKOfficial(meta_data, mongo)
        self.s3_manager = S3Manager()
        self.slack_client = SlackClient(database, meta_data.account_info, self.s3_manager, logger)
        self.instagram_uploader = InstagramUploader(meta_data.account_info, logger)
        self.champion_info_downloader = ChampionInfo(database)


    # 1. oracle_elixirs 업데이트
    # 2. 패치 버전 업데이트 확인
    # 3. ps 챔피언 티어 업데이트
    # 4. 이상치 탐색 글 작성
    # 5. 유튜브 영상 다운로드
    # 6. 인터뷰 글 작성
    # 7. slack 전송
    def daily_work(self):
        self.patch.set_patch_version()
        self.oracle_elixirs_downloader.update_oracle_elixirs()
        self.database.update_patch_url_number()
        self.champion_score.update_score()
        self.run_pick_rate()
        self.run_match_result()
        self.you_tube.download_videos_by_date()
        self.interview.run()
        self.s3_manager.upload_today_folders()
        self.show_all_image()

    # 리그 정보 업데이트
    # 팀 정보 업데이트, 팀 아이콘 다운
    # 선수는 너무 많아서 스킵
    def weekly_work(self):
        self.image_download.run_league()
        self.image_download.run_team()
        self.database.match_team_name()
        self.champion_info_downloader.update_champion_info()

    def run_pick_rate(self):
        pick_rate_list = self.detection.run_pick_rate()
        print(f"픽률 탐지 개수 : {len(pick_rate_list)}")
        for pick_rate_info in pick_rate_list:
            self.pick_rate.run(pick_rate_info['gameid'], pick_rate_info['playername'])

    # detection_type -> general, penta_kill, unmatch_line, two_bottom_choice
    def run_match_result(self):
        unmatch_line_list = self.detection.run_unmatch_line()
        print(f"unmatch_line_list 탐지 개수 : {len(unmatch_line_list)}")
        for unmatch_line in unmatch_line_list:
            self.match_result.run(unmatch_line['gameid'], unmatch_line['playername'], "unmatch_line")
        two_bottom_choice_list = self.detection.run_two_bottom_choice()
        print(f"two_bottom_choice_list 탐지 개수 : {len(two_bottom_choice_list)}")
        for two_bottom_choice in two_bottom_choice_list:
            self.match_result.run(two_bottom_choice['gameid'], two_bottom_choice['playername'], "two_bottom_choice")
        penta_kill_list = self.detection.run_penta_kill()
        print(f"penta_kill_list 탐지 개수 : {len(penta_kill_list)}")
        for penta_kill in penta_kill_list:
            self.match_result.run(penta_kill['gameid'], penta_kill['playername'], "penta_kill")

    def run_player_image(self):
        self.image_download.run_player()

    def run_interview(self):
        self.interview.run()

    def show_all_image(self):
        try:
            image_list = self.s3_manager.get_all_today_image()
            self.slack_client.show_image_list(image_list)
            self.logger.info("slack 이미지 전송 완료")
        except Exception as e:
            print(f"slack 이미지 전송 실패 메시지 {e}")

    def test_pick_rate(self):
        pick_rate_list = self.detection.run_pick_rate("test")
        for pick_rate in pick_rate_list:
            self.pick_rate.run(pick_rate['gameid'], pick_rate['playername'])

    def test_interview(self):
        self.interview.test_run()

    def test_1(self):
        self.champion_info_downloader.update_champion_info()

    # match_result detection_type -> general, penta_kill, unmatch_line, two_bottom_choice
    def test_match_result(self):
        unmatch_line_list = self.detection.run_unmatch_line("test")
        for unmatch_line in unmatch_line_list:
            self.match_result.run(unmatch_line['gameid'], unmatch_line['playername'], "unmatch_line")
        two_bottom_choice_list = self.detection.run_two_bottom_choice("test")
        for two_bottom_choice in two_bottom_choice_list:
            self.match_result.run(two_bottom_choice['gameid'], two_bottom_choice['playername'], "two_bottom_choice")
        penta_kill_list = self.detection.run_penta_kill("test")
        for penta_kill in penta_kill_list:
            self.match_result.run(penta_kill['gameid'],penta_kill['playername'],"penta_kill")


if __name__ == "__main__":
    logger = logging.getLogger("mylogger")
    meta_data = MetaData()
    database = Database(meta_data.db_info["mysql"], meta_data, logger=logger)
    mongo = MongoDB(meta_data.db_info["mongo_atlas"])
    main = Main(database, mongo, meta_data, logger)
    main.daily_work()
