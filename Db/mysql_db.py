import os
import sys

import numpy as np
import pymysql
import pandas as pd
from datetime import datetime
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
                            INSERT INTO oracle_elixir_{self.year} ({columns})
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

    def get_latest_patch(self):
        select_query = f"select max(patch) from oracle_elixir_{self.year}"
        return self.fetch_one(select_query)

    def get_all_champion_list(self, patch):
        position_champions = {}
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        for position in positions:
            query = f"SELECT name_us FROM champion_score_{position} where patch = {patch}"
            position_champions[position] = pd.read_sql(query, self.connection)['name_us'].tolist()
        return position_champions

    def get_player_info(self, patch):
        select_query = f"""
        SELECT *
        FROM oracle_elixir_{self.year} 
        WHERE position != 'team'
        AND patch = {patch}
        ORDER BY gameid, side
        """
        match_info = pd.read_sql(select_query, self.connection)
        return match_info

    def get_team_info(self):
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

    def get_champion_rate_table(self, name_us, patch, position):
        select_query = f"select name_us, pick_rate, win_rate, ban_rate, champion_tier from champion_score_{position} where name_us = (%s) and patch = (%s) "
        result = self.fetch_one(select_query, args=(name_us, patch))
        position_kr = {"top":"탑", "jungle":"정글", "mid":"미드", "bottom":"바텀", "support":"서포터"}
        champion_stats = {
            "라인": position_kr[position],
            "티어": result['champion_tier'],
            "승률": result['win_rate'],
            "픽률": result['pick_rate'],
            "밴률": result['ban_rate']
        }
        return champion_stats

    def get_champion_pick_rate_info(self, name_us, patch, position):
        select_query = f"select name_kr, ranking, pick_rate, win_rate, ban_rate, champion_tier from champion_score_{position} where name_us = (%s) and patch = (%s) "
        result = self.fetch_one(select_query, args=(name_us, patch))
        champion_stats = {
            "position": position,
            "name_kr": result['name_kr'],
            "ranking": result['ranking'],
            "pick_rate": result['pick_rate'],
            "win_rate": result['win_rate'],
            "ban_rate": result['ban_rate'],
            "tier": result['champion_tier']
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
                        (m1.killsat15 + m1.assistsat15) / CASE WHEN m1.deathsat15 = 0 THEN 1 ELSE m1.deathsat15 END as target_kda15,
                        (m2.killsat15 + m2.assistsat15) / CASE WHEN m2.deathsat15 = 0 THEN 1 ELSE m2.deathsat15 END as opponent_kda15
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
                     ROUND(AVG(m.target_kda15), 2) + ROUND(AVG(m.opponent_kda15), 2) as kda_diff
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
                'player': [player_df[stat] for stat in base_stats] + [player_team['dragons'], player_team['barons']],
                'opponent': [opp_player_df[stat] for stat in base_stats] + [opp_team['dragons'], opp_team['barons']]
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
            objective_participation = 0

            max_dragons = 4
            max_barons = 2
            max_towers = 11
            max_heralds = 2
            tower_score = min(team_row['towers'] / max_towers, 1.0) * 0.25
            dragon_score = min(team_row['dragons'] / max_dragons, 1.0) * 0.35
            baron_score = min(team_row['barons'] / max_barons, 1.0) * 0.25
            herald_score = min(team_row['heralds'] / max_heralds, 1.0) * 0.15
            objective_participation = tower_score + dragon_score + baron_score + herald_score
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