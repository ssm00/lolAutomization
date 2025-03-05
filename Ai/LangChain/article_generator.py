from langchain_core.tracers import LangChainTracer
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.json import JsonOutputParser

from langchain_core.prompts import PromptTemplate
from Ai.LangChain.response_form import *

class ArticleGenerator:
    def __init__(self, database, mongo, meta_data):
        load_dotenv()
        self.database = database
        self.mongo = mongo
        self.meta_data = meta_data
        self.prompt = meta_data.prompt
        self.pick_rate_type = meta_data.prompt.get("pick_rate").get("type")
        tracer = LangChainTracer(
            project_name=os.getenv('LANGCHAIN_PROJECT', 'default-project')
        )
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name=os.getenv('MODEL_NAME', 'gpt-4o-mini'),
            callbacks=[tracer]
        )
        self.parsers = {
            'first_page': JsonOutputParser(pydantic_object=FirstPageResponse),
            'second_page': JsonOutputParser(pydantic_object=SecondPageResponse),
            'third_page': JsonOutputParser(pydantic_object=ThirdPageResponse),
            'fourth_page': JsonOutputParser(pydantic_object=FourthPageResponse),
            'fifth_page': JsonOutputParser(pydantic_object=FifthPageResponse),
            'interview': JsonOutputParser(pydantic_object=InterviewResponse)
        }
        self.first_page_template = PromptTemplate(
            input_variables=["player_name", "champion_name", "position", "team_name", "pick_rate", "kda", "max_chars"],
            partial_variables={"format_instructions": self.parsers['first_page'].get_format_instructions()},
            template=self.prompt.get("pick_rate").get("long").get("page1")
        )

        self.second_page_template = PromptTemplate(
            input_variables=["game_date", "league", "set", "blue_team_name", "red_team_name",
                    "player_name", "champion_name", "opp_player", "opp_champion",
                    "patch_version", "pick_rate", "player_team", "mvp_champion",
                    "mvp_player", "mvp_score", "max_chars"],
            partial_variables={"format_instructions": self.parsers['second_page'].get_format_instructions()},
            template=self.prompt.get("pick_rate").get("long").get("page2")
        )

        self.third_page_template = PromptTemplate(
            input_variables=[
                "champion_kr_name", "opp_kr_name", "position",
                "gold_diff_data", "exp_diff_data",
                "time_frames", "max_chars", "stats", "player_stats_values", "opponent_stats_values", "label_mapping"
            ],
            partial_variables={"format_instructions": self.parsers['third_page'].get_format_instructions()},
            template=self.prompt.get("pick_rate").get("long").get("page3")
        )

        self.fourth_page_template = PromptTemplate(
            input_variables=["champion_kr_name", "position", "tier", "pick_rate", "ban_rate", "win_rate", "ranking", "max_chars", "patch", "opponent_champion"],
            partial_variables={"format_instructions": self.parsers['fourth_page'].get_format_instructions()},
            template=self.prompt.get("pick_rate").get("long").get("page4")
        )

        self.fifth_page_template = PromptTemplate(
            input_variables=[
                "player_name", "player_champion_kr", "position", "counters", "max_chars"
            ],
            partial_variables={"format_instructions": self.parsers['fifth_page'].get_format_instructions()},
            template=self.prompt.get("pick_rate").get("long").get("page5")
        )

        self.interview_template = PromptTemplate(
            input_variables=[
                "full_text"
            ],
            partial_variables={"format_instructions": self.parsers['interview'].get_format_instructions()},
            template=self.prompt.get("interview").get("v1")
        )

        self.chains = {
            'first_page': self.first_page_template | self.llm | self.parsers['first_page'],
            'second_page': self.second_page_template | self.llm | self.parsers['second_page'],
            'third_page': self.third_page_template | self.llm | self.parsers['third_page'],
            'fourth_page': self.fourth_page_template | self.llm | self.parsers['fourth_page'],
            'fifth_page': self.fifth_page_template | self.llm | self.parsers['fifth_page'],
            'interview': self.interview_template | self.llm | self.parsers['interview']
        }

    def generate_first_page_article(self, game_df, player_name, max_chars):
        player_data = game_df[game_df['playername'] == player_name].iloc[0]
        champion_kr_name = self.database.get_name_kr(player_data['name_us'])
        champion_stats = self.database.get_champion_rate_table(
            player_data['name_us'],
            self.meta_data.basic_info.get("patch"),
            player_data['position']
        )
        article_data = {
            "player_name": player_name,
            "champion_name": champion_kr_name,
            "position": player_data['position'],
            "team_name": player_data['teamname'],
            "pick_rate": f"{champion_stats['픽률']:.1f}%",
            "kda": f"{player_data['kills']}/{player_data['deaths']}/{player_data['assists']}",
            "max_chars": max_chars
        }
        result = self.chains['first_page'].invoke(article_data)
        return result['title']

    def generate_second_page_article(self, game_df, player_name, max_chars):
        if self.pick_rate_type == "long":
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            blue_team = game_df[game_df['side'] == 'Blue']
            red_team = game_df[game_df['side'] == 'Red']
            opp_player_data = game_df[
                (game_df['position'] == player_data['position']) &
                (game_df['side'] != player_data['side'])
                ].iloc[0]
            mvp_player_info = self.database.get_mvp_player(game_df)

            champion_stats = self.database.get_champion_pick_rate_info(
                player_data['name_us'],
                game_df['patch'].iloc[0],
                player_data['position']
            )

            template_variables = {
                'game_date': game_df['game_date'].iloc[0].strftime('%Y년%m월%d일'),
                'league': game_df['league'].iloc[0],
                'set': game_df['game'].iloc[0],
                'blue_team_name': blue_team['teamname'].iloc[0],
                'red_team_name': red_team['teamname'].iloc[0],
                'player_name': player_data['playername'],
                'champion_name': self.database.get_name_kr(player_data['name_us']),
                'opp_player': opp_player_data['playername'],
                'opp_champion': self.database.get_name_kr(opp_player_data['name_us']),
                'patch_version': game_df['patch'].iloc[0],
                'pick_rate': champion_stats['pick_rate'],
                'player_team': player_data['teamname'],
                'mvp_champion': mvp_player_info['name_kr'],
                'mvp_player': mvp_player_info['playername'],
                'mvp_score': mvp_player_info['mvp_score'],
                'max_chars': max_chars
            }

            result = self.chains['second_page'].invoke(template_variables)
            return result['text']
        elif self.pick_rate_type == "short":
            template = self.prompt.get("pick_rate").get("short").get("page2")
            mvp_player_info = self.database.get_mvp_player(game_df)
            player_data = game_df[game_df['playername'] == player_name].iloc[0]

            win_team = game_df[(game_df['result'] == 1) & (game_df['position'] == 'team')]['teamname'].iloc[0]
            lose_team = game_df[(game_df['result'] == 0) & (game_df['position'] == 'team')]['teamname'].iloc[0]
            win_team_total_score, lose_team_total_score = self.database.get_sets_score(player_data['gameid'], win_team, lose_team)
            if win_team_total_score >= lose_team_total_score:
                set_score = f"{win_team_total_score}-{lose_team_total_score}"
                score_leader = win_team
            else:
                set_score = f"{lose_team_total_score}-{win_team_total_score}"
                score_leader = lose_team
            line_kr = {'top':'탑','jungle':'정글','mid':'미드','bottom':'원딜','support':'서폿'}
            line = line_kr[player_data['position']]

            champion_stats = self.database.get_champion_pick_rate_info(player_data['name_us'], game_df['patch'].iloc[0], player_data['position'])
            template = template.format(
                win_team_name=win_team,
                lose_team_name=lose_team,
                set=game_df['game'].iloc[0],
                set_score=set_score,
                score_leader=score_leader,
                player_name=player_data['playername'],
                line=line,
                pick_rate=champion_stats['pick_rate'],
                champion_name=self.database.get_name_kr(player_data['name_us']),
                mvp_player=mvp_player_info['playername'],
                mvp_champion=mvp_player_info['name_kr'],
                mvp_score=mvp_player_info['mvp_score']
            )
            return template

    def generate_third_page_article(self, game_df, player_name, max_chars):
        if self.pick_rate_type == "long":
            try:
                player_data = game_df[game_df['playername'] == player_name].iloc[0]
                opp_mask = (game_df['position'] == player_data['position']) & (game_df['playername'] != player_name)
                opp_player_name = game_df[opp_mask]['playername'].iloc[0]
                game_id = player_data['gameid']
                radar_stats = self.database.get_radar_stats(game_id, player_name)
                comparison_data = self.database.get_player_comparison_series(
                    player_data['gameid'],
                    player_name,
                    opp_player_name
                )
                article_data = {
                    **comparison_data,
                    'stats': radar_stats['stats'],
                    'player_stats_values': radar_stats['stats_values']['player'],
                    'opponent_stats_values': radar_stats['stats_values']['opponent'],
                    'label_mapping': radar_stats['label_mapping'],
                    'max_chars': max_chars
                }
                result = self.chains['third_page'].invoke(article_data)
                return result['text']
            except Exception as e:
                print(f"오류 발생 위치: {__file__}, 라인: {e.__traceback__.tb_lineno}")
                print(f"오류 타입: {type(e).__name__}")
                print(f"오류 내용: {str(e)}")
                return "기사 생성에 실패했습니다."
        elif self.pick_rate_type == "short":
            template = self.prompt.get("pick_rate").get("short").get("page3")
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            opp_mask = (game_df['position'] == player_data['position']) & (game_df['playername'] != player_name)
            opp_player_name = game_df[opp_mask]['playername'].iloc[0]
            game_id = player_data['gameid']
            radar_stats = self.database.get_radar_stats(game_id, player_name)
            comparison_data = self.database.get_player_comparison_series(
                player_data['gameid'],
                player_name,
                opp_player_name
            )

            player_kills = radar_stats['stats_values'].get('player')[radar_stats['stats'].index('kills')]
            player_deaths = radar_stats['stats_values'].get('player')[radar_stats['stats'].index('deaths')]
            player_assists = radar_stats['stats_values'].get('player')[radar_stats['stats'].index('assists')]
            player_kda = self.calculate_kda(player_kills, player_deaths, player_assists)

            opp_kills = radar_stats['stats_values'].get('opponent')[radar_stats['stats'].index('kills')]
            opp_deaths = radar_stats['stats_values'].get('opponent')[radar_stats['stats'].index('deaths')]
            opp_assists = radar_stats['stats_values'].get('opponent')[radar_stats['stats'].index('assists')]
            opp_kda = self.calculate_kda(opp_kills, opp_deaths, opp_assists)

            name_additional_stat1 = radar_stats.get('label_mapping')[radar_stats['stats'][-2]]
            name_additional_stat2 = radar_stats.get('label_mapping')[radar_stats['stats'][-1]]
            player_additional_stat1 = radar_stats['stats_values'].get('player')[-2]
            player_additional_stat2 = radar_stats['stats_values'].get('player')[-1]
            opp_additional_stat1 = radar_stats['stats_values'].get('opponent')[-2]
            opp_additional_stat2 = radar_stats['stats_values'].get('opponent')[-1]
            comparison_text = self.create_comparison_text(comparison_data)
            template =template.format(
                champion_kr_name=comparison_data['champion_kr_name'],
                opp_kr_name=comparison_data['opp_kr_name'],
                player_kda=player_kda,
                opp_kda=opp_kda,
                name_additional_stat1=name_additional_stat1,
                name_additional_stat2=name_additional_stat2,
                player_additional_stat1=player_additional_stat1,
                player_additional_stat2=player_additional_stat2,
                opp_additional_stat1=opp_additional_stat1,
                opp_additional_stat2=opp_additional_stat2
            )
            template += comparison_text
            return template


    def generate_fourth_page_article(self, game_df, player_name, max_chars):
        if self.pick_rate_type == "long":
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            opp_player_data = game_df[
                (game_df['position'] == player_data['position']) &
                (game_df['side'] != player_data['side'])
                ].iloc[0]
            patch = self.meta_data.basic_info.get("patch")
            champion_stats = self.database.get_champion_pick_rate_info(
                player_data['name_us'],
                patch,
                player_data['position']
            )
            line_kr = {"top":"탑", "jungle":"정글", "mid":"미드", "bottom":"원딜", "support":"서포터", }
            article_data = {"champion_kr_name": champion_stats['name_kr'],
                            "position": line_kr[player_data['position']],
                            "tier": champion_stats['tier'],
                            "pick_rate": champion_stats['pick_rate'],
                            "ban_rate": champion_stats['ban_rate'],
                            "win_rate": champion_stats['win_rate'],
                            "ranking": champion_stats['ranking'],
                            "patch": patch,
                            "opponent_champion": self.database.get_name_kr(opp_player_data['name_us']),
                            "max_chars": max_chars
                            }
            result = self.chains['fourth_page'].invoke(article_data)
            return result['text']
        elif self.pick_rate_type == "short":
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            template = self.prompt.get("pick_rate").get("short").get("page4")
            patch = self.meta_data.basic_info.get("patch")
            champion_stats = self.database.get_champion_pick_rate_info(player_data['name_us'], patch, player_data['position'])
            line_kr = {"top": "탑", "jungle": "정글", "mid": "미드", "bottom": "원딜", "support": "서포터"}
            template = template.format(
                patch=patch,
                position=line_kr[player_data['position']],
                champion_kr_name=champion_stats['name_kr'],
                tier=champion_stats['tier'],
                total_champion_count=champion_stats['total_champion_count'],
                pick_rate=champion_stats['pick_rate'],
                pick_rank=champion_stats['pick_rank'],
                win_rate=champion_stats['win_rate'],
                win_rank=champion_stats['win_rank'],
                ban_rate=champion_stats['ban_rate'],
                ban_rank=champion_stats['ban_rank']
            )
            return template

    def generate_fifth_page_article(self, match_id, player_name, max_chars):
        if self.pick_rate_type == "long":
            game_df = self.database.get_game_data(match_id)
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            counter_info = self.database.get_counter_champion(player_data['name_us'], player_data['position'], self.meta_data.basic_info.get("patch"))
            player_champion_kr = self.database.get_name_kr(player_data['name_us'])
            top_counters = counter_info.head(3)
            try:
                article_data = {
                    'player_name': player_name,
                    'player_champion_kr': player_champion_kr,
                    'position': player_data['position'],
                    'max_chars': max_chars,
                    'counters': [
                        {
                            'name_kr': row['name_kr'],
                            'win_rate': row['win_rate'],
                            'games_played': row['games_played'],
                            'kda_diff': row['kda_diff'],
                            'counter_score': row['counter_score'],
                        }
                        for _, row in top_counters.iterrows()
                    ]
                }
                result = self.chains['fifth_page'].invoke(article_data)
                return result['text']
            except Exception as e:
                print(f"오류 발생 위치: {__file__}, 라인: {e.__traceback__.tb_lineno}")
                print(f"오류 내용: {str(e)}")
                return "기사 생성에 실패했습니다."
        elif self.pick_rate_type == "short":
            game_df = self.database.get_game_data(match_id)
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            counter_info = self.database.get_counter_champion(player_data['name_us'], player_data['position'], self.meta_data.basic_info.get("patch"))
            player_champion_kr = self.database.get_name_kr(player_data['name_us'])
            top_counters = counter_info.head(3)
            result_lines = ["프로경기 카운터 픽 분석"]
            for idx, row in top_counters.iterrows():
                counter_num = idx + 1
                line = [f"\u200b {counter_num}. {row['name_kr']}"]
                if row['counter_score'] > 0:
                    if row['win_rate'] > row['kda_diff'] * 10:
                        line.append(f"ㆍ 상대 승률 {row['win_rate']:.0f}%로 상대하기 쉬움")
                    else:
                        line.append(f"ㆍ 평균 상대 KDA +{row['kda_diff']:.2f}로 상대하기 쉬움")
                else:
                    line.append(f"ㆍ 상대 승률 {row['win_rate']:.0f}%로 상대하기 어려움")
                result_lines.append("\n".join(line))
            result = "\n".join(result_lines)
            return result

    def generate_interview_summary(self, document):
        result = self.chains['interview'].invoke({"full_text":document['full_text']})
        return result

    def calculate_kda(self, kill, death, assist):
        if death == 0:
            return kill + assist
        else:
            return round((kill + assist) / death, 2)

    def create_comparison_text(self, comparison_data):
        time_frames = comparison_data['time_frames']
        result_str = []

        phases = {
            'early': [t for t in time_frames if int(t.replace('min', '')) <= 10],
            'mid': [t for t in time_frames if 10 < int(t.replace('min', '')) <= 20],
            'late': [t for t in time_frames if int(t.replace('min', '')) > 20]
        }

        champion = comparison_data['champion_kr_name']
        opponent = comparison_data['opp_kr_name']

        def get_phase_winner(phase_times):
            if not phase_times:
                return ""

            gold_wins = 0
            exp_wins = 0
            total_comparisons = len(phase_times) * 2  # gold와 exp 각각 카운트

            for t in phase_times:
                if comparison_data['gold_diff_data'][t]['diff'] > 0:
                    gold_wins += 1
                if comparison_data['exp_diff_data'][t]['diff'] > 0:
                    exp_wins += 1

            win_rate = (gold_wins + exp_wins) / total_comparisons
            if len(phase_times) == 1:
                if win_rate == 1.0:
                    return f"{champion} 압도"
                elif win_rate == 0.5:
                    return "접전"
                else:
                    return f"{opponent} 압도"
            else:
                if win_rate >= 0.75:
                    return f"{champion} 압도"
                elif win_rate == 0.5:
                    return "접전"
                elif win_rate <= 0.25:
                    return f"{opponent} 압도"
                elif win_rate > 0.5:
                    return f"{champion} 승"
                else:
                    return f"{opponent} 승"

        phases_kr = {
            'early': '초반 (0~10분)',
            'mid': '중반 (10~20분)',
            'late': '후반 (20~25분)'
        }

        for phase, kr_phase in phases_kr.items():
            winner = get_phase_winner(phases[phase])
            if winner:
                result_str.append(f"ㆍ {kr_phase} : {winner}")

        return "\n".join(result_str)

