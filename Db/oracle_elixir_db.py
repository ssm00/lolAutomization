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
                o.name_us,
                o.playername,
                o.teamname,
                o.patch,
                p.performance_score,
                p.win_rate,
                p.pick_rate,
                p.is_outlier
            FROM oracle_elixir o
            JOIN performance_score p 
                ON o.name_us = p.name_us
                AND o.patch = p.patch
                AND o.position = p.line
            WHERE (o.position, o.name_us) IN (
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

    def get_player_info(self, patch):
        select_query = f"""
        SELECT *
        FROM oracle_elixir 
        WHERE position != 'team'
        AND patch = {patch}
        ORDER BY gameid, side
        """
        match_info = pd.read_sql(select_query, self.connection)
        return match_info

    def get_team_info(self):
        select_query = """
        select * 
        from oracle_elixir
        where position = "team"
        order by gameid, game_date
        """
        return pd.read_sql(select_query, self.connection)

    def get_pick_rate_info(self, patch):
        position_champions = {}
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        for position in positions:
            select_query = f"""
            select name_us, name_kr, pick_rate
            from champion_score_{position}
            where patch = {patch}
            """
            df = pd.read_sql(select_query, self.connection)
            thresh_hold = np.percentile(df['pick_rate'], 10)
            champions_dict = {row['name_us']: {
                'pick_rate': row['pick_rate'],
                'name_kr': row['name_kr']
            } for _, row in df.iterrows()}
            position_champions[position] = {
                'name_us_list': champions_dict,
                'low_pickrate_threshold': thresh_hold,
                'low_pickrate_champions': df[df['pick_rate'] <= thresh_hold]['name_us'].tolist()
            }
        return position_champions

    def get_only_bottom_champion(self, patch):
        select_query = f"""
        select name_us
        from champion_score_bottom cb
        where patch = {patch}
        and cb.name_us not in (select name_us from champion_score_mid)
        """
        return pd.read_sql(select_query, self.connection)['name_us'].tolist()

    def get_match_series_info(self, game_id, player_name):
        select_query = f"""
        select
            name_us,
            goldat10,
            xpat10,
            csat10,
            opp_goldat10,
            opp_xpat10,
            opp_csat10,
            golddiffat10,
            xpdiffat10,
            csdiffat10,
            killsat10,
            assistsat10,
            deathsat10,
            opp_killsat10,
            opp_assistsat10,
            opp_deathsat10,
            goldat15,
            xpat15,
            csat15,
            opp_goldat15,
            opp_xpat15,
            opp_csat15,
            golddiffat15,
            xpdiffat15,
            csdiffat15,
            killsat15,
            assistsat15,
            deathsat15,
            opp_killsat15,
            opp_assistsat15,
            opp_deathsat15,
            goldat20,
            xpat20,
            csat20,
            opp_goldat20,
            opp_xpat20,
            opp_csat20,
            golddiffat20,
            xpdiffat20,
            csdiffat20,
            killsat20,
            assistsat20,
            deathsat20,
            opp_killsat20,
            opp_assistsat20,
            opp_deathsat20,
            goldat25,
            xpat25,
            csat25,
            opp_goldat25,
            opp_xpat25,
            opp_csat25,
            golddiffat25,
            xpdiffat25,
            csdiffat25,
            killsat25,
            assistsat25,
            deathsat25,
            opp_killsat25,
            opp_assistsat25,
            opp_deathsat25
        from oracle_elixir 
        where gameid = %s and playername = %s
        """
        return pd.read_sql(select_query, self.connection, params=(game_id, player_name))

    def get_oppnent_player_name(self, game_id, player_name):
        select_query = """
        select name_us, playername 
        from oracle_elixir oe
        where gameid = (%s) 
        and position = (select position as p from oracle_elixir where gameid = (%s) and playername = (%s))
        and playername != (%s) 
        """
        return self.fetch_one(select_query, args=(game_id, game_id, player_name, player_name))

    def get_game_data(self, game_id):
        query = """
                    SELECT 
                        gameid, position, playername, name_us as champion,
                        kills, deaths, assists, teamkills, firstbloodkill, firstbloodassist,
                        cspm, damageshare, earnedgoldshare, goldspent, earnedgold,
                        vspm, wcpm, wpm, gamelength,
                        firsttower, firstdragon, firstherald, firstbaron,
                        towers, opp_towers, dragons, barons, heralds, opp_dragons,
                        damagetochampions, dpm, damagetakenperminute, damagemitigatedperminute,
                        monsterkillsenemyjungle, visionscore, gspd,
                        golddiffat15, xpdiffat15, csdiffat15,
                        result
                    FROM oracle_elixir 
                    WHERE gameid = %s 
                    """
        return pd.read_sql(query, self.connection, params=(game_id,))

    def get_official_image_name(self):
        query = "select lol_official_image_name from champion_info"
        return pd.read_sql(query, self.connection)

