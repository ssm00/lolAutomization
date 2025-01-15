import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import matplotlib.pyplot as plt
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

    def __init__(self, database, anomaly_info):
        self.database = database
        self.anomaly_info = anomaly_info
        self.today_date = datetime.today().date().strftime("%y_%m_%d")
        self.output_dir = Path(__file__).parent.parent / 'PltOutput'
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
        self.draw_pick_rates_opal(unusual_picks)
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

    def draw_pick_rates(self, unusual_picks):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        # 전체적인 스타일 설정
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')
        for pick in unusual_picks:
            position = pick['position']
            unusual_champion = pick['name_us']
            unusual_pick_rate = pick['pick_rate']

            champ_data = position_champions[position]['name_us_list']
            df = pd.DataFrame([
                {'name_us':name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
                for name_us, champ_info in champ_data.items()
            ])
            df_filtered = df[df['name_us'] != unusual_champion]
            top_9 = df_filtered.nlargest(9, 'Pick Rate')
            unusual_data = pd.DataFrame([{
                'name_us': unusual_champion,
                'name_kr': champ_data[unusual_champion]['name_kr'],
                'Pick Rate': unusual_pick_rate
            }])

            final_df = pd.concat([top_9, unusual_data])

            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10.8, 10.8))

            # 배경 스타일 설정
            ax.set_facecolor('#F0F0F0')
            fig.patch.set_facecolor('white')

            # 바 그래프 생성 - 그라데이션 효과 추가
            colors = ['#3498db' if x != unusual_champion else '#e74c3c' for x in final_df['name_us']]
            bars = ax.bar(
                range(len(final_df)),
                final_df['Pick Rate'],
                color=colors,
                edgecolor='black',
                linewidth=1,
                alpha=0.7,
                width=0.7
            )

            # 그리드 설정
            ax.grid(True, axis='y', linestyle='--', alpha=0.7, zorder=0)
            ax.set_axisbelow(True)

            # x축 레이블 설정
            plt.xticks(
                range(len(final_df)),
                final_df['name_kr'],
                rotation=45,
                ha='right',
                fontsize=11,
                fontweight='bold'
            )

            # y축 범위 설정 - 여유 공간 추가
            ax.set_ylim(0, max(final_df['Pick Rate']) * 1.2)
            position_kr_map = {'jungle':'정글', 'top':'탑','bottom':'바텀','mid':'미드','support':'서포터'}
            position_kr = position_kr_map[position]
            # 제목 및 레이블 설정
            plt.title(f'{position_kr} 챔피언별 픽률   패치 버전:{self.patch}',
                      pad=20,
                      size=16,
                      fontweight='bold')
            #plt.xlabel('Champions', size=12, labelpad=10)
            #plt.ylabel('Pick Rate (%)', size=12, labelpad=10)

            # threshold 선 추가 - 스타일 개선
            threshold = position_champions[position]['low_pickrate_threshold']
            ax.axhline(
                y=threshold,
                color='#e74c3c',
                linestyle='--',
                alpha=0.5,
                linewidth=2,
                label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
            )

            # 픽률 수치 표시 개선
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:.1f}%',
                    ha='center',
                    va='bottom',
                    fontsize=10,
                    fontweight='bold'
                )


            # 테두리 추가
            for spine in ax.spines.values():
                spine.set_edgecolor('#CCCCCC')

            plt.tight_layout()

            # 높은 해상도로 저장
            plt.savefig(
                f'pick_rate_analysis_{position}_{unusual_champion}_{self.patch}.png',
                bbox_inches='tight',
                dpi=300,
                facecolor=fig.get_facecolor(),
                edgecolor='none',
                transparent=True
            )
            plt.close()

    def draw_pick_rates_opal(self, unusual_picks):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        # 전체적인 스타일 설정
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')
        for pick in unusual_picks:
            position = pick['position']
            unusual_champion = pick['name_us']
            unusual_pick_rate = pick['pick_rate']

            champ_data = position_champions[position]['name_us_list']
            df = pd.DataFrame([
                {'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
                for name_us, champ_info in champ_data.items()
            ])
            df_filtered = df[df['name_us'] != unusual_champion]
            top_9 = df_filtered.nlargest(9, 'Pick Rate')
            unusual_data = pd.DataFrame([{
                'name_us': unusual_champion,
                'name_kr': champ_data[unusual_champion]['name_kr'],
                'Pick Rate': unusual_pick_rate
            }])

            final_df = pd.concat([top_9, unusual_data])

            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10.8, 10.8))

            # 배경 투명 설정
            ax.set_facecolor('none')
            fig.patch.set_facecolor('none')

            # 바 그래프 생성
            colors = ['#3498db' if x != unusual_champion else '#e74c3c' for x in final_df['name_us']]
            bars = ax.bar(
                range(len(final_df)),
                final_df['Pick Rate'],
                color=colors,
                edgecolor='black',
                linewidth=1,
                alpha=0.7,
                width=0.7
            )

            # 그리드 설정
            ax.grid(True, axis='y', linestyle='--', alpha=0.7, zorder=0)
            ax.set_axisbelow(True)

            # x축 레이블 설정 - 흰색으로 변경
            plt.xticks(
                range(len(final_df)),
                final_df['name_kr'],
                rotation=45,
                ha='right',
                fontsize=11,
                fontweight='bold',
                color='white'  # 텍스트 색상을 흰색으로
            )

            # y축 눈금 색상 변경
            ax.tick_params(axis='y', colors='white')

            # y축 범위 설정
            ax.set_ylim(0, max(final_df['Pick Rate']) * 1.2)

            position_kr_map = {'jungle': '정글', 'top': '탑', 'bottom': '바텀', 'mid': '미드', 'support': '서포터'}
            position_kr = position_kr_map[position]

            # 제목 설정 - 흰색으로 변경
            plt.title(f'{position_kr} 챔피언별 픽률   패치 버전:{self.patch}',
                      pad=20,
                      size=16,
                      fontweight='bold',
                      color='white')  # 제목 색상을 흰색으로

            # threshold 선 추가
            threshold = position_champions[position]['low_pickrate_threshold']
            ax.axhline(
                y=threshold,
                color='#e74c3c',
                linestyle='--',
                alpha=0.5,
                linewidth=2,
                label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
            )

            # 픽률 수치 표시 - 흰색으로 변경
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:.1f}%',
                    ha='center',
                    va='bottom',
                    fontsize=10,
                    fontweight='bold',
                    color='white'  # 텍스트 색상을 흰색으로
                )

            plt.tight_layout()

            # 투명 배경으로 저장
            plt.savefig(
                f'pick_rate_analysis_{position}_{unusual_champion}_{self.patch}.png',
                bbox_inches='tight',
                dpi=300,
                transparent=True
            )
            plt.close()

    def draw_pick_rates_horizontal(self, unusual_picks):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')

        for pick in unusual_picks:
            position = pick['position']
            unusual_champion = pick['name_us']
            unusual_pick_rate = pick['pick_rate']

            champ_data = position_champions[position]['name_us_list']
            df = pd.DataFrame([
                {'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
                for name_us, champ_info in champ_data.items()
            ])
            df_filtered = df[df['name_us'] != unusual_champion]
            top_9 = df_filtered.nlargest(9, 'Pick Rate')
            unusual_data = pd.DataFrame([{
                'name_us': unusual_champion,
                'name_kr': champ_data[unusual_champion]['name_kr'],
                'Pick Rate': unusual_pick_rate
            }])

            final_df = pd.concat([top_9, unusual_data])
            final_df = final_df.sort_values('Pick Rate', ascending=True)  # 오름차순으로 변경

            fig, ax = plt.subplots(figsize=(5.9, 10.8))

            ax.set_facecolor('#F0F0F0')
            fig.patch.set_facecolor('white')

            colors = ['#3498db' if x != unusual_champion else '#e74c3c' for x in final_df['name_us']]
            bars = ax.barh(
                range(len(final_df)),  # 정상 순서 사용
                final_df['Pick Rate'],
                color=colors,
                edgecolor='black',
                linewidth=1,
                alpha=0.7,
                height=0.7
            )

            ax.grid(True, axis='x', linestyle='--', alpha=0.7, zorder=0)
            ax.set_axisbelow(True)

            plt.yticks(
                range(len(final_df)),
                final_df['name_kr'],
                fontsize=11,
                fontweight='bold'
            )

            ax.set_xlim(0, max(final_df['Pick Rate']) * 1.2)

            position_kr_map = {'jungle': '정글', 'top': '탑', 'bottom': '바텀', 'mid': '미드', 'support': '서포터'}
            position_kr = position_kr_map[position]

            plt.title(f'{position_kr} 챔피언별 픽률   패치 버전:{self.patch}',
                      pad=20,
                      size=16,
                      fontweight='bold')

            threshold = position_champions[position]['low_pickrate_threshold']
            ax.axvline(
                x=threshold,
                color='#e74c3c',
                linestyle='--',
                alpha=0.5,
                linewidth=2,
                label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
            )

            for bar in bars:
                width = bar.get_width()
                ax.text(
                    width + (max(final_df['Pick Rate']) * 0.02),
                    bar.get_y() + bar.get_height() / 2.,
                    f'{width:.1f}%',
                    ha='left',
                    va='center',
                    fontsize=10,
                    fontweight='bold'
                )

            for spine in ax.spines.values():
                spine.set_edgecolor('#CCCCCC')

            plt.tight_layout()

            plt.savefig(
                f'pick_rate_analysis_{position}_{unusual_champion}_{self.patch}.png',
                bbox_inches='tight',
                dpi=300,
                facecolor=fig.get_facecolor(),
                edgecolor='none'
            )
            plt.close()

    def draw_pick_rates_horizontal_opal(self, unusual_picks):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')

        for pick in unusual_picks:
            position = pick['position']
            unusual_champion = pick['name_us']
            unusual_pick_rate = pick['pick_rate']

            champ_data = position_champions[position]['name_us_list']
            df = pd.DataFrame([
                {'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
                for name_us, champ_info in champ_data.items()
            ])
            df_filtered = df[df['name_us'] != unusual_champion]
            top_9 = df_filtered.nlargest(9, 'Pick Rate')
            unusual_data = pd.DataFrame([{
                'name_us': unusual_champion,
                'name_kr': champ_data[unusual_champion]['name_kr'],
                'Pick Rate': unusual_pick_rate
            }])

            final_df = pd.concat([top_9, unusual_data])
            final_df = final_df.sort_values('Pick Rate', ascending=True)

            fig, ax = plt.subplots(figsize=(5.9, 10.8))

            ax.set_facecolor('#F0F0F0')

            fig.patch.set_facecolor('white')

            colors = ['#3498db' if x != unusual_champion else '#e74c3c' for x in final_df['name_us']]
            bars = ax.barh(
                range(len(final_df)),
                final_df['Pick Rate'],
                color=colors,
                edgecolor='black',
                linewidth=1,
                alpha=0.7,
                height=0.7
            )

            ax.grid(True, axis='x', linestyle='--', alpha=0.7, zorder=0)
            ax.set_axisbelow(True)


            plt.yticks(
                range(len(final_df)),
                final_df['name_kr'],
                fontsize=11,
                fontweight='bold'
            )

            ax.set_xlim(0, max(final_df['Pick Rate']) * 1.2)

            position_kr_map = {'jungle': '정글', 'top': '탑', 'bottom': '바텀', 'mid': '미드', 'support': '서포터'}
            position_kr = position_kr_map[position]

            plt.title(f'{position_kr} 챔피언별 픽률   패치 버전:{self.patch}',
                      pad=20,
                      size=16,
                      fontweight='bold')

            threshold = position_champions[position]['low_pickrate_threshold']
            ax.axvline(
                x=threshold,
                color='#e74c3c',
                linestyle='--',
                alpha=0.5,
                linewidth=2,
                label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
            )

            # 텍스트에 약간의 테두리 효과 추가하여 가독성 향상
            for bar in bars:
                width = bar.get_width()
                text = ax.text(
                    width + (max(final_df['Pick Rate']) * 0.02),
                    bar.get_y() + bar.get_height() / 2.,
                    f'{width:.1f}%',
                    ha='left',
                    va='center',
                    fontsize=10,
                    fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1)  # 텍스트 배경 추가
                )

            for spine in ax.spines.values():
                spine.set_edgecolor('#CCCCCC')

            plt.tight_layout()

            plt.savefig(
                f'pick_rate_analysis_{position}_{unusual_champion}_{self.patch}.png',
                bbox_inches='tight',
                dpi=300,
                transparent=True  # 저장 시 배경 투명하게
            )
            plt.close()

    def draw_pick_rates_horizontal_opal_1(self, unusual_picks):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')

        for pick in unusual_picks:
            position = pick['position']
            unusual_champion = pick['name_us']
            unusual_pick_rate = pick['pick_rate']

            champ_data = position_champions[position]['name_us_list']
            df = pd.DataFrame([
                {'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
                for name_us, champ_info in champ_data.items()
            ])
            df_filtered = df[df['name_us'] != unusual_champion]
            top_9 = df_filtered.nlargest(9, 'Pick Rate')
            unusual_data = pd.DataFrame([{
                'name_us': unusual_champion,
                'name_kr': champ_data[unusual_champion]['name_kr'],
                'Pick Rate': unusual_pick_rate
            }])

            final_df = pd.concat([top_9, unusual_data])
            final_df = final_df.sort_values('Pick Rate', ascending=True)

            fig, ax = plt.subplots(figsize=(5.9, 10.8))

            ax.set_facecolor('#F0F0F0')
            fig.patch.set_facecolor('white')

            colors = ['#3498db' if x != unusual_champion else '#e74c3c' for x in final_df['name_us']]
            bars = ax.barh(
                range(len(final_df)),
                final_df['Pick Rate'],
                color=colors,
                edgecolor='black',
                linewidth=1,
                alpha=0.7,
                height=0.7
            )

            ax.grid(True, axis='x', linestyle='--', alpha=0.7, zorder=0)
            ax.set_axisbelow(True)

            # y축 레이블(챔피언 이름) 색상 변경
            plt.yticks(
                range(len(final_df)),
                final_df['name_kr'],
                fontsize=11,
                fontweight='bold',
                color='white'  # 텍스트 색상을 흰색으로
            )

            # x축 눈금 색상 변경
            ax.tick_params(axis='x', colors='white')

            ax.set_xlim(0, max(final_df['Pick Rate']) * 1.2)

            position_kr_map = {'jungle': '정글', 'top': '탑', 'bottom': '바텀', 'mid': '미드', 'support': '서포터'}
            position_kr = position_kr_map[position]

            # 제목 색상 변경
            plt.title(f'{position_kr} 챔피언별 픽률   패치 버전:{self.patch}',
                      pad=20,
                      size=16,
                      fontweight='bold',
                      color='white')  # 제목 색상을 흰색으로

            threshold = position_champions[position]['low_pickrate_threshold']
            ax.axvline(
                x=threshold,
                color='#e74c3c',
                linestyle='--',
                alpha=0.5,
                linewidth=2,
                label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
            )

            # 픽률 텍스트 색상 변경 (배경 제거)
            for bar in bars:
                width = bar.get_width()
                ax.text(
                    width + (max(final_df['Pick Rate']) * 0.02),
                    bar.get_y() + bar.get_height() / 2.,
                    f'{width:.1f}%',
                    ha='left',
                    va='center',
                    fontsize=10,
                    fontweight='bold',
                    color='white'  # 텍스트 색상을 흰색으로
                )

            for spine in ax.spines.values():
                spine.set_edgecolor('#CCCCCC')

            plt.tight_layout()

            plt.savefig(
                f'pick_rate_analysis_{position}_{unusual_champion}_{self.patch}.png',
                bbox_inches='tight',
                dpi=300,
                transparent=True
            )
            plt.close()

    def draw_gold_series(self, game_id, player_name, line):
        plt.style.use('seaborn-v0_8-dark')
        plt.rcParams['font.family'] = 'NanumGothic'  # 한글 폰트 설정
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
        plt.rcParams['text.color'] = 'white'  # 기본 텍스트 색상
        plt.rcParams['axes.labelcolor'] = 'white'  # 축 레이블 색상
        plt.rcParams['xtick.color'] = 'white'  # x축 눈금 색상
        plt.rcParams['ytick.color'] = 'white'  # y축 눈금 색상

        # 데이터 준비
        series_info = self.database.get_match_series_info(game_id, player_name)
        champion_name = series_info["name_us"][0]
        opp_champion_name = self.database.get_oppnent_player_name(game_id, player_name).get("name_us")
        select_columns = [
            "goldat10", "opp_goldat10", "golddiffat10",
            "goldat15", "opp_goldat15", "golddiffat15",
            "goldat20", "opp_goldat20", "golddiffat20",
            "goldat25", "opp_goldat25", "golddiffat25"
        ]
        df = series_info[select_columns].copy()

        # 시간대별 데이터 추출
        time_points = [10, 15, 20, 25]
        player_gold = []
        opponent_gold = []
        valid_times = []

        for time in time_points:
            gold_val = df[f'goldat{time}'].iloc[0]
            opp_gold_val = df[f'opp_goldat{time}'].iloc[0]

            if pd.notna(gold_val) and pd.notna(opp_gold_val):
                player_gold.append(gold_val / 1000)
                opponent_gold.append(opp_gold_val / 1000)
                valid_times.append(time)

        fig, ax = plt.subplots(figsize=(12, 7), dpi=100)

        # 배경 스타일링
        ax.set_facecolor('#1a1a1a')  # 어두운 배경
        fig.patch.set_facecolor('#1a1a1a')

        # 골드 라인 그리기
        player_line = ax.plot(valid_times, player_gold, '-', color='#1E40AF',
                              linewidth=3, marker='o', markersize=8,
                              label=f'플레이어({champion_name}) 골드')
        opp_line = ax.plot(valid_times, opponent_gold, '-', color='#DC2626',
                           linewidth=3, marker='o', markersize=8,
                           label=f'상대({opp_champion_name}) 골드')

        # 골드 차이 영역 표시
        ax.fill_between(valid_times, player_gold, opponent_gold,
                        where=(np.array(player_gold) >= np.array(opponent_gold)),
                        color='#1E40AF', alpha=0.1)
        ax.fill_between(valid_times, player_gold, opponent_gold,
                        where=(np.array(player_gold) <= np.array(opponent_gold)),
                        color='#DC2626', alpha=0.1)

        # 격자 스타일링
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')

        # 축 레이블 및 제목 설정
        ax.set_title(f'시간대별 골드 획득', pad=20, fontsize=24,
                     fontweight='bold', color='white')
        ax.set_xlabel('게임 시간 (분)', labelpad=10, fontsize=22, color='white')
        ax.set_ylabel('골드 (K)', labelpad=10, fontsize=22, color='white')

        # x축 설정
        ax.set_xticks(valid_times)
        ax.set_xticklabels([f'{t}분' for t in valid_times], fontsize=20, color='white')
        ax.tick_params(axis='y', labelsize=20)

        # y축 범위 설정 (여백 10% 추가)
        all_gold = player_gold + opponent_gold
        min_gold = min(all_gold)
        max_gold = max(all_gold)
        padding = (max_gold - min_gold) * 0.1
        ax.set_ylim(min_gold - padding, max_gold + padding)

        # y축 단위 포맷팅
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x)}K'))

        # 범례 스타일링 - 배경색과 텍스트 색상 조정
        legend = ax.legend(loc='upper left', frameon=True,
                           bbox_to_anchor=(0.02, 0.98),
                           fontsize=20)
        frame = legend.get_frame()
        frame.set_facecolor('#1a1a1a')  # 범례 배경색을 그래프 배경색과 동일하게
        frame.set_edgecolor('white')  # 테두리 색상

        # 범례 텍스트 색상 변경
        for text in legend.get_texts():
            text.set_color('white')

        # 그래프 테두리 제거
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)

        # 데이터 포인트에 값 표시
        for i, (pg, og) in enumerate(zip(player_gold, opponent_gold)):
            ax.annotate(f'{pg:.1f}K', (valid_times[i], pg),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', color='white', fontsize=18)
            ax.annotate(f'{og:.1f}K', (valid_times[i], og),
                        textcoords="offset points", xytext=(0, 10),  # 겹치지 않도록 위치 조정
                        ha='center', color='white', fontsize=18)

        # 레이아웃 조정
        plt.tight_layout()

        output_path = self.output_dir / 'Series' / 'PickRate' / self.today_date
        output_path.mkdir(exist_ok=True, parents=True)

        plt.savefig(
            output_path / f'{game_id}_{player_name}_gold.png',
            bbox_inches='tight',
            dpi=300,
            transparent=True
        )
        plt.close()

    def draw_all_series(self, game_id, player_name):
        # 각 통계 항목별 설정
        metrics_config = {
            "goldat": {
                "title": "시간대별 골드 획득",
                "ylabel": "골드 (K)",
                "format": lambda x: f"{x / 1000:.1f}K",
                "div_factor": 1000,
                "columns": ["goldat", "opp_goldat"]
            },
            "xpat": {
                "title": "시간대별 경험치 획득",
                "ylabel": "경험치",
                "format": lambda x: f"{x:.0f}",
                "div_factor": 1,
                "columns": ["xpat", "opp_xpat"]
            },
            "csat": {
                "title": "시간대별 CS 획득",
                "ylabel": "CS",
                "format": lambda x: f"{x:.0f}",
                "div_factor": 1,
                "columns": ["csat", "opp_csat"]
            },
            "killsat": {
                "title": "시간대별 킬 획득",
                "ylabel": "킬",
                "format": lambda x: f"{x:.0f}",
                "div_factor": 1,
                "columns": ["killsat", "opp_killsat"]
            },
            "assistsat": {
                "title": "시간대별 어시스트 획득",
                "ylabel": "어시스트",
                "format": lambda x: f"{x:.0f}",
                "div_factor": 1,
                "columns": ["assistsat", "opp_assistsat"]
            },
            "deathsat": {
                "title": "시간대별 데스",
                "ylabel": "데스",
                "format": lambda x: f"{x:.0f}",
                "div_factor": 1,
                "columns": ["deathsat", "opp_deathsat"]
            }
        }

        # 기본 스타일 설정
        plt.style.use('seaborn-v0_8-dark')
        plt.rcParams['font.family'] = 'NanumGothic'
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['text.color'] = 'white'
        plt.rcParams['axes.labelcolor'] = 'white'
        plt.rcParams['xtick.color'] = 'white'
        plt.rcParams['ytick.color'] = 'white'

        # 데이터 준비
        series_info = self.database.get_match_series_info(game_id, player_name)
        champion_name = series_info["name_us"][0]
        opp_champion_name = self.database.get_oppnent_player_name(game_id, player_name).get("name_us")

        for metric, config in metrics_config.items():
            self.draw_series(
                game_id=game_id,
                player_name=player_name,
                champion_name=champion_name,
                opp_champion_name=opp_champion_name,
                df=series_info,
                metric=metric,
                config=config
            )

    def draw_series(self, game_id, player_name, champion_name, opp_champion_name, df, metric, config):
        time_points = [10, 15, 20, 25]
        player_values = []
        opponent_values = []
        valid_times = []

        for time in time_points:
            col_name = f"{config['columns'][0]}{time}"
            opp_col_name = f"{config['columns'][1]}{time}"

            val = df[col_name].iloc[0]
            opp_val = df[opp_col_name].iloc[0]

            if pd.notna(val) and pd.notna(opp_val):
                player_values.append(val / config['div_factor'])
                opponent_values.append(opp_val / config['div_factor'])
                valid_times.append(time)

        fig, ax = plt.subplots(figsize=(12, 7), dpi=100)

        # 배경 스타일링
        ax.set_facecolor('#1a1a1a')
        fig.patch.set_facecolor('#1a1a1a')

        # 라인 그리기
        player_line = ax.plot(valid_times, player_values, '-', color='#1E40AF',
                              linewidth=3, marker='o', markersize=8,
                              label=f'({champion_name})')
        opp_line = ax.plot(valid_times, opponent_values, '-', color='#DC2626',
                           linewidth=3, marker='o', markersize=8,
                           label=f'({opp_champion_name})')

        # 차이 영역 표시
        ax.fill_between(valid_times, player_values, opponent_values,
                        where=(np.array(player_values) >= np.array(opponent_values)),
                        color='#1E40AF', alpha=0.1)
        ax.fill_between(valid_times, player_values, opponent_values,
                        where=(np.array(player_values) <= np.array(opponent_values)),
                        color='#DC2626', alpha=0.1)

        # 격자 스타일링
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')

        # 축 레이블 및 제목 설정
        ax.set_title(config['title'], pad=20, fontsize=24, fontweight='bold', color='white')
        ax.set_xlabel('게임 시간 (분)', labelpad=10, fontsize=22, color='white')
        ax.set_ylabel(config['ylabel'], labelpad=10, fontsize=22, color='white')

        # x축 설정
        ax.set_xticks(valid_times)
        ax.set_xticklabels([f'{t}분' for t in valid_times], fontsize=20, color='white')
        ax.tick_params(axis='y', labelsize=20)

        # y축 범위 설정
        all_values = player_values + opponent_values
        min_val = min(all_values)
        max_val = max(all_values)
        padding = (max_val - min_val) * 0.1
        ax.set_ylim(min_val - padding, max_val + padding)

        # 범례 스타일링
        legend = ax.legend(loc='upper left', frameon=True,
                           bbox_to_anchor=(0.02, 0.98),
                           fontsize=20)
        frame = legend.get_frame()
        frame.set_facecolor('#1a1a1a')
        frame.set_edgecolor('white')

        # 범례 텍스트 색상 변경
        for text in legend.get_texts():
            text.set_color('white')

        # 그래프 테두리 제거
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)

        # 데이터 포인트에 값 표시
        for i, (pv, ov) in enumerate(zip(player_values, opponent_values)):
            ax.annotate(config['format'](pv * config['div_factor']),
                        (valid_times[i], pv),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', color='white', fontsize=18)
            ax.annotate(config['format'](ov * config['div_factor']),
                        (valid_times[i], ov),
                        textcoords="offset points", xytext=(0, -20),
                        ha='center', color='white', fontsize=18)

        # 레이아웃 조정
        plt.tight_layout()

        # 저장
        output_path = self.output_dir / 'Series' / 'PickRate' / self.today_date
        output_path.mkdir(exist_ok=True, parents=True)
        plt.savefig(
            output_path / f'{game_id}_{player_name}_{metric}.png',
            bbox_inches='tight',
            dpi=300,
            transparent=True
        )
        plt.close()

    def draw_combined_series(self, game_id, player_name):
        # 기본 스타일 설정
        plt.style.use('seaborn-v0_8-dark')
        plt.rcParams['font.family'] = 'NanumGothic'
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['text.color'] = 'white'
        plt.rcParams['axes.labelcolor'] = 'white'
        plt.rcParams['xtick.color'] = 'white'
        plt.rcParams['ytick.color'] = 'white'

        # 데이터 준비
        series_info = self.database.get_match_series_info(game_id, player_name)
        champion_name = series_info["name_us"][0]
        opp_champion_name = self.database.get_oppnent_player_name(game_id, player_name).get("name_us")

        # KDA 그래프와 경제력 그래프를 각각 그리기
        self.draw_kda_graph(game_id, player_name, champion_name, opp_champion_name, series_info)
        self.draw_economy_graph(game_id, player_name, champion_name, opp_champion_name, series_info)

    def draw_kda_graph(self, game_id, player_name, champion_name, opp_champion_name, series_info):
        time_points = [10, 15, 20, 25]
        metrics = ['kills', 'deaths', 'assists']

        fig, ax = plt.subplots(figsize=(14, 8), dpi=100)
        ax.set_facecolor('#1a1a1a')
        fig.patch.set_facecolor('#1a1a1a')

        colors = {
            'kills': '#4CAF50',  # 초록색
            'deaths': '#DC2626',  # 빨간색
            'assists': '#1E40AF'  # 파란색
        }

        # 각 지표별로 플레이어와 상대방 데이터 플로팅
        for metric in metrics:
            player_values = []
            opponent_values = []
            valid_times = []

            for time in time_points:
                val = series_info[f'{metric}at{time}'].iloc[0]
                opp_val = series_info[f'opp_{metric}at{time}'].iloc[0]

                if pd.notna(val) and pd.notna(opp_val):
                    player_values.append(val)
                    opponent_values.append(opp_val)
                    valid_times.append(time)

            # 실선 스타일로 플레이어 데이터
            ax.plot(valid_times, player_values, '-', color=colors[metric],
                    linewidth=3, marker='o', markersize=8,
                    label=f'{champion_name} {metric.title()}')

            # 점선 스타일로 상대방 데이터
            ax.plot(valid_times, opponent_values, '--', color=colors[metric],
                    linewidth=2, marker='s', markersize=6,
                    label=f'{opp_champion_name} {metric.title()}')

            # 데이터 포인트에 값 표시
            for i, (pv, ov) in enumerate(zip(player_values, opponent_values)):
                ax.annotate(f'{pv:.0f}', (valid_times[i], pv),
                            textcoords="offset points", xytext=(0, 10),
                            ha='center', color='white', fontsize=12)
                ax.annotate(f'{ov:.0f}', (valid_times[i], ov),
                            textcoords="offset points", xytext=(0, -15),
                            ha='center', color='white', fontsize=12)

        # 그래프 스타일링
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')
        ax.set_title('시간대별 KDA', pad=20, fontsize=24, fontweight='bold', color='white')
        ax.set_xlabel('게임 시간 (분)', labelpad=10, fontsize=22, color='white')
        ax.set_ylabel('횟수', labelpad=10, fontsize=22, color='white')

        # x축 설정
        ax.set_xticks(valid_times)
        ax.set_xticklabels([f'{t}분' for t in valid_times], fontsize=20, color='white')
        ax.tick_params(axis='y', labelsize=20)

        # 범례 스타일링
        legend = ax.legend(loc='upper left', frameon=True,
                           bbox_to_anchor=(0.02, 0.98),
                           fontsize=16, ncol=2)
        frame = legend.get_frame()
        frame.set_facecolor('#1a1a1a')
        frame.set_edgecolor('white')

        for text in legend.get_texts():
            text.set_color('white')

        # 그래프 테두리 제거
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)

        plt.tight_layout()

        # 저장
        output_path = self.output_dir / 'Series' / 'PickRate' / self.today_date
        output_path.mkdir(exist_ok=True, parents=True)
        plt.savefig(
            output_path / f'{game_id}_{player_name}_kda_combined.png',
            bbox_inches='tight',
            dpi=300,
            transparent=True
        )
        plt.close()

    def draw_economy_graph(self, game_id, player_name, champion_name, opp_champion_name, series_info):
        time_points = [10, 15, 20, 25]
        metrics = {
            'gold': {'div_factor': 1000, 'format': lambda x: f'{x / 1000:.1f}K'},
            'xp': {'div_factor': 1, 'format': lambda x: f'{x:.0f}'},
            'cs': {'div_factor': 1, 'format': lambda x: f'{x:.0f}'}
        }

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), dpi=100)
        fig.patch.set_facecolor('#1a1a1a')

        colors = {
            'gold': '#FFD700',  # 골드색
            'xp': '#9C27B0',  # 보라색
            'cs': '#2196F3'  # 하늘색
        }

        axes = {'gold': ax1, 'xp': ax2, 'cs': ax3}
        titles = {
            'gold': '골드',
            'xp': '경험치',
            'cs': 'CS'
        }

        for metric, config in metrics.items():
            ax = axes[metric]
            ax.set_facecolor('#1a1a1a')

            player_values = []
            opponent_values = []
            valid_times = []

            for time in time_points:
                val = series_info[f'{metric}at{time}'].iloc[0]
                opp_val = series_info[f'opp_{metric}at{time}'].iloc[0]

                if pd.notna(val) and pd.notna(opp_val):
                    player_values.append(val / config['div_factor'])
                    opponent_values.append(opp_val / config['div_factor'])
                    valid_times.append(time)

            # 라인 그리기
            ax.plot(valid_times, player_values, '-', color=colors[metric],
                    linewidth=3, marker='o', markersize=8,
                    label=champion_name)
            ax.plot(valid_times, opponent_values, '--', color=colors[metric],
                    linewidth=2, marker='s', markersize=6,
                    label=opp_champion_name)

            # 차이 영역 표시
            ax.fill_between(valid_times, player_values, opponent_values,
                            where=(np.array(player_values) >= np.array(opponent_values)),
                            color=colors[metric], alpha=0.1)
            ax.fill_between(valid_times, player_values, opponent_values,
                            where=(np.array(player_values) <= np.array(opponent_values)),
                            color=colors[metric], alpha=0.1)

            # 데이터 포인트에 값 표시
            for i, (pv, ov) in enumerate(zip(player_values, opponent_values)):
                ax.annotate(config['format'](pv * config['div_factor']),
                            (valid_times[i], pv),
                            textcoords="offset points", xytext=(0, 10),
                            ha='center', color='white', fontsize=12)
                ax.annotate(config['format'](ov * config['div_factor']),
                            (valid_times[i], ov),
                            textcoords="offset points", xytext=(0, -15),
                            ha='center', color='white', fontsize=12)

            # 축 스타일링
            ax.grid(True, linestyle='--', alpha=0.3, color='gray')
            ax.set_title(f'시간대별 {titles[metric]}', pad=15, fontsize=18, color='white')
            ax.set_xlabel('게임 시간 (분)', labelpad=10, fontsize=16, color='white')
            ax.tick_params(axis='both', labelsize=14)
            ax.set_xticks(valid_times)
            ax.set_xticklabels([f'{t}분' for t in valid_times])

            # 범례 스타일링
            legend = ax.legend(loc='upper left', frameon=True,
                               bbox_to_anchor=(0.02, 0.98),
                               fontsize=14)
            frame = legend.get_frame()
            frame.set_facecolor('#1a1a1a')
            frame.set_edgecolor('white')

            for text in legend.get_texts():
                text.set_color('white')

            # 그래프 테두리 제거
            for spine in ['top', 'right']:
                ax.spines[spine].set_visible(False)

        plt.tight_layout()

        # 저장
        output_path = self.output_dir / 'Series' / 'PickRate' / self.today_date
        output_path.mkdir(exist_ok=True, parents=True)
        plt.savefig(
            output_path / f'{game_id}_{player_name}_economy_combined.png',
            bbox_inches='tight',
            dpi=300,
            transparent=True
        )
        plt.close()

    # def get_position_weights(self, position):
    #     """
    #     Get scoring weights based on player position
    #     """
    #     weights = {
    #         'top': {
    #             'kda': 0.25,
    #             'economy': 0.30,
    #             'vision': 0.15,
    #             'objective': 0.15,
    #             'damage': {
    #                 'dealt': 0.08,
    #                 'taken': 0.07
    #             }
    #         },
    #         'jng': {  # 데이터베이스의 position 컬럼에 맞춤
    #             'kda': 0.20,
    #             'economy': 0.15,
    #             'vision': 0.20,
    #             'objective': 0.35,
    #             'damage': {
    #                 'dealt': 0.05,
    #                 'taken': 0.05
    #             }
    #         },
    #         'mid': {
    #             'kda': 0.25,
    #             'economy': 0.25,
    #             'vision': 0.15,
    #             'objective': 0.15,
    #             'damage': {
    #                 'dealt': 0.15,
    #                 'taken': 0.05
    #             }
    #         },
    #         'bot': {  # ADC position
    #             'kda': 0.30,
    #             'economy': 0.25,
    #             'vision': 0.10,
    #             'objective': 0.15,
    #             'damage': {
    #                 'dealt': 0.15,
    #                 'taken': 0.05
    #             }
    #         },
    #         'sup': {  # Support position
    #             'kda': 0.20,
    #             'economy': 0.10,
    #             'vision': 0.35,
    #             'objective': 0.20,
    #             'damage': {
    #                 'dealt': 0.05,
    #                 'taken': 0.10
    #             }
    #         }
    #     }
    #     return weights.get(position.lower(), weights['mid'])
    #
    # def calculate_mvp_score(self, game_df):
    #     """
    #     Calculate MVP score for each player considering their positions
    #     """
    #
    #     def calculate_player_score(row):
    #         weights = self.get_position_weights(row['position'])
    #
    #         # 1. KDA Score
    #         if row['deaths'] == 0:
    #             kda = (row['kills'] + row['assists']) * 2
    #         else:
    #             kda = (row['kills'] + row['assists']) / row['deaths']
    #
    #         kill_participation = (row['kills'] + row['assists']) / row['teamkills'] if row['teamkills'] > 0 else 0
    #         first_blood_bonus = 2 if (row['firstbloodkill'] or row['firstbloodassist']) else 0
    #
    #         kda_score = (
    #                             (kda * 0.4) +
    #                             (kill_participation * 0.4) +
    #                             (first_blood_bonus * 0.2)
    #                     ) * weights['kda'] * 100
    #
    #         # 2. Economy Score
    #         gold_efficiency = row['goldspent'] / row['earnedgold'] if row['earnedgold'] > 0 else 0
    #         economy_score = (
    #                                 (row['cspm'] / 10 * 0.3) +
    #                                 (row['damageshare'] * 0.4) +
    #                                 (row['earnedgoldshare'] * 0.3)
    #                         ) * weights['economy'] * 100
    #
    #         # 3. Vision Score
    #         vision_score = (
    #                                (row['vspm'] * 0.4) +
    #                                (row['wcpm'] * 0.3) +
    #                                (row['wpm'] * 0.3)
    #                        ) * weights['vision'] * 100
    #
    #         # 4. Objective Score
    #         first_objectives = sum([
    #             row['firsttower'], row['firstdragon'],
    #             row['firstherald'], row['firstbaron']
    #         ])
    #
    #         objective_score = ((first_objectives / 4 * 0.5) +
    #                                   (row['towers'] / (row['towers'] + row['opp_towers']) * 0.25 if (row['towers'] +
    #                                                                                                   row[
    #                                                                                                       'opp_towers']) > 0 else 0) +
    #                                   (row['dragons'] / (row['dragons'] + row['opp_dragons']) * 0.25 if (row[
    #                                                                                                          'dragons'] +
    #                                                                                                      row[
    #                                                                                                          'opp_dragons']) > 0 else 0)
    #                           ) * weights['objective'] * 100
    #
    #         # 5. Damage Score
    #         damage_score = (
    #                                (row['damageshare'] * weights['damage']['dealt']) +
    #                                ((row['damagetakenperminute'] / (row['dpm'] if row['dpm'] > 0 else 1)) *
    #                                 weights['damage']['taken'])
    #                        ) * 100
    #
    #         # Position-specific bonuses
    #         position = row['position'].lower()
    #         if position == 'jng':
    #             objective_score *= 1.2
    #             if row['monsterkillsenemyjungle'] > 5:
    #                 objective_score *= 1.1
    #
    #         elif position == 'sup':
    #             vision_score *= 1.2
    #             if row['assists'] > row['kills'] * 2:
    #                 kda_score *= 1.1
    #
    #         elif position == 'mid':
    #             if kill_participation > 0.6:
    #                 kda_score *= 1.15
    #
    #         elif position == 'bot':
    #             if row['deaths'] < 3:
    #                 kda_score *= 1.2
    #
    #         elif position == 'top':
    #             if row['firsttower']:
    #                 objective_score *= 1.2
    #
    #         # Victory bonus
    #         if row['result']:
    #             total_score_base = kda_score + economy_score + vision_score + objective_score + damage_score
    #             victory_bonus = total_score_base * 0.1  # 승리 시 10% 보너스
    #         else:
    #             victory_bonus = 0
    #
    #         total_score = kda_score + economy_score + vision_score + objective_score + damage_score + victory_bonus
    #
    #         return {
    #             'total_score': total_score,
    #             'breakdown': {
    #                 'KDA': kda_score,
    #                 'Economy': economy_score,
    #                 'Vision': vision_score,
    #                 'Objective': objective_score,
    #                 'Damage': damage_score,
    #                 'Victory Bonus': victory_bonus
    #             }
    #         }
    #
    #     # Calculate scores for all players
    #     scores = game_df.apply(calculate_player_score, axis=1)
    #
    #     # Create result DataFrame
    #     result_df = game_df[['playername', 'champion', 'position']].copy()
    #     result_df['mvp_score'] = scores.apply(lambda x: x['total_score'])
    #     result_df['score_breakdown'] = scores.apply(lambda x: x['breakdown'])
    #     print(result_df)
    #     return result_df.sort_values('mvp_score', ascending=False)

    def get_game_mvp(self, game_id):
        game_df = self.database.get_game_data(game_id)
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

        # 게임별로 스탯 정규화 적용
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

