import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from adjustText import adjust_text
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path


class ChampionDetection:

    def __init__(self, database):
        self.database = database
        self.output_dir = Path(__file__).parent.parent / 'PltOutput' / 'PerformanceScore' / datetime.today().date().strftime("%y_%m_%d")
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def isolation_forest(self):
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

        self.draw_scatter(result,f"top")
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

    def draw_scatter(self, result, title):
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
        plt.xlabel('Performance Score (픽률, 승률, 밴률, 티어)')
        plt.ylabel('이상치 점수')
        plt.title('Performance Score 기반 챔피언 이상치 탐지 10개')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(self.output_dir/f'{title}.png',
                    bbox_inches='tight',
                    dpi=300,
                    facecolor='white')
        plt.close()
