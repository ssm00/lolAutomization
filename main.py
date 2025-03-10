from Db.mysql_db import Database
from MyMetaData.metadata import MetaData
from DataSource.oracle_elixir.oracle_elixir_downloader import OracleElixirDownloader
from DataSource.Lolps.champion_score import ChampionScore
from DataSource.LolOfficial.image_download import ImageDownload
from AnomalyDetection.champion_detection import ChampionDetection
from ImageModifier.pickrate import PickRate
from Ai.LangChain.article_generator import ArticleGenerator
import logging
from Db.mongo_db import MongoDB
from ImageModifier.match_result import MatchResult
from ImageModifier.interview import Interview



class Main:

    def __init__(self, database, mongo, meta_data, logger):
        self.database = database,
        self.mongo = mongo,
        self.meta_data = meta_data,
        self.logger = logger,
        self.oracle_elixirs_downloader = OracleElixirDownloader(database)
        self.champion_score = ChampionScore(database)
        self.detection = ChampionDetection(database, meta_data)
        self.image_download = ImageDownload(database)
        self.article_generator = ArticleGenerator(database, mongo, meta_data)
        self.match_result = MatchResult(database, meta_data)
        self.interview = Interview(database, mongo, meta_data, self.article_generator)
        self.pick_rate = PickRate(database, meta_data, self.article_generator)
    
    # 1. oracle_elixirs 업데이트
    # 2. 패치 버전 업데이트 확인
    # 3. ps 챔피언 티어 업데이트
    # 4. 이상치 탐색 글 작성
    # 5. slack 전송
    def daily_work(self):
        self.oracle_elixirs_downloader.update_oracle_elixirs()
        self.champion_score.update_score()
        pentakill_list = self.detection.run_penta_kill()
        self.match_result.run(pentakill_list)

    def run_pick_rate(self):
        self.pick_rate.fifth_page("LOLTMNT01_204281","GIDEON")

    def run_match_result(self):
        self.match_result.run("LOLTMNT01_204281", "GIDEON", "type")


if __name__ == "__main__":
    logger = logging.getLogger("mylogger")
    meta_data = MetaData()
    database = Database(meta_data.db_info["mysql_local"], meta_data, logger=logger)
    mongo = MongoDB(meta_data.db_info["mongo_local"])
    main = Main(database, mongo, meta_data, logger)
    #main.run_pick_rate()
    main.run_match_result()
    #main.daily_work()

# detection.run_pick_rate()
# detection.run_unmatch_line()
# detection.run_two_bottom_choice()
#detection.run_penta_kill()

#detection.run_pick_rate()
#detection.run_unmatch_line()
#detection.run_performance_score()
#detection.run_match_info()
#detection.draw_all_series("LOLTMNT02_192520","Sylvie")
#detection.draw_combined_series("LOLTMNT02_192520","Sylvie")
#detection.get_game_mvp("LOLTMNT03_138902")


#interview.summary_interview("../input.mp4")
#interview.title_page("input.mp4")
#interview.main_page("input.mp4")
#match_result.title_page("LOLTMNT01_204281","GIDEON")
#match_result.main_page("LOLTMNT01_204281","GIDEON")
#pickrate = PickRate(database, meta_data, article_generator)
#pickrate.first_page("LOLTMNT01_204281","GIDEON")
#pickrate.second_page("LOLTMNT01_204281","GIDEON")
#pickrate.third_page("LOLTMNT01_204281","GIDEON")
#pickrate.fourth_page("LOLTMNT01_204281","GIDEON")
#pickrate.fifth_page("LOLTMNT01_204281","GIDEON")
#pickrate.run_all_page("LOLTMNT03_185067","Oner")
#pickrate.create_champion_comparison()
#pickrate.convert_png()
# note = PatchNote(database, postgres)
# note.update_patch_note()
