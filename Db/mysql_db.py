import os
import sys
import re as regex
import numpy as np
import pymysql
import pandas as pd
from datetime import datetime, date
from fuzzywuzzy import fuzz
from util.commonException import CommonError,ErrorCode
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))

class Database:
    def __init__(self, db_info, meta_data, logger):
        self.db_info = db_info
        self.logger = logger
        self.connection = None
        self.cursor = None
        self.connect()
        self.year = meta_data.basic_info.get("year")

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
                            INSERT IGNORE INTO oracle_elixir_{self.year} ({columns})
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

    def get_last_date_from_db(self):
        query = f"SELECT MAX(game_date) FROM oracle_elixir_{self.year}"
        result = self.fetch_one(query)['MAX(game_date)']
        if result is None:
            return pd.to_datetime(f'{self.year}-01-01')
        return result

    def get_latest_patch_and_url_number(self):
        query = """
        SELECT patch_version, url_number 
        FROM patch_version_mapping
        ORDER BY patch_version DESC
        LIMIT 1
        """
        result = self.fetch_one(query)
        if result:
            return {"patch_version": result['patch_version'], "url_number": result['url_number']}
        return None

    def get_url_number(self, patch_version):
        query = "SELECT url_number FROM patch_version_mapping WHERE patch_version = %s"
        self.cursor.execute(query, patch_version)
        result = self.cursor.fetchone()
        if result:
            return result['url_number']
        return None

    # 공식 사이트 패치 정보 데이터 소스 url 업데이트
    def update_patch_url_number(self):
        latest_patch_version = self.get_latest_patch_oracle_elixirs()
        #이미 최신이라 업데이트 안해도 되면 그냥 반환
        url_number = self.get_url_number(latest_patch_version)
        if url_number is not None:
            return
        latest = self.get_latest_patch_and_url_number()
        new_url_number = latest["url_number"] + 1
        insert_query = """
        INSERT INTO patch_version_mapping (patch_version, url_number)
        VALUES (%s, %s)
        """
        self.cursor.execute(insert_query, (latest_patch_version, new_url_number))
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
                        updated_at,
                        position)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                        updated_at = VALUES(updated_at),
                        position = VALUES(position)
                """
                line_id = {0:"top",1:"jungle",2:"mid",3:"bottom",4:"support"}
                if line == "all":
                    line = line_id[data.get("laneId")]
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
                    updated_at,
                    line
                    ]
                self.cursor.execute(insert_query, values)
            self.commit()
        except Exception as e:
            print(f"{insert_query} \n {values} \n {e}")

    def get_champion_score_by_line(self, line, patch):
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
            FROM oracle_elixir_{self.year} o
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

    def get_latest_patch_oracle_elixirs(self):
        select_query = f"select max(patch) from oracle_elixir_{self.year}"
        return self.fetch_one(select_query)['max(patch)']

    def get_all_champion_list(self, patch):
        position_champions = {}
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        for position in positions:
            query = f"SELECT name_us FROM champion_score_{position} where patch = {patch}"
            position_champions[position] = pd.read_sql(query, self.connection)['name_us'].tolist()
        return position_champions

    def get_all_data_without_team(self, patch, game_date=None):
        select_query = f"""
        SELECT *
        FROM oracle_elixir_{self.year} 
        WHERE position != 'team'
        AND result = 1
        """
        if game_date is None:
            select_query += " AND DATE(game_date) = (CURDATE() - 1)"
        select_query += "ORDER BY gameid, side"
        match_info = pd.read_sql(select_query, self.connection)
        return match_info

    def get_oracle_elixirs_all_team_info(self):
        select_query = f"""
        select * 
        from oracle_elixir_{self.year}
        where position = "team"
        order by gameid, game_date
        """
        return pd.read_sql(select_query, self.connection)

    def get_all_position_pick_rate(self, patch):
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

    def get_penta_kill_game_id(self, patch, game_date=None):
        select_query = f"""select playername, gameid from oracle_elixir_{self.year} where pentakills >= 1 and patch = %s and playername is not null"""
        penta_kill_list = self.fetch_all(select_query, patch)
        if game_date is None:
            select_query += " AND DATE(game_date) = CURDATE()"
        return penta_kill_list

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
        from oracle_elixir_{self.year} 
        where gameid = %s and playername = %s
        """
        return pd.read_sql(select_query, self.connection, params=(game_id, player_name))

    def get_oppnent_player_name(self, game_id, player_name):
        select_query = f"""
        select name_us, playername 
        from oracle_elixir_{self.year} oe
        where gameid = (%s) 
        and position = (select position as p from oracle_elixir_{self.year} where gameid = (%s) and playername = (%s))
        and playername != (%s) 
        """
        return self.fetch_one(select_query, args=(game_id, game_id, player_name, player_name))

    def get_mvp_base_data(self, game_id):
        query = f"""
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
                    FROM oracle_elixir_{self.year} 
                    WHERE gameid = %s 
                    """
        return pd.read_sql(query, self.connection, params=(game_id,))

    def get_champion_name(self):
        query = "select * from champion_info"
        return pd.read_sql(query, self.connection)

    def get_game_data(self, game_id):
        select_query = f"select * from oracle_elixir_{self.year} where gameid = %s"
        return pd.read_sql(select_query, self.connection, params=game_id)

    def get_name_kr(self, name_us):
        select_query = "select name_kr from champion_info where ps_name = (%s)"
        return self.fetch_one(select_query, args=name_us)['name_kr']

    def get_name_kr_list(self):
        select_query = "select name_kr from champion_info"
        res = [record.get('name_kr') for record in self.fetch_all(select_query)]
        return res

    def get_champion_rate_table(self, name_us, patch, position):
        # unmatch_line일때 체크
        check_query = self.fetch_one(f"select * from champion_score_{position} where name_us = %s and patch = %s",args=(name_us, patch))
        if check_query is None:
            position = "all"
        select_query = f"select name_us, pick_rate, win_rate, ban_rate, champion_tier,position from champion_score_{position} where name_us = (%s) and patch = (%s) "
        result = self.fetch_one(select_query, args=(name_us, patch))
        # 모든 라인에서 고인인 경우
        if result is None:
            return {
                "라인": "-",
                "티어": "-",
                "승률": "-",
                "픽률": "-",
                "밴률": "-"
            }

        position_kr = {"top":"탑", "jungle":"정글", "mid":"미드", "bottom":"바텀", "support":"서포터"}
        champion_stats = {
            "라인": position_kr[result['position']],
            "티어": result['champion_tier'],
            "승률": result['win_rate'],
            "픽률": result['pick_rate'],
            "밴률": result['ban_rate']
        }
        return champion_stats

    def get_champion_pick_rate_info(self, name_us, patch, position):
        #unmatch_line일때 체크
        check_query = self.fetch_one(f"select * from champion_score_{position} where name_us = %s and patch = %s", args=(name_us, patch))
        if check_query is None:
            position = "all"
        select_query = f"""
        select name_kr, ranking, pick_rate, win_rate, ban_rate, champion_tier,
         (SELECT COUNT(*) FROM champion_score_{position} WHERE patch = %s) as total_champion_count, 
         (select COUNT(*) + 1 FROM champion_score_{position} c2 WHERE c2.pick_rate > c1.pick_rate AND patch = %s) as pick_rank, 
         (select COUNT(*) + 1 FROM champion_score_{position} c2 WHERE c2.win_rate > c1.win_rate AND patch = %s) as win_rank, 
         (select COUNT(*) + 1 FROM champion_score_{position} c2 WHERE c2.ban_rate > c1.ban_rate AND patch = %s) as ban_rank 
         from champion_score_{position} c1 where name_us = %s and patch = %s """
        result = self.fetch_one(select_query, args=(patch, patch, patch, patch, name_us, patch))
        # 전체, 특정라인에서 안나오면 고인임.
        if result is None:
            raise CommonError(ErrorCode.DEAD_CHAMPION, "Dead Champion")
        champion_stats = {
            "position": position,
            "name_kr": result['name_kr'],
            "total_champion_count": result['total_champion_count'],
            "ranking": result['ranking'],
            "pick_rate": result['pick_rate'],
            "win_rate": result['win_rate'],
            "ban_rate": result['ban_rate'],
            "tier": result['champion_tier'],
            "pick_rank": result['pick_rank'],
            "win_rank": result['win_rank'],
            "ban_rank": result['ban_rank']
        }
        return champion_stats

    def get_counter_champion(self, name_us, position, patch):
        query = f"""
               WITH matchups AS (
                    SELECT 
                        m1.gameid,
                        m1.name_us as target_champ,
                        m1.position as target_pos,
                        m2.name_us as opponent_champ,
                        m2.position as opponent_pos,
                        m1.result as target_won,
                        m1.golddiffat15,
                        m1.xpdiffat15,
                        (m1.kills + m1.assists) / CASE WHEN m1.deaths = 0 THEN 1 ELSE m1.deaths END as target_kda,
                        (m2.kills + m2.assists) / CASE WHEN m2.deaths = 0 THEN 1 ELSE m2.deaths END as opponent_kda
                    FROM oracle_elixir_{self.year} m1
                    JOIN oracle_elixir_{self.year} m2 
                        ON m1.gameid = m2.gameid
                        AND m1.side != m2.side
                        AND m1.position = m2.position
                    WHERE m1.name_us = %s
                        AND m1.position = %s
                        AND m1.patch = %s
                )
                SELECT 
                    m.opponent_champ,
                    ci.name_kr,
                    COUNT(*) as games_played,
                    ROUND(AVG(CASE WHEN m.target_won = 1 THEN 1 ELSE 0 END) * 100, 2) as win_rate,
                    ROUND(AVG(m.golddiffat15), 2) as avg_gold_diff_15,
                    ROUND(AVG(m.xpdiffat15), 2) as avg_xp_diff_15,
                     ROUND(AVG(m.target_kda), 2) + ROUND(AVG(m.opponent_kda), 2) as kda_diff
                FROM matchups m
                LEFT JOIN champion_info ci ON m.opponent_champ = ci.ps_name  
                GROUP BY m.opponent_champ, ci.name_kr 
                ORDER BY win_rate DESC, games_played DESC
            """
        results = pd.read_sql(query, self.connection, params=[name_us, position, patch])
        results['counter_score'] = (
                results['win_rate'] * 0.4 +
                results['avg_gold_diff_15'].clip(-2000, 2000) / 20 * 0.3 +
                results['avg_xp_diff_15'].clip(-2000, 2000) / 20 * 0.3
        )
        results = results.dropna()
        return results


    def get_player_comparison_series(self, game_id, player_name, opponent_player_name):
        query = f"""
               SELECT 
                   p.playername,
                   p.position,
                   p.name_us as champion_name,
                   n.name_kr as champion_kr_name, 
                   p.goldat10, p.goldat15, p.goldat20, p.goldat25,
                   p.golddiffat10, p.golddiffat15, p.golddiffat20, p.golddiffat25,
                   p.xpat10, p.xpat15, p.xpat20, p.xpat25,
                   p.xpdiffat10, p.xpdiffat15, p.xpdiffat20, p.xpdiffat25,
                   p.damagetochampions,
                   p.damageshare,
                   p.earnedgoldshare

               FROM oracle_elixir_{self.year} p
               LEFT JOIN champion_info n ON p.name_us = n.ps_name
               WHERE p.gameid = %(game_id)s 
               AND p.playername IN (%(player1)s, %(player2)s)
           """

        df = pd.read_sql(
            query,
            self.connection,
            params={
                'game_id': game_id,
                'player1': player_name,
                'player2': opponent_player_name
            }
        )
        player_data = df[df['playername'] == player_name].iloc[0]
        opponent_player_data = df[df['playername'] == opponent_player_name].iloc[0]
        time_frames = [10, 15, 20, 25]
        gold_diff_data = {
            f"{t}min": {
                player_name: int(player_data[f'goldat{t}']) if not pd.isna(player_data[f'goldat{t}']) else None,
                opponent_player_name: int(opponent_player_data[f'goldat{t}']) if not pd.isna(opponent_player_data[f'goldat{t}']) else None,
                 'diff': int(player_data[f'golddiffat{t}']) if not pd.isna(player_data[f'golddiffat{t}']) else None
            }
            for t in time_frames
            if not (pd.isna(df.iloc[0][f'goldat{t}']) and pd.isna(df.iloc[1][f'goldat{t}']))
        }
        exp_diff_data = {
            f"{t}min": {
                player_name: int(player_data[f'xpat{t}']) if not pd.isna(player_data[f'xpat{t}']) else None,
                opponent_player_name: int(opponent_player_data[f'xpat{t}']) if not pd.isna(opponent_player_data[f'xpat{t}']) else None,
                'diff': int(player_data[f'xpdiffat{t}']) if not pd.isna(player_data[f'xpdiffat{t}']) else None
            }
            for t in time_frames
            if not (pd.isna(df.iloc[0][f'xpat{t}']) and pd.isna(df.iloc[1][f'xpat{t}']))
        }
        line_kr = {"top": "탑", "jungle": "정글", "mid": "미드", "bottom": "원딜", "support": "서포터", }
        formatted_data = {
            'champion_kr_name': player_data['champion_kr_name'],
            'opp_kr_name': opponent_player_data['champion_kr_name'],
            'position': line_kr[df.iloc[0]['position']],
            'time_frames': list(gold_diff_data.keys()),
            'gold_diff_data': gold_diff_data,
            'exp_diff_data': exp_diff_data
        }
        return formatted_data

    def get_radar_stats_backup(self, game_id, player_name):
        game_df = self.get_game_data(game_id)
        player_df = game_df[game_df["playername"] == player_name].iloc[0]
        opp_player_df = game_df[(game_df["position"] == player_df['position']) & (game_df['side'] != player_df['side'])].iloc[0]
        player_name_kr = self.get_name_kr(player_df['name_us'])
        opp_player_name_kr = self.get_name_kr(opp_player_df['name_us'])

        base_stats = ['kills', 'deaths', 'assists', 'damagetochampions', 'damagetakenperminute']
        label_mapping = {
            'kills': '킬',
            'deaths': '데스',
            'assists': '어시스트',
            'damagetochampions': '가한 피해량',
            'damagetakenperminute': '분당 받은 피해량',
            'totalgold': '골드 획득',
            'laning_score': '라인전 점수',
            'visionscore': '시야 점수',
            'dragons': '드래곤',
            'barons': '바론'
        }

        position = player_df['position']
        if position in ['mid', 'top', 'bottom']:
            player_laning = ((player_df['golddiffat15'] * 0.4) +
                             (player_df['xpdiffat15'] * 0.3) +
                             (player_df['csdiffat15'] * 0.3))
            opp_laning = ((opp_player_df['golddiffat15'] * 0.4) +
                          (opp_player_df['xpdiffat15'] * 0.3) +
                          (opp_player_df['csdiffat15'] * 0.3))
            stats = base_stats + ['totalgold', 'laning_score']
            stats_values = {
                'player': [player_df[stat] for stat in base_stats] + [player_df['totalgold'], player_laning],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [opp_player_df['totalgold'], opp_laning]
            }

        elif position == 'jungle':
            player_team = game_df[(game_df['position'] == "team") & (game_df['side'] == player_df['side'])].iloc[0]
            opp_team = game_df[(game_df['position'] == "team") & (game_df['side'] == opp_player_df['side'])].iloc[0]

            stats = base_stats + ['dragons', 'barons']
            stats_values = {
                'player': [player_df[stat] for stat in base_stats] + [int(player_team['dragons']), int(player_team['barons'])],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [int(opp_team['dragons']), int(opp_team['barons'])]
            }

        else:  # support
            player_laning = ((player_df['golddiffat15'] * 0.4) +
                             (player_df['xpdiffat15'] * 0.3) +
                             (player_df['csdiffat15'] * 0.3))
            opp_laning = ((opp_player_df['golddiffat15'] * 0.4) +
                          (opp_player_df['xpdiffat15'] * 0.3) +
                          (opp_player_df['csdiffat15'] * 0.3))

            stats = base_stats + ['visionscore', 'laning_score']
            stats_values = {
                'player': [player_df[stat] for stat in base_stats] + [player_df['visionscore'], player_laning],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [opp_player_df['visionscore'], opp_laning]
            }
        max_values = [max(stats_values['player'][i], stats_values['opponent'][i]) for i in range(len(stats))]
        normalized_values = {
            'player': [val / max_val * 0.7 if max_val != 0 else 0 for val, max_val in
                       zip(stats_values['player'], max_values)],
            'opponent': [val / max_val * 0.7 if max_val != 0 else 0 for val, max_val in
                         zip(stats_values['opponent'], max_values)]
        }

        return {
            'game_id': game_id,
            'position': position,
            'stats': stats,
            'label_mapping': label_mapping,
            'stats_values': stats_values,
            'normalized_values': normalized_values,
            'player_names': {
                'player': f"{player_df['playername']}({player_name_kr})",
                'opponent': f"{opp_player_df['playername']}({opp_player_name_kr})"
            }
        }

    def get_radar_stats(self, game_id, player_name):
        game_df = self.get_game_data(game_id)
        player_df = game_df[game_df["playername"] == player_name].iloc[0]
        opp_player_df = game_df[(game_df["position"] == player_df['position']) & (game_df['side'] != player_df['side'])].iloc[0]
        player_name_kr = self.get_name_kr(player_df['name_us'])
        opp_player_name_kr = self.get_name_kr(opp_player_df['name_us'])

        base_stats = ['kills', 'deaths', 'assists', 'damagetochampions', 'damagetakenperminute']
        label_mapping = {
            'kills': '킬',
            'deaths': '데스',
            'assists': '어시스트',
            'damagetochampions': '가한 피해량',
            'damagetakenperminute': '분당 받은 피해량',
            'totalgold': '골드 획득',
            'laning_score': '라인전 점수',
            'visionscore': '시야 점수',
            'dragons': '드래곤',
            'barons': '바론'
        }

        # 시그모이드 함수를 사용한 레이닝 점수 계산 함수
        def calculate_sigmoid_laning_score(player_stats, opp_stats):
            # 골드, 경험치, CS 차이 구하기
            gold_diff = player_stats['golddiffat15'] - opp_stats['golddiffat15']
            xp_diff = player_stats['xpdiffat15'] - opp_stats['xpdiffat15']
            cs_diff = player_stats['csdiffat15'] - opp_stats['csdiffat15']

            # 시그모이드 함수를 사용한 점수 계산
            # 골드 차이 - 더 민감하게 반응하도록 k값 조정
            k_gold = 0.002  # 1500 골드 차이에서 약 85% 수준으로 포화되도록 설정
            norm_gold = 1 / (1 + np.exp(-k_gold * gold_diff))

            # 경험치 차이
            k_xp = 0.003  # 1000 XP 차이에서 약 85% 수준으로 포화되도록 설정
            norm_xp = 1 / (1 + np.exp(-k_xp * xp_diff))

            # CS 차이
            k_cs = 0.1  # 30 CS 차이에서 약 85% 수준으로 포화되도록 설정
            norm_cs = 1 / (1 + np.exp(-k_cs * cs_diff))

            # 포지션별 맞춤형 가중치 적용
            position = player_stats['position']

            if position == 'top':
                weights = {'gold': 0.3, 'xp': 0.3, 'cs': 0.4}  # 탑은 CS와 경험치가 중요
            elif position == 'mid':
                weights = {'gold': 0.4, 'xp': 0.3, 'cs': 0.3}  # 미드는 골드와 로밍 영향력이 중요
            elif position == 'bottom':
                weights = {'gold': 0.5, 'xp': 0.2, 'cs': 0.3}  # 원딜은 골드가 가장 중요
            elif position == 'jungle':
                weights = {'gold': 0.4, 'xp': 0.4, 'cs': 0.2}  # 정글은 골드와 경험치가 중요
            else:  # support
                weights = {'gold': 0.3, 'xp': 0.5, 'cs': 0.2}  # 서포터는 경험치와 로밍이 중요

            # 가중 평균 계산
            laning_score_normalized = (
                    norm_gold * weights['gold'] +
                    norm_xp * weights['xp'] +
                    norm_cs * weights['cs']
            )

            # 0~10 범위로 변환
            laning_score = laning_score_normalized * 10

            # 소수점 첫째 자리에서 반올림
            return round(laning_score, 1)

        position = player_df['position']
        if position in ['mid', 'top', 'bottom']:
            # 양 선수의 레이닝 점수를 각각 계산
            player_laning = calculate_sigmoid_laning_score(player_df, opp_player_df)
            opp_laning = calculate_sigmoid_laning_score(opp_player_df, player_df)

            stats = base_stats + ['totalgold', 'laning_score']
            stats_values = {
                'player': [player_df[stat] for stat in base_stats] + [player_df['totalgold'], player_laning],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [opp_player_df['totalgold'], opp_laning]
            }

        elif position == 'jungle':
            player_team = game_df[(game_df['position'] == "team") & (game_df['side'] == player_df['side'])].iloc[0]
            opp_team = game_df[(game_df['position'] == "team") & (game_df['side'] == opp_player_df['side'])].iloc[0]

            stats = base_stats + ['dragons', 'barons']
            stats_values = {
                'player': [player_df[stat] for stat in base_stats] + [int(player_team['dragons']),
                                                                      int(player_team['barons'])],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [int(opp_team['dragons']),
                                                                            int(opp_team['barons'])]
            }

        else:  # support
            # 서포터도 동일한 방식으로 각각 계산
            player_laning = calculate_sigmoid_laning_score(player_df, opp_player_df)
            opp_laning = calculate_sigmoid_laning_score(opp_player_df, player_df)

            stats = base_stats + ['visionscore', 'laning_score']
            stats_values = {
                'player': [player_df[stat] for stat in base_stats] + [player_df['visionscore'], player_laning],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [opp_player_df['visionscore'], opp_laning]
            }

        # 레이더 차트를 위한 정규화 (데스는 낮을수록 좋으므로 특별 처리)
        max_values = [max(stats_values['player'][i], stats_values['opponent'][i]) if stats[i] != 'deaths' else min(
            stats_values['player'][i], stats_values['opponent'][i]) for i in range(len(stats))]
        normalized_values = {
            'player': [val / max_val * 0.7 if max_val != 0 else 0 for val, max_val in
                       zip(stats_values['player'], max_values)],
            'opponent': [val / max_val * 0.7 if max_val != 0 else 0 for val, max_val in
                         zip(stats_values['opponent'], max_values)]
        }

        return {
            'game_id': game_id,
            'position': position,
            'stats': stats,
            'label_mapping': label_mapping,
            'stats_values': stats_values,
            'normalized_values': normalized_values,
            'player_names': {
                'player': f"{player_df['playername']}({player_name_kr})",
                'opponent': f"{opp_player_df['playername']}({opp_player_name_kr})"
            }
        }

    def update_patch_info(self, info):
        query = """
                INSERT INTO patch_info (patch, title, url, description, patch_date)
                VALUES (%(patch)s, %(title)s, %(url)s, %(description)s, %(patch_date)s)
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    url = VALUES(url),
                    description = VALUES(description),
                    patch_date = VALUES(patch_date)
            """
        patch_date = datetime.strptime(info['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
        params = {
            'patch': info['version'],
            'title': info['title'],
            'url': info['url'],
            'description': info['description'],
            'patch_date': patch_date
        }
        self.cursor.execute(query, params)
        self.commit()

    def get_patch_url_list(self):
        query = "select patch, url from patch_info"
        return self.fetch_all(query)

    def get_mvp_player(self, game_df):
        if game_df is None or game_df.empty:
            return None
        mvp_scores = self.calculate_mvp_score(game_df)
        mvp_player = {
            'name_kr': mvp_scores.iloc[0]['name_kr'],
            'playername': mvp_scores.iloc[0]['playername'],
            'mvp_score': round(mvp_scores.iloc[0]['mvp_score'], 2)
        }
        return mvp_player

    def calculate_mvp_score(self, df):
        position_weights = {
            'top': {
                'combat': 1.7,
                'economy': 1.4,
                'vision': 0.5,
                'objective': 0.8,
                'laning': 1.1
            },
            'mid': {
                'combat': 2.0,
                'economy': 1.6,
                'vision': 0.5,
                'objective': 0.6,
                'laning': 0.8
            },
            'bottom': {
                'combat': 1.8,
                'economy': 1.8,
                'vision': 0.4,
                'objective': 0.5,
                'laning': 1.0
            },
            'jungle': {
                'combat': 1.6,
                'economy': 0.8,
                'vision': 0.9,
                'objective': 1.7,
                'laning': 0.5
            },
            'support': {
                'combat': 1.4,
                'economy': 0.4,
                'vision': 1.8,
                'objective': 0.8,
                'laning': 1.1
            }
        }

        team_data = df[df['position'] == 'team'].copy()
        player_data = df[df['position'] != 'team'].copy()

        def normalize_stats(group):
            stats_to_normalize = [
                'kills', 'deaths', 'assists', 'cspm', 'damageshare', 'earnedgoldshare',
                'vspm', 'wcpm', 'wpm', 'damagetakenperminute', 'damagemitigatedperminute',
                'monsterkillsenemyjungle', 'visionscore', 'gspd',
                'golddiffat15', 'xpdiffat15', 'csdiffat15'
            ]

            for stat in stats_to_normalize:
                if stat in group.columns:
                    max_val = group[stat].max()
                    min_val = group[stat].min()
                    if max_val != min_val:
                        group[f'normalized_{stat}'] = (group[stat] - min_val) / (max_val - min_val)
                    else:
                        group[f'normalized_{stat}'] = 0.5
            return group
        player_data = normalize_stats(player_data)
        mvp_scores = []
        for _, player in player_data.iterrows():
            position = player['position'].lower()
            weights = position_weights[position]

            combat_score = (
                                   (player['normalized_kills'] * 0.15) +
                                   ((1 - player['normalized_deaths']) * 0.15) +
                                   (player['normalized_assists'] * 0.1) +
                                   (player['normalized_damageshare'] * 0.4) +
                                   (player['normalized_damagemitigatedperminute'] * 0.2)
                           ) * weights['combat']

            economy_score = (
                                    (player['normalized_cspm'] * 0.4) +
                                    (player['normalized_earnedgoldshare'] * 0.6)
                            ) * weights['economy']

            vision_score = (
                                   (player['normalized_visionscore'] * 0.5) +
                                   (player['normalized_wcpm'] * 0.3) +
                                   (player['normalized_wpm'] * 0.2)
                           ) * weights['vision']

            laning_score = (
                                   (player['normalized_golddiffat15'] * 0.4) +
                                   (player['normalized_xpdiffat15'] * 0.3) +
                                   (player['normalized_csdiffat15'] * 0.3)
                           ) * weights['laning']

            team_row = team_data[team_data['result'] == player['result']].iloc[0]

            max_dragons = 4
            max_barons = 3
            max_towers = 11
            tower_score = min(team_row['towers'] / max_towers, 1.0) * 0.20
            dragon_score = min(team_row['dragons'] / max_dragons, 1.0) * 0.40
            baron_score = min(team_row['barons'] / max_barons, 1.0) * 0.40
            objective_participation = tower_score + dragon_score + baron_score
            objective_score = objective_participation * weights['objective']
            score_breakdown = {
                'combat': combat_score,
                'economy': economy_score,
                'vision': vision_score,
                'objective': objective_score,
                'laning': laning_score
            }

            final_score = sum(score_breakdown.values())

            if player['result']:
                final_score *= 1.1

            mvp_scores.append({
                'playername': player['playername'],
                'champion': player['name_us'],
                'teamname': player['teamname'],
                'name_kr': self.get_name_kr(player['name_us']),
                'position': position,
                'mvp_score': final_score
            })

        mvp_df = pd.DataFrame(mvp_scores)
        ideal_max_score = 5.5
        mvp_df['mvp_score'] = mvp_df['mvp_score'] / ideal_max_score
        scaling_factor = 8.0
        power_factor = 1.2
        mvp_df['mvp_score'] = (mvp_df['mvp_score'] * power_factor) * scaling_factor
        mvp_df['mvp_score'] = mvp_df['mvp_score'].clip(0, 10)
        mvp_df = mvp_df.sort_values('mvp_score', ascending=False)
        return mvp_df

    def get_sets_score(self, game_id, blue_team_name, red_team_name):
        info_query = f"""select game_date, game, league from oracle_elixir_{self.year} where gameid = %s"""
        base_info = self.fetch_one(info_query, game_id)
        game_date = base_info.get('game_date')
        game = base_info.get('game')
        league = base_info.get('league')
        info_query = f"""select * from oracle_elixir_{self.year} where league = %s and (teamname = %s or teamname = %s) and position = 'team' and game_date between Date(%s) and Date_Add(Date(%s), interval 1 Day) order by game_date"""
        info = pd.read_sql(info_query, self.connection, params=(league, blue_team_name, red_team_name, game_date, game_date))
        blue_score = len(info[(info['teamname'] == blue_team_name) & (info['result'] == 1)])
        red_score = len(info[(info['teamname'] == red_team_name) & (info['result'] == 1)])
        return blue_score, red_score

    def get_sets_game_id(self, game_id, blue_team_name, red_team_name):
        info_query = f"""select game_date, game, league from oracle_elixir_{self.year} where gameid = %s"""
        base_info = self.fetch_one(info_query, game_id)
        game_date = base_info.get('game_date')
        game = base_info.get('game')
        league = base_info.get('league')
        info_query = f"""select gameid, game from oracle_elixir_{self.year} where league = %s and (teamname = %s or teamname = %s) and position = 'team' and game_date between Date(%s) and Date_Add(Date(%s), interval 1 Day)"""
        info = pd.read_sql(info_query, self.connection, params=(league, blue_team_name, red_team_name, game_date, game_date))
        result = info.sort_values('game').groupby('gameid', sort=False).first().reset_index()
        return result
 
    def get_league_title(self, game_id):
        query = f"select league, game_year, split from oracle_elixir_{self.year} where gameid = %s"
        info = self.fetch_one(query, game_id)
        return info

    def calculate_overall_mvp_score(self, game_df, match_id, player_name):
        info_query = f"""select game_date, game, league from oracle_elixir_{self.year} where gameid = %s"""
        base_info = self.fetch_one(info_query, match_id)
        game_date = base_info.get('game_date')
        game = base_info.get('game')
        league = base_info.get('league')
        player_team = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        opp_team = game_df[game_df['teamname'] != player_team]['teamname'].iloc[0]
        info_query = f"""select * from oracle_elixir_{self.year} where league = %s and (teamname = %s or teamname = %s) and position = 'team' and game_date between Date(%s) and Date_Add(Date(%s), interval 1 Day) order by game_date"""
        series_data = pd.read_sql(info_query, self.connection, params=(league, player_team, opp_team, game_date, game_date))

        game_ids = series_data['gameid'].unique()

        all_mvp_scores = []
        for game_id in game_ids:
            game_data = self.get_game_data(game_id)
            mvp_df = self.calculate_mvp_score(game_data)
            game_num = game_data['game'].iloc[0]
            mvp_df['game'] = game_num
            all_mvp_scores.append(mvp_df)

        combined_mvp = pd.concat(all_mvp_scores)
        overall_mvp = combined_mvp.groupby(['playername', 'position', 'teamname']).agg({
            'mvp_score': 'mean',
            'name_kr': lambda x: ', '.join(set(x))
        }).reset_index()
        overall_mvp = overall_mvp.sort_values('mvp_score', ascending=False)
        return overall_mvp

    def save_league_info(self, save_dir, leagues):
        insert_query = """
        INSERT INTO league_info (
            official_site_name,
            official_site_slug,
            official_site_id,
            region,
            image_path
        ) VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            official_site_name = VALUES(official_site_name),
            official_site_id = VALUES(official_site_id),
            region = VALUES(region),
            image_path = VALUES(image_path)
        """
        params = []
        for league in leagues:
            league_id = league.get('id', '')
            league_slug = league.get('slug', '')
            league_name = league.get('name', '')
            league_region = league.get('region', '')

            local_image_path = f"{save_dir}/{league_slug}.png"

            params.append((
                league_name,
                league_slug,
                league_id,
                league_region,
                local_image_path
            ))
        for param in params:
            self.cursor.execute(insert_query, param)
        self.connection.commit()

    def get_league_id(self):
        select_query = "select * from league_info"
        return self.fetch_all(select_query)

    def save_tournament_info(self, tournament, league_seq):
        tournament_id = tournament.get('id', '')
        tournament_slug = tournament.get('slug', '')
        start_date = tournament.get('startDate', '')
        query = "SELECT COUNT(*) as count FROM tournament_info WHERE official_site_id = %s"
        result = self.fetch_all(query, (tournament_id,))
        exists = result[0]['count'] > 0 if result else False
        if exists:
            update_query = """
            UPDATE tournament_info 
            SET official_site_slug = %s, start_date = %s
            WHERE official_site_id = %s
            """
            self.cursor.execute(update_query, (tournament_slug, start_date, tournament_id))
        else:
            insert_query = """
            INSERT INTO tournament_info 
            (official_site_id, official_site_slug, league_seq, start_date) 
            VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(insert_query, (tournament_id, tournament_slug, league_seq, start_date))
        self.commit()

    def save_team_info(self, team, local_image_path, league_seq):
        team_id = team.get('id', '')
        team_name = team.get('name', '')
        team_slug = team.get('slug', '')
        team_code = team.get('code', '')
        team_image = local_image_path if local_image_path else team.get('image', '')
        record = team.get('record', {})
        if record is None:
            record = {}
        wins = record.get('wins', 0)
        losses = record.get('losses', 0)
        ties = record.get('ties', 0)
        query = """
        INSERT INTO team_info (
            official_site_id,
            official_site_name,
            official_site_slug,
            official_site_code,
            wins,
            losses,
            ties,
            image_path,
            league_seq
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            official_site_id = VALUES(official_site_id),
            official_site_name = VALUES(official_site_name),
            official_site_code = VALUES(official_site_code),
            wins = VALUES(wins),
            losses = VALUES(losses),
            ties = VALUES(ties),
            image_path = VALUES(image_path),
            league_seq = VALUES(league_seq)
        """
        self.cursor.execute(query, (team_id, team_name, team_slug, team_code, wins, losses, ties, team_image, league_seq))
        self.commit()

    def clean_team_name(self, name):
        """팀 이름 정규화: 특수문자 제거, 소문자 변환, 불용어 제거"""
        TEAM_STOPWORDS = {'team', 'gaming', 'esports', 'e-sports', 'esport', 'honda', '-', 'e', 'sports'}
        name = regex.sub(r'[^\w\s]', ' ', name.lower())
        tokens = name.lower().split()
        filtered = [t for t in tokens if t not in TEAM_STOPWORDS]
        return ' '.join(filtered)

    def find_best_match(self, team_name, candidate_list, threshold=70):
        best_score = 0
        best_match = None
        clean_name = self.clean_team_name(team_name)
        name_tokens = set(clean_name.split())

        for candidate in candidate_list:
            clean_candidate = self.clean_team_name(candidate)
            candidate_tokens = set(clean_candidate.split())

            # 정확히 일치
            if clean_name == clean_candidate:
                return candidate, 100

            # 유사도 점수 계산
            token_score = fuzz.token_sort_ratio(clean_name, clean_candidate)
            partial_score = fuzz.partial_ratio(clean_name, clean_candidate)
            overlap_score = len(name_tokens & candidate_tokens) / max(len(name_tokens | candidate_tokens), 1) * 100

            # 추가: 부분 단어 일치 비율
            token_match_ratio_1 = len(name_tokens & candidate_tokens) / max(len(name_tokens), 1)
            token_match_ratio_2 = len(name_tokens & candidate_tokens) / max(len(candidate_tokens), 1)
            subset_match_score = max(token_match_ratio_1, token_match_ratio_2) * 100

            score = (token_score + partial_score + overlap_score + subset_match_score) / 4

            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= threshold:
            return best_match, best_score
        else:
            return None, best_score

    def match_team_name(self):
        oracle_teams_data_2025 = self.fetch_all("SELECT DISTINCT teamname FROM oracle_elixir_2025")
        oracle_teams_data_2024 = self.fetch_all("SELECT DISTINCT teamname FROM oracle_elixir_2024")
        oracle_teams_2025 = [row['teamname'] for row in oracle_teams_data_2025]
        oracle_teams_2024 = [row['teamname'] for row in oracle_teams_data_2024]

        team_info_records = self.fetch_all("SELECT seq, official_site_name, official_site_slug, official_site_code FROM team_info")

        if not team_info_records:
            self.logger.warning("team_info 테이블에서 팀 정보를 찾을 수 없습니다.")
            return

        mapping_results = []
        update_count = 0

        for team in team_info_records:
            team_seq = team['seq']
            official_site_team_name = team['official_site_name']
            official_site_slug = team['official_site_slug']
            official_site_code = team['official_site_code']
            best_match, score = self.find_best_match(official_site_team_name, oracle_teams_2025)
            if best_match is None:
                best_match, score = self.find_best_match(official_site_slug, oracle_teams_2025)
            if best_match is None:
                best_match, score = self.find_best_match(official_site_code, oracle_teams_2025)
            if best_match is None:
                best_match, score = self.find_best_match(official_site_team_name, oracle_teams_2024)
            if best_match is None:
                best_match, score = self.find_best_match(official_site_slug, oracle_teams_2024)
            if best_match is None:
                best_match, score = self.find_best_match(official_site_code, oracle_teams_2024)
            mapping_results.append({
                'team_seq': team_seq,
                'official_site_name': official_site_team_name,
                'oracle_elixir_team_name': best_match,
                'match_score': score
            })

            if best_match is not None:
                update_query = """
                        UPDATE team_info 
                        SET oracle_elixir_team_name = %s 
                        WHERE seq = %s
                        """
                self.cursor.execute(update_query, (best_match, team_seq))
                update_count += 1
        self.connection.commit()
        print(f"총 {len(team_info_records)}개 팀 중 {update_count}개 팀 매칭 완료")
        self.logger.info(f"총 {len(team_info_records)}개 팀 중 {update_count}개 팀 매칭 완료")
        unmatched = [result for result in mapping_results if result['oracle_elixir_team_name'] is None]
        if unmatched:
            print(f"{len(unmatched)}개 팀이 매칭되지 않았습니다.")
            self.logger.info(f"{len(unmatched)}개 팀이 매칭되지 않았습니다.")
            for team in unmatched:
                print(f"매칭 실패: {team['official_site_name']} (ID: {team['team_seq']})")
                self.logger.info(f"매칭 실패: {team['official_site_name']} (ID: {team['team_seq']})")
        manual_code1 = '''update team_info set oracle_elixir_team_name = "OKSavingsBank BRION Challengers" where official_site_name = "BRO Challengers"'''
        manual_code2 = '''update team_info set oracle_elixir_team_name = "Nongshim Esports Academy" where official_site_name = "NS Challengers"'''
        manual_code3 = '''update team_info set oracle_elixir_team_name = "Hanwha Life Esports Challengers" where official_site_name = "HLE Challengers"'''
        self.cursor.execute(manual_code1)
        self.cursor.execute(manual_code2)
        self.cursor.execute(manual_code3)
        self.commit()
        return mapping_results

    def get_all_team_slug(self):
        select_query = "select official_site_slug from team_info"
        return self.fetch_all(select_query)

    def get_team_icon_name_by_oracle_elixir(self, oracle_elixir_team_name):
        select_query = "select official_site_slug from team_info where oracle_elixir_team_name = (%s)"
        result = self.fetch_one(select_query, oracle_elixir_team_name)
        if result is not None:
            return result.get("official_site_slug")
        else:
            self.logger.info(f"팀 아이콘 정보 없음 : {oracle_elixir_team_name}")
            print(f"팀 아이콘 정보 없음 : {oracle_elixir_team_name}")

    def find_game_id_by_title_info(self, title_info):
        player_name = title_info.get("player_name")
        player_team_code = title_info.get("player_team")
        opp_team_code = title_info.get("opp_team")
        date_info = title_info.get("date")
        select_team_name = "select oracle_elixir_team_name from team_info where official_site_code = %s"
        team_result = self.fetch_one(select_team_name, player_team_code)
        if team_result is None:
            return None
        player_team = team_result.get("oracle_elixir_team_name")
        select_query = f"""select gameid from oracle_elixir_{self.year} where playername = %s and teamname = %s and DATE_FORMAT(game_date, "%%Y-%%m-%%d") = %s order by game_date desc"""
        find_game = self.fetch_one(select_query, (player_name, player_team, date_info))
        if find_game is None:
            return None
        return find_game.get("gameid")

    def update_ps_name(self, data_info):
        for champion_data in data_info['data']:
            insert_query = "insert ignore into champion_info (name_kr, ps_name) values (%s, %s) "
            values = (champion_data['nameKr'], champion_data['nameUs'])
            self.cursor.execute(insert_query, values)
            self.commit()
        update_query = """UPDATE champion_info ci JOIN oracle_elixir_2025 oe ON ci.ps_name = oe.name_us SET ci.oracle_elixir_name = oe.name_us WHERE ci.oracle_elixir_name IS NULL"""
        self.cursor.execute(update_query)
        self.commit()


