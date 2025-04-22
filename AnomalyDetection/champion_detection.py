import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
from pathlib import Path
import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt

"""
    oracle_elixir IF,
    pick_rate,
    performance score,
    unmatch_line,
    bottom_two_choice
"""
class ChampionDetection:

    def __init__(self, database, meta_data, patch):
        self.database = database
        self.basic_info = meta_data.basic_info
        self.output_dir = Path(__file__).parent.parent / 'PltOutput'
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.patch = patch
        self.line_list = ["top","mid","jungle","bottom","support"]


    def run_performance_score(self):
        self.update_performance_score()
        match_info = self.database.detect_by_performance_score(self.patch.version)

    def run_two_bottom_choice(self, game_date=None):
        bottom_champions = self.database.get_only_bottom_champion(self.patch.version)
        match_info = self.database.get_all_data_without_team(self.patch.version, game_date)
        multi_adc_games = []
        for (gameid, side), team_picks in match_info.groupby(['gameid', 'side']):
            adc_picks = [pick for pick in team_picks.itertuples() if pick.name_us in bottom_champions]
            unmatch_picks = [pick for pick in team_picks.itertuples()
                             if pick.name_us in bottom_champions and pick.position != 'bottom']

            if len(adc_picks) >= 2:
                game_info = {
                    'gameid': gameid,
                    'team_name': unmatch_picks[0].teamname,
                    'playername': unmatch_picks[0].playername
                }
                multi_adc_games.append(game_info)
        return multi_adc_games

    def run_penta_kill(self, game_date=None):
        penta_kill_list = self.database.get_penta_kill_game_id(self.patch.version, game_date)
        return penta_kill_list

    def run_pick_rate(self, game_date=None):
        """
        픽률이 하위 10프로인 챔피언을 픽한 경우 -> 이긴경우
        """
        position_champions = self.database.get_all_position_pick_rate(self.patch.version)
        match_info = self.database.get_all_data_without_team(self.patch.version, game_date)
        unusual_picks = []
        for index, row in match_info.iterrows():
            position = row['position'].lower()
            name_us = row['name_us']
            result = row['result']
            champion = position_champions[position]['name_us_list'].get(name_us, None)
            # 라인에 맞지 않는 챔피언, 패배한 경우
            if champion is None or result == 0:
                continue
            name_kr = champion.get("name_kr")
            pick_rate = champion.get("pick_rate")

            pick_info = {
                'gameid': row['gameid'],
                'league': row['league'],
                'set': row['game'],
                'result': row['result'],
                'playername': row['playername'],
                'team': row['teamname'],
                'position': position,
                'name_us': name_us,
                'name_kr': name_kr,
                'pick_rate': pick_rate,
                'issue_type': []
            }
            if name_us in position_champions[position]['low_pickrate_champions']:
                pick_info['issue_type'].append(f'낮은 픽률 {pick_rate}')

            # 문제가 있는 경우에만 결과 리스트에 추가
            if pick_info['issue_type']:
                unusual_picks.append(pick_info)
        # if unusual_picks:
        #     print("\n비정상적인 챔피언 선택 분석:")
        #     print("=" * 50)
        #     for pick in unusual_picks:
        #         print(f"게임 ID: {pick['gameid']}")
        #         print(f"리그: {pick['league']}")
        #         print(f"세트: {pick['set']}")
        #         print(f"결과: {pick['result']}")
        #         print(f"플레이어: {pick['player']} ({pick['team']})")
        #         print(f"포지션: {pick['position']}")
        #         print(f"선택한 챔피언: {pick['name_us']}")
        #         print(f"특이사항: {', '.join(pick['issue_type'])}")
        #         print("-" * 50)
        # else:
        #     print("모든 챔피언 선택이 일반적입니다.")
        return unusual_picks

    # 모든 매치 데이터에서 IF
    def run_match_info(self):
        match_df = self.database.get_oracle_elixirs_all_team_info()
        features = ['gamelength','result','kills','deaths','assists','team_kpm','ckpm','damagetochampions','dpm','damagetakenperminute','visionscore','totalgold','earned_gpm','gspd']
        x = match_df[features].copy()
        scaler = MinMaxScaler()
        x_scaled = scaler.fit_transform(x)
        isolation_forest = IsolationForest(contamination=0.1, random_state=42, n_estimators=200)
        outliers = isolation_forest.fit_predict(x_scaled)
        anomaly_score = -isolation_forest.score_samples(x_scaled)

        result = match_df.copy()

        result['is_outlier'] = False
        result.loc[outliers == -1, 'is_outlier'] = True
        print(result[result['is_outlier'] == False])

    def update_performance_score(self):
        """
        승률, 픽률, 밴률, 챔피언 티어 기반 performance score하위 10개 챔피언 탐지
        그래도 같은 라인 챔피언을 선택한 경우임
        완전 말도 안되는 챔피언 픽이 아닌 구린 챔피언을 픽한 경우를 나타냄
        패치 버전 최신으로 데이터를 가져옴
        - 완전 말도 안되는 챔피언 픽 탐지가 필요한 경우
            1. 다른 라인 챔피언을 선택한 경우,
            2. 다른 라인 챔피언 + performance score 가 구린 경우
        """
        for line in self.line_list:
            df = self.database.get_champion_score_by_line(line, self.patch.version)
            features = ['pick_rate', 'win_rate', 'ban_rate']
            X = df[features].copy()
            performance_score = (
                    X['pick_rate'] +
                    X['win_rate'] +
                    X['ban_rate']
            )
            median_score = performance_score.median()
            weak_idx = performance_score < median_score
            X_weak = X[weak_idx]

            scaler = MinMaxScaler()
            X_scaled = scaler.fit_transform(X_weak)
            iso_forest = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100,
            )
            outliers = iso_forest.fit_predict(X_scaled)
            anomaly_score = -iso_forest.score_samples(X_scaled)

            result = df.copy()
            result['is_outlier'] = False
            result['performance_score'] = performance_score
            is_outlier_mask = outliers == -1
            result.loc[weak_idx,'is_outlier'] = is_outlier_mask
            result.loc[weak_idx,'anomaly_score'] = anomaly_score

            self.draw_performance_scatter(line, result)
            self.database.insert_performance_score(line, result)


    def draw_performance_scatter(self, line, result):
        plt.figure(figsize=(10, 6))
        plt.rc('font', family='Malgun Gothic')
        plt.scatter(
            result[~result['is_outlier']]['performance_score'],
            result[~result['is_outlier']]['anomaly_score'],
            c='blue',
            label='일반',
            alpha=0.6
        )
        top_outliers = result[result['is_outlier']].nlargest(10, 'anomaly_score')
        plt.scatter(
            top_outliers['performance_score'],
            top_outliers['anomaly_score'],
            c='red',
            label='이상치',
            alpha=0.6
        )
        for idx, row in top_outliers.iterrows():
            plt.annotate(
                row['name_kr'],
                (row['performance_score'], row['anomaly_score']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9,
                alpha=0.8
            )
        plt.xlabel('Performance Score (픽률, 승률, 밴률의 종합 점수)')
        plt.ylabel('이상치 점수')
        today_date = datetime.today().date().strftime("%y_%m_%d")
        plt.title(f'Performance Score 하위 10% 이상치 챔피언, 라인:{line}, 날짜:{today_date}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        output_path = self.output_dir / 'PerformanceScore' / today_date
        output_path.mkdir(exist_ok=True, parents=True)
        plt.savefig(output_path/ f'{line}.png',
                    bbox_inches='tight',
                    dpi=300,
                    facecolor='white')
        plt.close()

    def run_unmatch_line(self, game_date=None):
        champion_dict_by_line = self.database.get_all_champion_list(self.patch.version)
        match_info = self.database.get_all_data_without_team(self.patch.version, game_date)
        off_position_picks = []
        for index, row in match_info.iterrows():
            line = row['position'].lower()
            name_us = row['name_us']
            if name_us not in champion_dict_by_line[line]:
                off_position_picks.append({
                    'gameid': row['gameid'],
                    'playername': row['playername'],
                    'team': row['teamname'],
                    'line': line,
                    'name_us': name_us
                })
        return off_position_picks
