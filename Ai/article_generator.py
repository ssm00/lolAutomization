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
            'third_page': JsonOutputParser(pydantic_object=ThirdPageResponse),
            'fourth_page': JsonOutputParser(pydantic_object=FourthPageResponse),
            'fifth_page': JsonOutputParser(pydantic_object=FifthPageResponse)
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

        self.third_page_template = PromptTemplate(
            input_variables=["champion_kr_name", "position", "tier", "pick_rate", "ban_rate", "win_rate", "ranking", "max_chars", "patch"],
            partial_variables={"format_instructions": self.parsers['third_page'].get_format_instructions()},
            template="""
                다음은 패치 {patch}에서 특이하게 낮은 픽률을 보이는 챔피언의 상세 데이터입니다. 
                해당 데이터를 바탕으로 ({max_chars})자 이내의 전략적 분석 카드뉴스를 작성해주세요:
            
                [챔피언 기본 정보]
                챔피언명: {champion_kr_name}
                포지션: {position}
                티어: {tier}
            
                [핵심 지표]
                승률: {win_rate}%
                픽률: {pick_rate}% (전체 하위 10% 수준)
                밴률: {ban_rate}%
            
                [분석 요구사항]
                1. 메타 현황 분석
                   - 현재 패치 {patch}에서의 챔피언 위치
                   - 낮은 픽률의 메타적 원인 파악
                   - 티어 {tier} 수준에서의 평가
            
                2. 통계적 의미 분석
                   - {win_rate}% 승률이 가지는 의미
                   - {pick_rate}% 픽률과 {ban_rate}% 밴률의 상관관계
            
                3. 실전적 가치 평가
                   - {position} 포지션에서의 특화된 역할
                   - 현재 메타에서의 활용 가능성
                   - 승률과 픽률의 격차가 주는 시사점
            
                4. 전략적 함의
                   - 낮은 픽률 속 숨겨진 가치
                   - 특정 상황에서의 강점
                   - 향후 메타 변화에 따른 전망

                [작성 지침]
                - 공백 포함 정확히 {max_chars}자 이내로 작성
                - '~습니다', '~했는데요' 체를 사용한 자연스러운 서술
                - 낮은 픽률이 가진 특별한 의미에 초점
                - 데이터를 기반으로 한 객관적 분석
                - 프로 경기의 특수성을 고려한 해석
                - 한국어 챔피언명({champion_kr_name}) 사용
                - 독자가 이해하기 쉬운 설명 방식

                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "text": "상세한 분석 내용 ({max_chars}자 이내)"
                }}

                {format_instructions}
                """
        )

        self.fourth_page_template = PromptTemplate(
            input_variables=[
                "champion_kr_name", "opp_kr_name", "position",
                "gold_diff_data", "exp_diff_data",
                "time_frames", "max_chars", "stats", "stats_values", "label_mapping"
            ],
            partial_variables={"format_instructions": self.parsers['fourth_page'].get_format_instructions()},
            template="""
                다음은 {champion_kr_name}와 {opp_kr_name}의 {position} 포지션 대결 데이터입니다.
                시간대별 성장 비교와 자원 획득 차이를 분석하여 ({max_chars})자 이내의 심층 분석 기사를 작성해주세요:

                [대결 구도]
                아군 챔피언: {champion_kr_name}
                상대 챔피언: {opp_kr_name}
                포지션: {position}
                상대와의 차이 칼럼: {stats}
                상대와의 차이 데이터: {stats_values}
                한글 칼럼 명: {label_mapping}

                [시간대별 데이터]
                시간 구간: {time_frames} (10분, 15분, 20분, 25분)
                골드 획득 추이: {gold_diff_data}
                경험치 획득 추이: {exp_diff_data}

                [분석 요구사항]
                1. 시간대별 시계열 데이터 분석
                - 초반 라인전 분석 (0~10분)
                - 중반 운영 비교 (10~20분)
                - 후반 영향력 비교 (20~25분)
                   
                2. 상대 챔피언과의 스탯 비교
                - kill, death, assist
                - 중반 운영 비교 (10~20분)
                - 후반 영향력 비교 (20~25분)

                [작성 지침]
                - 정확히 {max_chars}자 이내로 작성
                - '~습니다', '~했는데요' 체를 사용한 자연스러운 서술
                - 시간대별 변화를 중심으로 한 순차적 분석
                - 두 챔피언의 특성을 고려한 맥락적 해석
                - 전문성과 가독성의 균형 유지
                - 핵심 변곡점에 대한 명확한 설명

                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "text": "상세한 분석 내용 ({max_chars}자 이내)"
                }}
                {format_instructions}
                """
        )

        self.fifth_page_template = PromptTemplate(
            input_variables=[
                "champion_kr_name", "opp_kr_name", "position",
                "gold_diff_data", "exp_diff_data",
                "time_frames", "max_chars", "stats", "stats_values", "label_mapping"
            ],
            partial_variables={"format_instructions": self.parsers['fifth_page'].get_format_instructions()},
            template="""
                    다음은 {champion_kr_name}와 {opp_kr_name}의 {position} 포지션 대결 데이터입니다.
                    시간대별 성장 비교와 자원 획득 차이를 분석하여 ({max_chars})자 이내의 심층 분석 기사를 작성해주세요:

                    [대결 구도]
                    아군 챔피언: {champion_kr_name}
                    상대 챔피언: {opp_kr_name}
                    포지션: {position}
                    상대와의 차이 칼럼: {stats}
                    상대와의 차이 데이터: {stats_values}
                    한글 칼럼 명: {label_mapping}

                    [시간대별 데이터]
                    시간 구간: {time_frames} (10분, 15분, 20분, 25분)
                    골드 획득 추이: {gold_diff_data}
                    경험치 획득 추이: {exp_diff_data}

                    [분석 요구사항]
                    1. 시간대별 시계열 데이터 분석
                    - 초반 라인전 분석 (0~10분)
                    - 중반 운영 비교 (10~20분)
                    - 후반 영향력 비교 (20~25분)

                    2. 상대 챔피언과의 스탯 비교
                    - kill, death, assist
                    - 중반 운영 비교 (10~20분)
                    - 후반 영향력 비교 (20~25분)

                    [작성 지침]
                    - 정확히 {max_chars}자 이내로 작성
                    - '~습니다', '~했는데요' 체를 사용한 자연스러운 서술
                    - 시간대별 변화를 중심으로 한 순차적 분석
                    - 두 챔피언의 특성을 고려한 맥락적 해석
                    - 전문성과 가독성의 균형 유지
                    - 핵심 변곡점에 대한 명확한 설명

                    응답은 반드시 다음 JSON 형식을 따라야 합니다:
                    {{
                        "text": "상세한 분석 내용 ({max_chars}자 이내)"
                    }}
                    {format_instructions}
                """
        )

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
            'second_page': self.second_page_template | self.llm | self.parsers['second_page'],
            'third_page': self.third_page_template | self.llm | self.parsers['third_page'],
            'fourth_page': self.fourth_page_template | self.llm | self.parsers['fourth_page'],
            'fifth_page': self.fifth_page_template | self.llm | self.parsers['fifth_page']
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
        champion_stats = self.database.get_champion_rate_table(
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

    def generate_third_page_article(self, game_df, player_name, max_chars):
        player_data = game_df[game_df['playername'] == player_name].iloc[0]
        patch = self.meta_data.anomaly_info.get("patch")
        champion_stats = self.database.get_champion_pick_rate_info(
            player_data['name_us'],
            patch,
            player_data['position']
        )
        article_data = {"champion_kr_name": champion_stats['name_kr'],
                        "position": player_data['position'],
                        "tier": champion_stats['tier'],
                        "pick_rate": champion_stats['pick_rate'],
                        "ban_rate": champion_stats['ban_rate'],
                        "win_rate": champion_stats['win_rate'],
                        "ranking": champion_stats['ranking'],
                        "patch": patch,
                        "max_chars": max_chars
                        }
        result = self.chains['third_page'].invoke(article_data)
        return result['text']


    def generate_fourth_page_article(self, game_df, player_name, max_chars):
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
            print(radar_stats)
            article_data = {
                **comparison_data,
                'stats': radar_stats['stats'],
                'stats_values': radar_stats['stats_values'],
                'label_mapping': radar_stats['label_mapping'],
                'max_chars': max_chars
            }
            result = self.chains['fourth_page'].invoke(article_data)
            return result['text']
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