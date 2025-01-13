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
        select_columns = {
            "goldat":[
                "goldat10", "opp_goldat10", "golddiffat10",
                "goldat15", "opp_goldat15", "golddiffat15",
                "goldat20", "opp_goldat20", "golddiffat20",
                "goldat25", "opp_goldat25", "golddiffat25"],
            "xpat":[
                "xpat10", "opp_xpat10", "xpdiffat10",
                "xpat15", "opp_xpat15", "xpdiffat15",
                "xpat20", "opp_xpat20", "xpdiffat20",
                "xpat25", "opp_xpat25", "xpdiffat25"],
            "csat":[
                "csat10", "opp_csat10", "csdiffat10",
                "csat15", "opp_csat15", "csdiffat15",
                "csat20", "opp_csat20", "csdiffat20",
                "csat25", "opp_csat25", "csdiffat25"],
            "killsat": [
                "killsat10", "opp_killsat10",
                "killsat15", "opp_killsat15",
                "killsat20", "opp_killsat20",
                "killsat25", "opp_killsat25"],
            "assistsat": [
                "assistsat10", "opp_assistsat10",
                "assistsat15", "opp_assistsat15",
                "assistsat20", "opp_assistsat20",
                "assistsat25", "opp_assistsat25"],
            "deathsat": [
                "deathsat10", "opp_deathsat10",
                "deathsat15", "opp_deathsat15",
                "deathsat20", "opp_deathsat20",
                "deathsat25", "opp_deathsat25", ],
        }
        df = series_info[select_columns].copy()
        
        self.draw_series(champion_name, df, game_id, opp_champion_name, player_name)

    def draw_series(self, champion_name, df, game_id, opp_champion_name, player_name):
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
                              label=f'({champion_name}) 골드')
        opp_line = ax.plot(valid_times, opponent_gold, '-', color='#DC2626',
                           linewidth=3, marker='o', markersize=8,
                           label=f'({opp_champion_name}) 골드')
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