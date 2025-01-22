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

    def __init__(self, database, meta_data):
        self.database = database
        self.anomaly_info = meta_data.anomaly_info
        self.today_date = datetime.today().date().strftime("%y_%m_%d")
        self.output_dir = Path(__file__).parent.parent / 'PltOutput'
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.patch = self.set_patch_version(self.anomaly_info)
        self.line_list = ["top","mid","jungle","bottom","support"]

    def set_patch_version(self, anomaly_info):
        if anomaly_info['patch'] == "latest":
            return self.database.get_latest_patch()
        else:
            return anomaly_info['patch']

    def run_performance_score(self):
        self.update_performance_score()
        match_info = self.database.detect_by_performance_score(self.patch)
        print(match_info)

    def run_unmatch_line(self):
        self.find_unmatch_line()

    def run_two_bottom_choice(self):
        bottom_champions = self.database.get_only_bottom_champion(self.patch)
        match_info = self.database.get_player_info(self.patch)
        multi_adc_games = []

        for (game_id, side), team_picks in match_info.groupby(['gameid', 'side']):
            adc_picks = [pick for pick in team_picks.itertuples()
                         if pick.name_us in bottom_champions]

            if len(adc_picks) >= 2:
                game_info = {
                    'game_id': game_id,
                    'team_side': side,
                    'team_name': adc_picks[0].teamname,
                    'adc_picks': []
                }

                for pick in adc_picks:
                    game_info['adc_picks'].append({
                        'champion': pick.name_us,
                        'position': pick.position,
                        'player': pick.playername
                    })

                multi_adc_games.append(game_info)

        if multi_adc_games:
            print("\n원거리 딜러 다중 픽 게임 분석:")
            print("=" * 60)
            for game in multi_adc_games:
                print(f"게임 ID: {game['game_id']}")
                print(f"팀 사이드: {game['team_side']}")
                print(f"팀 이름: {game['team_name']}")
                print("\n원거리 딜러 픽:")
                for pick in game['adc_picks']:
                    print(f"- {pick['champion']} ({pick['position']} 포지션, 플레이어: {pick['player']})")
                print("----------------------------------------------")
        else:
            print("원거리 딜러를 2개 이상 픽한 게임이 없습니다.")

    def run_pick_rate(self):
        """
        픽률이 하위 10프로인 챔피언을 픽한 경우
        """
        position_champions = self.database.get_pick_rate_info(self.patch)
        match_info = self.database.get_player_info(self.patch)
        unusual_picks = []
        for index, row in match_info.iterrows():
            position = row['position'].lower()
            name_us = row['name_us']
            champion = position_champions[position]['name_us_list'].get(name_us, None)
            #오프 포지션임
            if champion is None:
                continue
            name_kr = champion.get("name_kr")
            pick_rate = champion.get("pick_rate")

            pick_info = {
                'gameid': row['gameid'],
                'league': row['league'],
                'set': row['game'],
                'result': row['result'],
                'player': row['playername'],
                'team': row['teamname'],
                'position': position,
                'name_us': name_us,
                'name_kr': name_kr,
                'pick_rate': pick_rate,
                'issue_type': []
            }
            # 2. 픽률이 하위 10% 이하인 경우
            if name_us in position_champions[position]['low_pickrate_champions']:
                pick_info['issue_type'].append(f'낮은 픽률 {pick_rate}')

            # 문제가 있는 경우에만 결과 리스트에 추가
            if pick_info['issue_type']:
                unusual_picks.append(pick_info)
        if unusual_picks:
            print("\n비정상적인 챔피언 선택 분석:")
            print("=" * 50)
            for pick in unusual_picks:
                print(f"게임 ID: {pick['gameid']}")
                print(f"리그: {pick['league']}")
                print(f"세트: {pick['set']}")
                print(f"결과: {pick['result']}")
                print(f"플레이어: {pick['player']} ({pick['team']})")
                print(f"포지션: {pick['position']}")
                print(f"선택한 챔피언: {pick['name_us']}")
                print(f"특이사항: {', '.join(pick['issue_type'])}")
                print("-" * 50)
        else:
            print("모든 챔피언 선택이 일반적입니다.")

    # 모든 매치 데이터에서 IF
    def run_match_info(self):
        match_df = self.database.get_team_info()
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
            df = self.database.get_champion_score(line, self.patch)
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
        plt.title(f'Performance Score 하위 10% 이상치 챔피언, 라인:{line}, 날짜:{self.today_date}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        output_path = self.output_dir / 'PerformanceScore' / self.today_date
        output_path.mkdir(exist_ok=True, parents=True)
        plt.savefig(output_path/ f'{line}.png',
                    bbox_inches='tight',
                    dpi=300,
                    facecolor='white')
        plt.close()

    def find_unmatch_line(self):
        champion_dict_by_line = self.database.get_champion_name_by_line(self.patch)
        match_info = self.database.get_player_info(self.patch)

        off_position_picks = []
        for index, row in match_info.iterrows():
            line = row['position'].lower()
            name_us = row['name_us']
            if name_us not in champion_dict_by_line[line]:
                off_position_picks.append({
                    'gameid': row['gameid'],
                    'player': row['playername'],
                    'team': row['teamname'],
                    'line': line,
                    'name_us': name_us
                })

        if off_position_picks:
            print("비정상적인 포지션 픽:")
            for pick in off_position_picks:
                print(f"게임 ID: {pick['gameid']}")
                print(f"플레이어: {pick['player']} ({pick['team']})")
                print(f"포지션: {pick['line']}")
                print(f"선택한 챔피언: {pick['name_us']}")
                print("---")
        else:
            print("모든 챔피언이 정상적인 포지션에서 선택되었습니다.")

    def get_game_mvp(self, game_id):
        game_df = self.database.get_mvp_base_data(game_id)
        if game_df is None or game_df.empty:
            return None

        mvp_scores = self.calculate_mvp_score(game_df)
        print(mvp_scores[['playername','champion','position','mvp_score']])
        mvp_player = mvp_scores.iloc[0]

        print(f"\nMVP of Game {game_id}")
        print(f"Player: {mvp_player['playername']}")
        print(f"Champion: {mvp_player['champion']}")
        print(f"Position: {mvp_player['position']}")
        print(f"Total Score: {mvp_player['mvp_score']:.2f}")
        print("\nScore Breakdown:")
        for category, score in mvp_player['score_breakdown'].items():
            print(f"{category}: {score:.2f}")
        return mvp_player

    def calculate_mvp_score(self, df):
        # 포지션별 가중치 정의
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

            # 전투력 점수 계산
            combat_score = (
                                   (player['normalized_kills'] * 0.15) +
                                   ((1 - player['normalized_deaths']) * 0.15) +
                                   (player['normalized_assists'] * 0.1) +
                                   (player['normalized_damageshare'] * 0.4) +
                                   (player['normalized_damagemitigatedperminute'] * 0.2)
                           ) * weights['combat']

            # 경제력 점수 계산
            economy_score = (
                                    (player['normalized_cspm'] * 0.4) +
                                    (player['normalized_earnedgoldshare'] * 0.6)
                            ) * weights['economy']

            # 시야 점수 계산
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

            # 점수 세부 내역 저장
            score_breakdown = {
                'combat': combat_score,
                'economy': economy_score,
                'vision': vision_score,
                'objective': objective_score,
                'laning': laning_score
            }

            # 최종 MVP 점수 계산
            final_score = sum(score_breakdown.values())

            # 승리 팀 보너스
            if player['result']:
                final_score *= 1.1

            mvp_scores.append({
                'playername': player['playername'],
                'champion': player['champion'],
                'position': position,
                'mvp_score': final_score,
                'score_breakdown': score_breakdown,
                'kills': player['kills'],
                'deaths': player['deaths'],
                'assists': player['assists'],
                'damage_share': player['damageshare'],
                'vision_score': player['visionscore'],
                'result': player['result']
            })

        mvp_df = pd.DataFrame(mvp_scores)
        ideal_max_score = 5.5
        mvp_df['mvp_score'] = mvp_df['mvp_score'] / ideal_max_score
        scaling_factor = 10.0
        power_factor = 1.2
        mvp_df['mvp_score'] = (mvp_df['mvp_score'] * power_factor) * scaling_factor
        mvp_df['mvp_score'] = mvp_df['mvp_score'].clip(0, 10)
        mvp_df = mvp_df.sort_values('mvp_score', ascending=False)

        return mvp_df

