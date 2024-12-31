from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path


class ChampionDetection:

    def __init__(self, database):
        self.database = database
        self.today_date = datetime.today().date().strftime("%y_%m_%d")
        self.output_dir = Path(__file__).parent.parent / 'PltOutput' / 'PerformanceScore' / self.today_date
        self.output_dir.mkdir(exist_ok=True, parents=True)


    def performance_score(self):
        """
        승률, 픽률, 밴률, 챔피언 티어 기반 performance score하위 10개 챔피언 탐지
        그래도 같은 라인 챔피언을 선택한 경우임
        완전 말도 안되는 챔피언 픽이 아닌 구린 챔피언을 픽한 경우를 나타냄
        완전 말도 안되는 챔피언 픽 탐지가 필요한 경우
            1. 다른 라인 챔피언을 선택한 경우,
            2. 다른 라인 챔피언 + performance score 가 구린 경우
        """
        df = self.database.get_champion_df("top")
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

        self.draw_performance_scatter(result, "top")
        weak_outliers = result[result['is_outlier']].nlargest(10, 'anomaly_score')
        print("\n=== 성능이 특히 낮은 챔피언 ===")
        for _, row in weak_outliers.iterrows():
            print(f"{row['name_kr']}:")
            print(f"  픽률: {row['pick_rate']:.2f}%")
            print(f"  승률: {row['win_rate']:.2f}%")
            print(f"  밴률: {row['ban_rate']:.2f}%")
            print(f"  티어: {row['champion_tier']}")
            print(f"  성능 점수: {row['performance_score']:.2f}")
            print(f"  이상치 점수: {row['anomaly_score']:.2f}")
            print()
        return weak_outliers

    def draw_performance_scatter(self, result, line):
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
