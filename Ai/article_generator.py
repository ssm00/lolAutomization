
from langchain_core.tracers import LangChainTracer
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.json import JsonOutputParser

from langchain_core.prompts import PromptTemplate
from Ai.response_form import *

class ArticleGenerator:
    def __init__(self, database, meta_data):
        load_dotenv()
        self.database = database
        self.meta_data = meta_data
        self.prmpt = meta_data.prompt.get("pick_rate")
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
            'fifth_page': JsonOutputParser(pydantic_object=FifthPageResponse)
        }
        self.first_page_template = PromptTemplate(
            input_variables=["player_name", "champion_name", "position", "team_name", "pick_rate", "kda", "max_chars"],
            partial_variables={"format_instructions": self.parsers['first_page'].get_format_instructions()},
            template=self.prmpt.get("v1").get("page1")
        )

        self.second_page_template = PromptTemplate(
            input_variables=["game_date", "league", "set", "blue_team_name", "red_team_name",
                    "player_name", "champion_name", "opp_player", "opp_champion",
                    "patch_version", "pick_rate", "player_team", "mvp_champion",
                    "mvp_player", "mvp_score", "max_chars"],
            partial_variables={"format_instructions": self.parsers['second_page'].get_format_instructions()},
            template=self.prmpt.get("v1").get("page2")
        )

        self.third_page_template = PromptTemplate(
            input_variables=[
                "champion_kr_name", "opp_kr_name", "position",
                "gold_diff_data", "exp_diff_data",
                "time_frames", "max_chars", "stats", "player_stats_values", "opponent_stats_values", "label_mapping"
            ],
            partial_variables={"format_instructions": self.parsers['third_page'].get_format_instructions()},
            template=self.prmpt.get("v1").get("page3")
        )

        self.fourth_page_template = PromptTemplate(
            input_variables=["champion_kr_name", "position", "tier", "pick_rate", "ban_rate", "win_rate", "ranking", "max_chars", "patch", "opponent_champion"],
            partial_variables={"format_instructions": self.parsers['fourth_page'].get_format_instructions()},
            template=self.prmpt.get("v1").get("page4")
        )

        self.fifth_page_template = PromptTemplate(
            input_variables=[
                "player_name", "player_champion_kr", "position", "counters", "max_chars"
            ],
            partial_variables={"format_instructions": self.parsers['fifth_page'].get_format_instructions()},
            template=self.prmpt.get("v1").get("page5")
        )
        self.chains = {
            'first_page': self.first_page_template | self.llm | self.parsers['first_page'],
            'second_page': self.second_page_template | self.llm | self.parsers['second_page'],
            'third_page': self.third_page_template | self.llm | self.parsers['third_page'],
            'fourth_page': self.fourth_page_template | self.llm | self.parsers['fourth_page'],
            'fifth_page': self.fifth_page_template | self.llm | self.parsers['fifth_page']
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
        print(max_chars)
        print(result)
        print(len(result['text']))
        return result['text']




    def generate_third_page_article(self, game_df, player_name, max_chars):
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

    def generate_fourth_page_article(self, game_df, player_name, max_chars):
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

    def generate_fifth_page_article(self, match_id, player_name, max_chars):
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

