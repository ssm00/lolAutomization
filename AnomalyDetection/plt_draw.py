import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import pandas as pd
from pathlib import Path
import numpy as np


class PltDraw:

    def __init__(self, database, meta_data):
        self.database = database
        self.patch = meta_data.anomaly_info.get("patch")
        self.plt_out_dir = Path(__file__).parent.parent / "PltOutput"

    def draw_pick_rates(self, name_us, position):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')
        champ_data = position_champions[position]['name_us_list']
        df = pd.DataFrame([
            {'name_us':name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
            for name_us, champ_info in champ_data.items()
        ])
        df_filtered = df[df['name_us'] != name_us]
        top_9 = df_filtered.nlargest(9, 'Pick Rate')
        for champ_name, champ_info in champ_data.items():
            if champ_name == name_us:
                unusual_data = pd.DataFrame([{
                    'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']
                }])
        final_df = pd.concat([top_9, unusual_data])
        fig, ax = plt.subplots(figsize=(10.8, 10.8))
        ax.set_facecolor('#F0F0F0')
        fig.patch.set_facecolor('white')
        colors = ['#3498db' if x != name_us else '#e74c3c' for x in final_df['name_us']]
        bars = ax.bar(
            range(len(final_df)),
            final_df['Pick Rate'],
            color=colors,
            edgecolor='black',
            linewidth=1,
            alpha=0.7,
            width=0.7
        )
        ax.grid(True, axis='y', linestyle='--', alpha=0.7, zorder=0)
        ax.set_axisbelow(True)

        plt.xticks(
            range(len(final_df)),
            final_df['name_kr'],
            rotation=45,
            ha='right',
            fontsize=20,
            fontweight='bold'
        )

        ax.set_ylim(0, max(final_df['Pick Rate']) * 1.2)
        position_kr_map = {'jungle':'정글', 'top':'탑','bottom':'바텀','mid':'미드','support':'서포터'}
        position_kr = position_kr_map[position]
        plt.title(f'{position_kr} {unusual_data["name_kr"]} 챔피언별 픽률   패치 버전:{self.patch}',
                  pad=20,
                  size=30,
                  fontweight='bold')
        threshold = position_champions[position]['low_pickrate_threshold']
        ax.axhline(
            y=threshold,
            color='#e74c3c',
            linestyle='--',
            alpha=0.5,
            linewidth=2,
            label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
        )

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{height:.1f}%',
                ha='center',
                va='bottom',
                fontsize=20,
                fontweight='bold'
            )

        for spine in ax.spines.values():
            spine.set_edgecolor('#CCCCCC')

        plt.tight_layout()
        plt.savefig(
            self.plt_out_dir / "PickRate" / f'{position_kr} {unusual_data["name_kr"].iloc[0]} 픽률   패치 버전:{self.patch}',
            bbox_inches='tight',
            dpi=300,
            facecolor=fig.get_facecolor(),
            edgecolor='none',
            transparent=True
        )
        plt.close()

    def draw_pick_rates_transparent(self, name_us, position):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        # 전체적인 스타일 설정
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')

        champ_data = position_champions[position]['name_us_list']
        df = pd.DataFrame([
            {'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
            for name_us, champ_info in champ_data.items()
        ])
        df_filtered = df[df['name_us'] != name_us]
        top_9 = df_filtered.nlargest(9, 'Pick Rate')

        for champ_name, champ_info in champ_data.items():
            if champ_name == name_us:
                unusual_data = pd.DataFrame([{
                    'name_us': name_us,
                    'name_kr': champ_info['name_kr'],
                    'Pick Rate': champ_info['pick_rate']
                }])

        final_df = pd.concat([top_9, unusual_data])

        fig, ax = plt.subplots(figsize=(10.8, 10.8))

        ax.set_facecolor('none')
        fig.patch.set_facecolor('none')

        colors = ['#3498db' if x != name_us else '#e74c3c' for x in final_df['name_us']]
        bars = ax.bar(
            range(len(final_df)),
            final_df['Pick Rate'],
            color=colors,
            edgecolor='black',
            linewidth=1,
            alpha=0.7,
            width=0.7
        )

        ax.grid(True, axis='y', linestyle='--', alpha=0.7, zorder=0)
        ax.set_axisbelow(True)

        plt.xticks(
            range(len(final_df)),
            final_df['name_kr'],
            rotation=45,
            ha='right',
            fontsize=20,
            fontweight='bold',
            color='white'
        )

        ax.tick_params(axis='y', colors='white')

        ax.set_ylim(0, max(final_df['Pick Rate']) * 1.2)

        position_kr_map = {'jungle': '정글', 'top': '탑', 'bottom': '바텀', 'mid': '미드', 'support': '서포터'}
        position_kr = position_kr_map[position]
        plt.title(f'{position_kr} {unusual_data["name_kr"].iloc[0]} 픽률   패치 버전:{self.patch}',
                  pad=20,
                  size=30,
                  fontweight='bold',
                  color='white')

        threshold = position_champions[position]['low_pickrate_threshold']
        ax.axhline(
            y=threshold,
            color='#e74c3c',
            linestyle='--',
            alpha=0.5,
            linewidth=2,
            label=f'Low Pick Rate Threshold ({threshold:.2f}%)'
        )

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{height:.1f}%',
                ha='center',
                va='bottom',
                fontsize=20,
                fontweight='bold',
                color='white'
            )

        plt.tight_layout()
        save_path = self.plt_out_dir / "PickRate" / f'pick_rate_analysis_{position}_{name_us}_{self.patch}.png'
        plt.savefig(
            save_path,
            bbox_inches='tight',
            dpi=300,
            transparent=True
        )
        plt.close()
        return save_path

    def draw_pick_rates_vertical_transparent(self, name_us, position):
        matplotlib.use('Agg')
        position_champions = self.database.get_pick_rate_info(self.patch)
        plt.style.use('seaborn-v0_8-dark')
        plt.rc('font', family='Malgun Gothic')

        champ_data = position_champions[position]['name_us_list']
        df = pd.DataFrame([
            {'name_us': name_us, 'name_kr': champ_info['name_kr'], 'Pick Rate': champ_info['pick_rate']}
            for name_us, champ_info in champ_data.items()
        ])
        df_filtered = df[df['name_us'] != name_us]
        top_9 = df_filtered.nlargest(9, 'Pick Rate')

        for champ_name, champ_info in champ_data.items():
            if champ_name == name_us:
                unusual_data = pd.DataFrame([{
                    'name_us': name_us,
                    'name_kr': champ_info['name_kr'],
                    'Pick Rate': champ_info['pick_rate']
                }])

        final_df = pd.concat([top_9, unusual_data])
        final_df = final_df.sort_values('Pick Rate', ascending=True)

        fig, ax = plt.subplots(figsize=(5.9, 10.8))

        ax.set_facecolor('none')
        fig.patch.set_facecolor('none')

        colors = ['#3498db' if x != name_us else '#e74c3c' for x in final_df['name_us']]
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
            fontweight='bold',
            color='white'
        )

        ax.tick_params(axis='x', colors='white')

        ax.set_xlim(0, max(final_df['Pick Rate']) * 1.2)

        position_kr_map = {'jungle': '정글', 'top': '탑', 'bottom': '바텀', 'mid': '미드', 'support': '서포터'}
        position_kr = position_kr_map[position]

        plt.title(f'{position_kr} {unusual_data["name_kr"].iloc[0]} 챔피언별 픽률   패치 버전:{self.patch}',
                  pad=20,
                  size=16,
                  fontweight='bold',
                  color='white')

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
                fontweight='bold',
                color='white'
            )

        plt.tight_layout()
        save_path = self.plt_out_dir / "PickRate" / f'pick_rate_analysis_{position}_{name_us}_{self.patch}.png'
        plt.savefig(
            save_path,
            bbox_inches='tight',
            dpi=300,
            transparent=True
        )
        plt.close()
        return save_path

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