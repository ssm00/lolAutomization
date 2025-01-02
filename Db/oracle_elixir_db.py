import os
import sys

import numpy as np
import pymysql
import pandas as pd
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))


class Database:
    def __init__(self, db_info, logger):
        self.db_info = db_info
        self.logger = logger
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=self.db_info['host'],
                user=self.db_info['id'],
                password=self.db_info['password'],
                db=self.db_info['db'],
                charset='utf8mb4',
            )
            self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)
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
        self.connection.commit()

    def close(self):
        self.connection.close()

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

    def get_champion_score(self, line, patch):
        table = f"champion_score_{line}"
        select_query = f"""
            select * from {table} where patch = {patch};"""
        return pd.read_sql(select_query, self.connection)

    def insert_performance_score(self, line, df):
        table = f"performance_score"
        df = df.replace({np.nan: None})
        for _,row in df.iterrows():
            insert_query = f"""
            insert into {table} (name_us, name_kr, pick_rate, win_rate, ban_rate, champion_tier, patch, line, performance_score, anomaly_score, is_outlier)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on duplicate key update
                name_us = values(name_us),
                name_kr = values(name_kr),
                pick_rate = values(pick_rate),
                win_rate = values(win_rate),
                ban_rate = values(ban_rate),
                champion_tier = values(champion_tier),
                patch = values(patch),
                line = values(line),
                performance_score = values(performance_score),
                anomaly_score = values(anomaly_score),
                is_outlier = values(is_outlier)"""
            values = [
                row['name_us'],
                row['name_kr'],
                row['pick_rate'],
                row['win_rate'],
                row['ban_rate'],
                row['champion_tier'],
                row['patch'],
                line,
                row['performance_score'],
                row['anomaly_score'],
                row['is_outlier']
            ]
            self.cursor.execute(insert_query, values)
        self.commit()

    def detect_by_performance_score(self, patch):
        select_query = f"""
            WITH outlier_champs AS (
                SELECT name_us, line, patch
                FROM performance_score
                WHERE is_outlier = true 
                AND patch = {patch}
            )
            SELECT 
                o.gameid,
                o.position,
                o.champion,
                o.playername,
                o.teamname,
                o.patch,
                p.performance_score,
                p.win_rate,
                p.pick_rate,
                p.is_outlier
            FROM oracle_elixir o
            JOIN performance_score p 
                ON o.champion = p.name_us
                AND o.patch = p.patch
                AND o.position = p.line
            WHERE (o.position, o.champion) IN (
                SELECT line, name_us 
                FROM outlier_champs
            )
            AND o.position != 'team'
            AND o.patch = {patch}
            ORDER BY o.position, o.gameid;
            """
        return pd.read_sql(select_query, self.connection)

    def get_latest_patch(self):
        select_query = "select max(patch) from oracle_elixir"
        return self.fetch_one(select_query)

    def get_champion_name_by_line(self, patch):
        position_champions = {}
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        for position in positions:
            query = f"SELECT name_us FROM champion_score_{position} where patch = {patch}"
            position_champions[position] = pd.read_sql(query, self.connection)['name_us'].tolist()
        return position_champions

    def get_match_info(self, patch):
        select_query = f"""
        SELECT gameid, position, playername, champion, teamname
        FROM oracle_elixir 
        WHERE position != 'team'
        AND patch = {patch}
        """
        match_info = pd.read_sql(select_query, self.connection)
        return match_info

    def get_pick_rate_info(self, patch):
        position_champions = {}
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        for position in positions:
            select_query = f"""
            select name_us, pick_rate
            from champion_score_{position}
            where patch = {patch}
            """
            df = pd.read_sql(select_query, self.connection)
            thresh_hold = np.percentile(df['pick_rate'], 10)
            position_champions[position] = {
                'champions': df['name_us'].tolist(),
                'low_pickrate_threshold': thresh_hold,
                'low_pickrate_champions': df[df['pick_rate'] <= thresh_hold]['name_us'].tolist()
            }
        return position_champions


