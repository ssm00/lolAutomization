import os
import sys
import pymysql
import pandas as pd
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))


class Database:
    def __init__(self, db_info, logger):
        self.db_info = db_info
        self.logger = logger
        self.db = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.db = pymysql.connect(
                host=self.db_info['host'],
                user=self.db_info['id'],
                password=self.db_info['password'],
                db=self.db_info['db'],
                charset='utf8mb4',
            )
            self.cursor = self.db.cursor(pymysql.cursors.DictCursor)
            self.logger.info("데이터베이스 연결 성공")
        except Exception as e:
            self.logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    def fetch_all(self, query, args=None):
        self.cursor.execute(query, args)
        return self.cursor.fetchall()

    def fetch_one(self, query, args=None):
        self.cursor.execute(query, args)
        return self.cursor.fetchone()

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()

    def process_value(self, value):
        if pd.isna(value):
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, str) and value.strip() == '':
            return None
        return value

    def insert_oracle_elixir(self, df):
        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_query = f"""
                            INSERT INTO oracle_elixir ({columns})
                            VALUES ({placeholders})
                        """
        for index, row in df.iterrows():
            try:
                values = [self.process_value(val) for val in row]
                self.cursor.execute(insert_query, values)
                if (index + 1) % 1000 == 0:
                    self.commit()
                    print(f"Processed {index + 1} rows...")
            except pymysql.Error as e:
                    print(f"Error inserting row {index + 1}: {e}")
                    print(f"Problematic row data: {row}")
                    continue
        self.commit()

    def insert_champion_score(self, line, patch, survey_target_tier, region, data_list):
        try:
            table = f"champion_score_{line}"
            for data in data_list:
                insert_query = f"""
                    INSERT INTO {table} (
                        name_us,
                        name_kr,
                        champion_tier,
                        ranking,
                        ranking_variation,
                        is_op,
                        ps_score,
                        honey_score,
                        win_rate,
                        pick_rate,
                        ban_rate,
                        sample_size,
                        patch,
                        survey_target_tier,
                        region,
                        updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE 
                        name_us = VALUES(name_us),
                        name_kr = VALUES(name_kr),
                        champion_tier = VALUES(champion_tier),
                        ranking = VALUES(ranking),
                        ranking_variation = VALUES(ranking_variation),
                        is_op = VALUES(is_op),
                        ps_score = VALUES(ps_score),
                        honey_score = VALUES(honey_score),
                        win_rate = VALUES(win_rate),
                        pick_rate = VALUES(pick_rate),
                        ban_rate = VALUES(ban_rate),
                        sample_size = VALUES(sample_size),
                        patch = VALUES(patch),
                        survey_target_tier = VALUES(survey_target_tier),
                        region = VALUES(region),
                        updated_at = VALUES(updated_at)
                """
                updated_at = datetime.strptime(data.get("updatedAt"), "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
                values = [
                    data.get("championInfo").get("nameUs"),
                    data.get("championInfo").get("nameKr"),
                    data.get("opTier"),
                    data.get("ranking"),
                    data.get("rankingVariation"),
                    data.get("isOp"),
                    data.get("opScore"),
                    data.get("honeyScore"),
                    data.get("winRate"),
                    data.get("pickRate"),
                    data.get("banRate"),
                    data.get("count"),
                    patch,
                    survey_target_tier,
                    region,
                    updated_at
                    ]
                self.cursor.execute(insert_query, values)
            self.commit()
        except Exception as e:
            print(f"{insert_query} \n {values} \n {e}")
