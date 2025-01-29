from PIL.Image import Image
from PIL.ImageDraw import ImageDraw
from PIL.ImageFont import ImageFont
from langchain_core.tracers import LangChainTracer
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.json import JsonOutputParser

from langchain.prompts import PromptTemplate
from Ai.response_form import *

class ArticleGenerator:
    def __init__(self, database, meta_data):
        load_dotenv()
        self.database = database
        self.meta_data = meta_data
        tracer = LangChainTracer(
            project_name=os.getenv('LANGCHAIN_PROJECT', 'default-project')
        )
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name=os.getenv('MODEL_NAME', 'gpt-3.5-turbo'),
            callbacks=[tracer]
        )
        self.parsers = {
            'first_page': JsonOutputParser(pydantic_object=FirstPageResponse),
            'second_page': JsonOutputParser(pydantic_object=SecondPageResponse),
            'third_page': JsonOutputParser(pydantic_object=ThirdPageResponse)
        }
        self.first_page_template = PromptTemplate(
            input_variables=["player_name", "champion_name", "position", "team_name", "pick_rate", "kda", "max_chars"],
            partial_variables={"format_instructions": self.parsers['first_page'].get_format_instructions()},
            template="""
                다음은 낮은 픽률의 챔피언을 선택한 경기에 대한 정보입니다. 
                ({max_chars})자 이내의 자극적인 제목을 생성해주세요.
    
                [입력 정보]
                선수명: {player_name}
                챔피언: {champion_name}
                포지션: {position}
                소속팀: {team_name}
                픽률: {pick_rate}
                KDA: {kda}
    
                [필수 작성 규칙]
                1. 제목은 반드시 {max_chars}자를 넘지 않아야 합니다(현재 글자 수가 표시되어야 함)
                2. 강조할 내용을 정확히 하나만 선택하여 ^ 기호 사이에 넣어주세요
                3. 제목이 {max_chars}자를 초과하면 자동으로 잘립니다
                4. 픽률과 관련된 내용이 포함되어야 합니다
    
                [제목 형식 예시 - 20자 기준]
                - "Faker의 픽률 ^0.1%^ 아지르 의도는?" (15자)
                - "^픽률 0.1%^의 스카너 픽?" (13자)
                - "의외로 개사기인 픽률 0.1% 스카너" (13자)
                - "레전드 픽 Faker의 픽률 0.1% 스카너" (13자)
    
                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "title": "제목 ({max_chars}자 이내, 강조 표시 ^ 포함)"
                }}
                {format_instructions}
            """
        )

        self.second_page_template = PromptTemplate(
            input_variables=["team_stats", "ban_picks", "player_info", "max_chars"],
            partial_variables={"format_instructions": self.parsers['second_page'].get_format_instructions()},
            template="""
                다음 경기 데이터를 바탕으로 ({max_chars})이내의 상세한 경기 분석 기사를 작성해주세요:
    
                [입력 데이터]
                팀 데이터: {team_stats}
                밴/픽 정보: {ban_picks}
                분석중인 플레이어 정보: {player_info}
    
                [분석 요구사항]
                1. 게임 전체 흐름 분석
                   - 양 팀의 전략적 의도 파악
                   - 승패를 결정지은 주요 요인 분석
                   - 주요 교전과 목표물 획득 과정 설명
    
                2. 밴픽 단계 상세 분석
                   - 각 팀의 밴픽 의도와 전략 설명
                   - 메타와의 연관성 분석
                   - 특이 픽이 있다면 그 의미 해석
    
                3. 라인전 성과 분석
                   - 각 라인별 대결 구도 설명
                   - CS, 골드, 경험치 차이의 의미
                   - 초중반 라인전이 후반에 미친 영향
    
                4. 핵심 플레이어 비교 분석
                   - 분석 중인 플레이어와 상대 포지션 선수의 상세 비교
                   - KDA, 데미지, 시야점수 등 객관적 지표 해석
                   - 팀 기여도와 경기 영향력 평가
    
                [작성 지침]
                - 공백을 포함하여 정확히 {max_chars}자 내외로 작성
                - '~습니다', '~했는데요' 체를 사용하여 자연스러운 서술
                - 객관적 데이터를 기반으로 한 분석적 시각 유지
                - 전문적이면서도 이해하기 쉬운 설명 제공
                - 핵심 플레이어에 대한 심층 분석 포함
                - champion 명을 사용할때는 name_kr을 사용하여 한국어명 이용
                
                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "text": "상세한 분석 내용 ({max_chars}자 내외)"
                }}
    
                {format_instructions}
                """
        )

        # 세 번째 페이지 프롬프트 템플릿 추가
        self.third_page_template = PromptTemplate(
            input_variables=["champion_name", "pick_rate", "ban_rate", "win_rate", "position", "tier", "max_chars"],
            template="""
            다음 챔피언 데이터를 바탕으로 챔피언 분석 기사를 작성해주세요:

            챔피언: {champion_name}
            포지션: {position}
            티어: {tier}
            픽률: {pick_rate}
            밴률: {ban_rate}
            승률: {win_rate}

            다음 가이드라인을 따라 작성해주세요:
            1. 현재 메타에서의 챔피언 위치
            2. 픽률과 밴률의 의미 분석
            3. {max_chars}자 이내로 작성
            
            """
        )

        # 네 번째 페이지 프롬프트 템플릿 추가
        self.fourth_page_template = PromptTemplate(
            input_variables=["performance_stats", "gold_stats", "exp_stats", "max_chars"],
            template="""
            다음 성과지표를 바탕으로 분석 기사를 작성해주세요:

            성과지표: {performance_stats}
            골드 데이터: {gold_stats}
            경험치 데이터: {exp_stats}

            다음 가이드라인을 따라 작성해주세요:
            1. 선수의 라인전 운영 능력 분석
            2. 자원 활용도 평가
            3. {max_chars}자 이내로 작성
            """
        )

        # 다섯 번째 페이지 프롬프트 템플릿 추가
        self.fifth_page_template = PromptTemplate(
            input_variables=["champion_name", "counter_picks", "counter_stats", "max_chars"],
            template="""
            다음 카운터 픽 데이터를 바탕으로 분석 기사를 작성해주세요:

            챔피언: {champion_name}
            카운터 챔피언: {counter_picks}
            상대 전적: {counter_stats}

            다음 가이드라인을 따라 작성해주세요:
            1. 카운터 챔피언들의 특징 분석
            2. 상대 전적의 의미 해석
            3. {max_chars}자 이내로 작성
            """
        )

        # 여섯 번째 페이지 프롬프트 템플릿 추가
        self.sixth_page_template = PromptTemplate(
            input_variables=["match_result", "team_stats", "player_contribution", "max_chars"],
            template="""
            다음 경기 결과 데이터를 바탕으로 결과 분석 기사를 작성해주세요:

            경기 결과: {match_result}
            팀 통계: {team_stats}
            선수 기여도: {player_contribution}

            다음 가이드라인을 따라 작성해주세요:
            1. 승패 요인 분석
            2. 팀 기여도 평가
            3. {max_chars}자 이내로 작성
            """
        )
        self.chains = {
            'first_page': self.first_page_template | self.llm | self.parsers['first_page'],
            'second_page': self.second_page_template | self.llm | self.parsers['second_page']
        }

    def calculate_text_box_size(self, font_path, font_size, box_width, box_height):
        font = ImageFont.truetype(font_path, font_size)
        test_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(test_img)
        test_chars = "가나다라마바사아자차카타파하"
        avg_char_width = sum(draw.textlength(char, font=font) for char in test_chars) / len(test_chars)
        line_height = font_size * 1.2
        chars_per_line = int(box_width / avg_char_width)
        available_lines = int(box_height / line_height)
        max_chars = chars_per_line * available_lines
        max_chars = int(max_chars * 0.85)
        return max(1, max_chars)

    def generate_first_page_article(self, game_df, player_name, max_chars):
        player_data = game_df[game_df['playername'] == player_name].iloc[0]
        champion_kr_name = self.database.get_name_kr(player_data['name_us'])
        champion_stats = self.database.get_champion_stats(
            player_data['name_us'],
            self.meta_data.anomaly_info.get("patch"),
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

    def generate_second_page_article(self, game_df, mvp_score, player_name, max_chars):
        player_data = game_df[game_df['playername'] == player_name].iloc[0]
        blue_team = game_df[game_df['side'] == 'Blue']
        red_team = game_df[game_df['side'] == 'Red']

        team_stats = {
            'game_info': {
                'league': game_df['league'].iloc[0],
                'game_date': game_df['game_date'].iloc[0],
                'mvp_score': mvp_score,
            },
            'blue_team': {
                'teamname': blue_team['teamname'].iloc[0],
                'kills': blue_team['teamkills'].iloc[0],
                'deaths': blue_team['teamdeaths'].iloc[0],
                'towers': blue_team['towers'].iloc[0]
            },
            'red_team': {
                'teamname': red_team['teamname'].iloc[0],
                'kills': red_team['teamkills'].iloc[0],
                'deaths': red_team['teamdeaths'].iloc[0],
                'towers': red_team['towers'].iloc[0]
            }
        }
        ban_picks = {
            'blue_bans': [blue_team[f'ban{i}'].iloc[0] for i in range(1, 6)],
            'red_bans': [red_team[f'ban{i}'].iloc[0] for i in range(1, 6)]
        }
        player_info = {
            'player_name': player_data['playername'],
            'champion_name': player_data['name_us']
        }
        article_data = {"team_stats":team_stats, "ban_picks":ban_picks, "player_info":player_info, "max_chars":max_chars}
        result = self.chains['second_page'].invoke(article_data)
        return result['text']

    def generate_third_page_article(self, match_id, player_name, font_size, box_width, box_height):
        try:
            max_chars = self.calculate_text_box_size(font_size, box_width, box_height)
            self.max_chars['third_page'] = min(max_chars, self.max_chars['third_page'])

            game_df = self.database.get_game_data(match_id)
            player_data = game_df[game_df['playername'] == player_name].iloc[0]
            champion_kr_name = self.database.get_champion_kr_name(player_data['name_us'])

            champion_stats = self.database.get_champion_stats(
                player_data['name_us'],
                self.meta_data.anomaly_info.get("patch"),
                player_data['position']
            )

            article = self.chains['third_page'].run({
                'champion_name': champion_kr_name,
                'position': player_data['position'],
                'tier': champion_stats['티어'],
                'pick_rate': f"{champion_stats['픽률']:.1f}%",
                'ban_rate': f"{champion_stats['밴률']:.1f}%",
                'win_rate': f"{champion_stats['승률']:.1f}%",
                'max_chars': self.max_chars['third_page']
            })

            if len(article) > self.max_chars['third_page']:
                article = article[:self.max_chars['third_page']] + "..."
            return article
        except Exception as e:
            print(f"오류 발생 위치: {__file__}, 라인: {e.__traceback__.tb_lineno}")
            print(f"오류 타입: {type(e).__name__}")
            print(f"오류 내용: {str(e)}")
            return "기사 생성에 실패했습니다."

    def generate_fourth_page_article(self, match_id, player_name, font_size, box_width, box_height):
        try:
            max_chars = self.calculate_text_box_size(font_size, box_width, box_height)
            self.max_chars['fourth_page'] = min(max_chars, self.max_chars['fourth_page'])

            game_df = self.database.get_game_data(match_id)
            player_data = game_df[game_df['playername'] == player_name].iloc[0]

            performance_stats = {
                'kills': player_data['kills'],
                'deaths': player_data['deaths'],
                'assists': player_data['assists'],
                'damage_share': f"{player_data['damageshare']:.1f}%"
            }

            gold_stats = {
                'total_gold': player_data['totalgold'],
                'earned_gpm': player_data['earned_gpm'],
                'gold_share': f"{player_data['earnedgoldshare']:.1f}%"
            }

            exp_stats = {
                'xp_diff_10': player_data['xpdiffat10'],
                'xp_diff_15': player_data['xpdiffat15'],
                'xp_diff_20': player_data['xpdiffat20']
            }

            article = self.chains['fourth_page'].run({
                'performance_stats': str(performance_stats),
                'gold_stats': str(gold_stats),
                'exp_stats': str(exp_stats),
                'max_chars': self.max_chars['fourth_page']
            })

            if len(article) > self.max_chars['fourth_page']:
                article = article[:self.max_chars['fourth_page']] + "..."
            return article
        except Exception as e:
            print(f"오류 발생 위치: {__file__}, 라인: {e.__traceback__.tb_lineno}")
            print(f"오류 타입: {type(e).__name__}")
            print(f"오류 내용: {str(e)}")
            return "기사 생성에 실패했습니다."

    def generate_fifth_page_article(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_data = game_df[game_df['playername'] == player_name].iloc[0]

        counter_info = self.database.get_counter_champion(
            player_data['name_us'],
            player_data['position'],
            self.meta_data.anomaly_info.get("patch")
        )

        try:
            article = self.chains['fifth_page'].run({
                'champion_name': player_data['name_kr'],
                'counter_picks': str(counter_info['name_kr'].tolist()),
                'counter_stats': str(counter_info[['win_rate', 'counter_score']].to_dict())
            })
            return article
        except Exception as e:
            print(f"오류 발생 위치: {__file__}, 라인: {e.__traceback__.tb_lineno}")
            print(f"오류 내용: {str(e)}")
            return "기사 생성에 실패했습니다."

    def generate_sixth_page_article(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_data = game_df[game_df['playername'] == player_name].iloc[0]
        team_data = game_df[game_df['teamname'] == player_data['teamname']]

        match_result = {
            'result': '승리' if player_data['result'] else '패배',
            'game_length': player_data['gamelength']
        }

        team_stats = {
            'total_kills': team_data['teamkills'].iloc[0],
            'total_deaths': team_data['teamdeaths'].iloc[0],
            'towers': team_data['towers'].iloc[0],
            'dragons': team_data['dragons'].iloc[0],
            'barons': team_data['barons'].iloc[0]
        }

        player_contribution = {
            'damage_share': f"{player_data['damageshare']:.1f}%",
            'gold_share': f"{player_data['earnedgoldshare']:.1f}%",
            'kda': f"{player_data['kills']}/{player_data['deaths']}/{player_data['assists']}"
        }

        try:
            article = self.chains['sixth_page'].run({
                'match_result': str(match_result),
                'team_stats': str(team_stats),
                'player_contribution': str(player_contribution)
            })
            return article
        except Exception as e:
            print(f"오류 발생 위치: {__file__}, 라인: {e.__traceback__.tb_lineno}")
            print(f"오류 내용: {str(e)}")
            return "기사 생성에 실패했습니다."