import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path


class ChampionDetection:

    def __init__(self, database, anomaly_info):
        self.database = database
        self.anomaly_info = anomaly_info
        self.today_date = datetime.today().date().strftime("%y_%m_%d")
        self.output_dir = Path(__file__).parent.parent / 'PltOutput' / 'PerformanceScore' / self.today_date
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.patch = self.set_patch_version(anomaly_info)
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

    def run_multiple_choice(self):
        
        pass

    def run_pick_rate(self):
        position_champions = self.database.get_pick_rate_info(self.patch)
        match_info = self.database.get_match_info(self.patch)
        unusual_picks = []
        for index, row in match_info.iterrows():
            position = row['position'].lower()
            champion = row['champion']

            pick_info = {
                'gameid': row['gameid'],
                'player': row['playername'],
                'team': row['teamname'],
                'position': position,
                'champion': champion,
                'issue_type': []  # 문제가 되는 이유를 저장할 리스트
            }

            # 1. 해당 포지션의 챔피언 풀에 없는 경우
            if champion not in position_champions[position]['champions']:
                pick_info['issue_type'].append('오프 포지션')

            # 2. 픽률이 하위 10% 이하인 경우
            elif champion in position_champions[position]['low_pickrate_champions']:
                pick_info['issue_type'].append('낮은 픽률')

            # 문제가 있는 경우에만 결과 리스트에 추가
            if pick_info['issue_type']:
                unusual_picks.append(pick_info)

        # 결과 출력
        if unusual_picks:
            print("\n비정상적인 챔피언 선택 분석:")
            print("=" * 50)
            for pick in unusual_picks:
                print(f"게임 ID: {pick['gameid']}")
                print(f"플레이어: {pick['player']} ({pick['team']})")
                print(f"포지션: {pick['position']}")
                print(f"선택한 챔피언: {pick['champion']}")
                print(f"특이사항: {', '.join(pick['issue_type'])}")
                print("-" * 50)
        else:
            print("모든 챔피언 선택이 일반적입니다.")
        pass

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
            features = ['pick_rate', 'win_rate', 'ban_rate', 'champion_tier']
            X = df[features].copy()
            performance_score = (
                    X['pick_rate'] * 0.3 +
                    X['win_rate'] * 0.3 +
                    X['ban_rate'] * 0.2 +
                    (1 / X['champion_tier']) * 0.2
            )

            median_score = performance_score.median()
            weak_idx = performance_score < median_score
            X_weak = X[weak_idx]

            scaler = MinMaxScaler()
            X_scaled = scaler.fit_transform(X_weak)
            iso_forest = IsolationForest(
                contamination=0.2,
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
        plt.xlabel('Performance Score (픽률, 승률, 밴률, 티어의 종합 점수)')
        plt.ylabel('이상치 점수')
        plt.title(f'Performance Score 하위 10 이상치 챔피언, 라인:{line}, 날짜:{self.today_date}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(self.output_dir/f'{line}.png',
                    bbox_inches='tight',
                    dpi=300,
                    facecolor='white')
        plt.close()

    def find_unmatch_line(self):
        champion_dict_by_line = self.database.get_champion_name_by_line(self.patch)
        match_info = self.database.get_match_info(self.patch)

        off_position_picks = []
        for index, row in match_info.iterrows():
            line = row['position'].lower()
            champion = row['champion']
            if champion not in champion_dict_by_line[line]:
                off_position_picks.append({
                    'gameid': row['gameid'],
                    'player': row['playername'],
                    'team': row['teamname'],
                    'line': line,
                    'champion': champion
                })

        if off_position_picks:
            print("비정상적인 포지션 픽:")
            for pick in off_position_picks:
                print(f"게임 ID: {pick['gameid']}")
                print(f"플레이어: {pick['player']} ({pick['team']})")
                print(f"포지션: {pick['line']}")
                print(f"선택한 챔피언: {pick['champion']}")
                print("---")
        else:
            print("모든 챔피언이 정상적인 포지션에서 선택되었습니다.")

