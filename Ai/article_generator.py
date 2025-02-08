
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
            template="""
                당신은 리그오브레전드 프로게임 분석 전문가입니다. 
                다음은 낮은 픽률의 챔피언을 선택한 경기에 대한 정보입니다. 
                예시 탬플릿을 활용하여 ({max_chars})자 이내의 자극적인 제목을 생성해주세요:
    
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
    
                [예시 템플릿]
                - "Faker의 픽률 ^0.1%^ 아지르" (20자)
                - "^픽률 0.1%^의 스카너 픽?" (17자)
                - "의외로 개사기인 픽률 ^0.1%^ 스카너" (20자)
                - "이걸? 픽률 ^0.1%^ 스카너" (20자)
                - "^레전드 픽^ 발생 Faker의 픽률 0.1% 스카너" (13자)
    
                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "title": "제목 ({max_chars}자 이내, 강조 표시 ^ 포함)"
                }}
                {format_instructions}
            """
        )

        self.second_page_template = PromptTemplate(
            input_variables=["game_date", "league", "set", "blue_team_name", "red_team_name",
                    "player_name", "champion_name", "opp_player", "opp_champion",
                    "patch_version", "pick_rate", "player_team", "mvp_champion",
                    "mvp_player", "mvp_score", "max_chars"],
            partial_variables={"format_instructions": self.parsers['second_page'].get_format_instructions()},
            template="""
                다음 주어진 경기 데이터를 바탕으로 템플릿을 참고하여 ({max_chars})이내의 상세한 경기 분석 기사를 작성해주세요:
                
                
                 [입력 데이터 설명]
                - 경기 날짜: {game_date}
                - 리그명: {league}
                - 세트 번호: {set}
                - 블루 진영 팀명: {blue_team_name}
                - 레드 진영 팀명: {red_team_name}
                - 분석 대상 선수명: {player_name}
                - 분석 대상 선수의 챔피언명(한글): {champion_name}
                - 상대 선수명: {opp_player}
                - 상대 선수의 챔피언명(한글): {opp_champion}
                - 패치 버전: {patch_version}
                - 챔피언 픽률: {pick_rate}
                - 분석 대상 선수의 소속팀: {player_team}
                - MVP 선수명: {mvp_player}
                - MVP 선수의 챔피언명(한글): {mvp_champion}
                - MVP 점수: {mvp_score}
            
                [예시 템플릿]
                (경기 정보)
                {game_date}일 {league} {set}세트 {blue_team_name}과 {red_team_name}의 경기가 진행되었습니다.
                (라인전 구도)
                {player_name}은 {champion_name}을 선택 하여 {opp_player}의 {opp_champion}을 상대하였습니다.
                (Mvp 분석)
                경기는 {player_team}의 승리로 마무리 되었고 {mvp_champion}가 자체 스코어 {mvp_score}점으로 mvp로 선정되었습니다.
                
                [작성 규칙]
                - 공백을 포함하여 정확히 {max_chars}자 이내로 작성 (현재 {max_chars}자까지 허용)
                - 글자 수는 모든 공백과 특수문자를 포함하여 계산됩니다
                - 각 섹션을 자연스럽게 연결하여 하나의 기사로 통합
                - 문장 사이에 관련 분석을 추가하여 풍부한 내용 구성
                - '~했습니다', '~되었습니다' 종결어미 사용
                - champion 명칭은 한국어 사용(name_kr)
                
                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "text": "상세한 분석 내용 ({max_chars}자 내외)"
                    "chars": "생성한 text의 length"
                }}
                
                {format_instructions}
                """
        )

        self.third_page_template = PromptTemplate(
            input_variables=[
                "champion_kr_name", "opp_kr_name", "position",
                "gold_diff_data", "exp_diff_data",
                "time_frames", "max_chars", "stats", "player_stats_values", "opponent_stats_values", "label_mapping"
            ],
            partial_variables={"format_instructions": self.parsers['third_page'].get_format_instructions()},
            template="""
                        당신은 리그오브레전드 프로게임 분석 전문가입니다. 다음은 리그오브레전드 경기 {champion_kr_name}와 {opp_kr_name}의 {position} 포지션 대결 데이터입니다.
                        예시 탬플릿을 포함하여 ({max_chars})자 이내의 심층 분석 기사를 작성해주세요:

                        [대결 구도]
                        아군 챔피언: {champion_kr_name}
                        상대 챔피언: {opp_kr_name}
                        포지션: {position}
                        칼럼 순서: {stats}
                        한글 칼럼 명: {label_mapping}
                        {champion_kr_name} : {player_stats_values}
                        {opp_kr_name} : {opponent_stats_values}

                        [라인별 중요 지표]
                        탑, 미드 : '분당 받은 피해량', '가한 피해량'
                        정글 : '오브젝트 획득'
                        원딜 : '가한 피해량', '라인전 점수'
                        서포터 : '시야 점수'

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
                        - kill, death, assist, 라인별 중요 지표
                        - 중반 운영 비교 (10~20분)
                        - 후반 영향력 비교 (20~25분)

                        [예시 템플릿]
                        (라인별 중요 지표 비교)
                        {champion_kr_name}은 ()킬 ()데스 ()어시스트를 기록하며 {opp_kr_name}를 상대로 좋은 모습을 보여주었습니다. 
                        (상대 챔피언과의 기본 지표 비교)
                        또한 {position}의 중요한 지표인 (중요 지표)에서 {opp_kr_name}를 앞섰습니다.
                        (시간대별 데이터 설명)
                        {champion_kr_name}은 {opp_kr_name}를 상대로 초반 (골드, 경험치)에 우위를 가져갔습니다. 게임 중반과 후반에는 (골드, 경험치)에서 (값)의 차이를 벌리며 안정적인 플레이를 보여주었습니다.

                        [작성 지침]
                        - 공백을 포함하여 정확히 {max_chars}자 이내로 작성 (현재 {max_chars}자까지 허용)
                        - 글자 수는 모든 공백과 특수문자를 포함하여 계산 
                        - 각 섹션을 자연스럽게 연결하여 하나의 기사로 통합
                        - 구체적인 통계 수치를 활용한 설득력 있는 분석
                        - {max_chars}자 이내 예시 템플릿 사이에 관련 분석을 추가하여 풍부한 내용 구성
                        - 자연스러운 한국어를 사용
                        - 리그오브레전드 게임임을 고려한 단어 선택 (그의 -> {champion_kr_name}의)
                        - 필요시 [예시 템플릿] 내부 표현 변경 가능

                        응답은 반드시 다음 JSON 형식을 따라야 합니다:
                        {{
                            "text": "상세한 분석 내용 ({max_chars}자 이내)"
                        }}
                        {format_instructions}
                        """
        )

        self.fourth_page_template = PromptTemplate(
            input_variables=["champion_kr_name", "position", "tier", "pick_rate", "ban_rate", "win_rate", "ranking", "max_chars", "patch", "opponent_champion"],
            partial_variables={"format_instructions": self.parsers['fourth_page'].get_format_instructions()},
            template="""
                다음은 패치 {patch}에서 특이하게 낮은 픽률을 보이는 리그오브레전드 챔피언의 상세 데이터입니다.
                낮은 픽률임에도 프로경기에서 사용된 {opponent_champion}을 상대로 픽되었습니다.
                예시 탬플릿을 포함하여 ({max_chars})자 이내의 전략적 분석 카드뉴스를 작성해주세요:
            
                [챔피언 기본 정보]
                챔피언명: {champion_kr_name}
                포지션: {position}
                티어: {tier}
                상대 챔피언: {opponent_champion}
            
                [핵심 지표]
                승률: {win_rate}%
                픽률: {pick_rate}% (전체 하위 10% 수준)
                밴률: {ban_rate}%
                랭킹: {ranking}
                
                [분석 요구사항]
                1. 메타 현황 분석
                   - 현재 패치 {patch}에서의 챔피언 위치
                   - 티어 {tier} 수준에서의 평가
                
                2. 통계적 의미 분석
                   - {win_rate}% 승률이 가지는 의미
                   - {pick_rate}% 픽률과 {ban_rate}% 밴률의 상관관계
                
                3. 전략적 함의
                   - 낮은 픽률 속 숨겨진 가치
                   - 특정 상황에서의 강점
                   - 향후 메타 변화에 따른 전망
                
                [예시 템플릿]
                (stat 설명)
                {champion_kr_name}은 {patch}패치에서 {tier}티어, {pick_rate}%픽률을 보여주고 있습니다.
                (낮은 픽률 설명)
                이번 경기에서는 현재 메타에서 잘 사용하지 않은 {position} {champion_kr_name}픽이 주목 받았는데요 {opponent_champion}을 상대로 경기를 승리하며 새로운 가능성을 보여주었습니다.
                (승률과 밴률 설명)
                {win_rate}%의 승률과 {ban_rate}%의 밴률로 (승률과 밴률의 특징 설명)를 보여 주고 있습니다.
                
                [작성 지침]
                - 공백을 포함하여 정확히 {max_chars}자 이내로 작성 (현재 {max_chars}자까지 허용)
                - 글자 수는 모든 공백과 특수문자를 포함하여 계산됩니다
                - 각 섹션을 자연스럽게 연결하여 하나의 기사로 통합
                - 문장 사이에 관련 분석을 추가하여 풍부한 내용 구성
                - 낮은 픽률이 가진 특별한 의미에 초점
                - 자연스러운 한국어를 사용
                - 리그오브레전드 게임임을 고려한 단어 선택 (그의 -> {champion_kr_name}의)

                응답은 반드시 다음 JSON 형식을 따라야 합니다:
                {{
                    "text": "상세한 분석 내용 ({max_chars}자 이내)"
                    "chars": "생성한 text의 length"
                }}

                {format_instructions}
                """
        )



        self.fifth_page_template = PromptTemplate(
            input_variables=[
                "player_name", "player_champion_kr", "position", "counters", "max_chars"
            ],
            partial_variables={"format_instructions": self.parsers['fifth_page'].get_format_instructions()},
            template="""
                    당신은 리그오브레전드 프로게임 분석 전문가입니다.
                    다음은 {player_champion_kr}가 {position} 포지션에서 상대하기 쉬운 챔피언의 데이터입니다.
                    예시 탬플릿을 포함하여 ({max_chars})자 이내의 {player_champion_kr}를 추천하는 상세한 분석 글을 작성해주십시오:
                  
                    [카운터 정보]
                    - 아군 챔피언: {player_champion_kr}
                    - 상대 하기 쉬운 챔피언: {counters}
                    - 포지션: {position}
                    - 상대하기 쉬운 챔피언 세부 정보:
                       - name_kr: 챔피언 한글 이름
                       - win_rate: 아군 챔피언의 승률
                       - games_played: 총 대전 게임 수
                       - kda_diff: 라인전 평균 KDA 차이 (양수일 수록 우위)
                       - counter_score: 카운터 점수 (자체적으로 계산한 승률, 골드 차이, 경험치 차이 종합)
                       
                    [작성 방향]
                    1. 챔피언 추천 근거
                       - {player_champion_kr}가 상대하기 쉬운 챔피언들의 공통된 특징
                       - 각각의 상대 챔피언을 상대로 {player_champion_kr}가 가지는 이점
                       - 프로 경기 데이터 기반의 구체적인 승률과 KDA 우위 분석
                    
                    2. 실전 활용 전략
                       - {player_champion_kr}의 강점을 극대화하는 운영 방법
                       - 상대 챔피언별 맞춤형 상대법
                       - 팀 구성에서 {player_champion_kr}가 기여할 수 있는 역할
                       
                    3. 챔피언 추천
                       - 상대하기 쉬운 챔피언이 등장한 경우 {player_champion_kr}의 사용을 추천하는 문장
                    
                    [예시 템플릿]
                    (프로경기 전적 설명)
                    {player_champion_kr}은 프로 경기에서 (상대 하기 쉬운 챔피언의 모든 name_kr) 상대로 좋은 모습을 보여주고 있습니다.
                    (데이터를 언급하여 설명)
                    특히 (상대 하기 쉬운 챔피언 name_kr)을 상대로 (승률 or kda or 카운터 점수)로 좋은모습을 보여주었는데요 
                    (챔피언의 강점 언급)
                    {player_champion_kr}의 (챔피언 강점)때문으로 보입니다.
                    (마무리 멘트)
                    1 : (추천 상황 or 상대하기 쉬운 챔피언 name_kr 언급) {player_champion_kr}을 픽해보는건 어떨까요?
                    2 : {player_name}의 깜짝 픽 {player_champion_kr}을 여러분은 어떻게 생각하시나요?
                    3 : 이번주는 (상대하기 쉬운 챔피언 name_kr 언급)이 등장한다면 {player_champion_kr}을 픽해보시죠.
                     
                    [작성 지침]
                    - 공백을 포함하여 정확히 {max_chars}자 이내로 작성 (현재 {max_chars}자까지 허용)
                    - 글자 수는 모든 공백과 특수문자를 포함하여 계산 
                    - 각 섹션을 자연스럽게 연결하여 하나의 기사로 통합
                    - {max_chars}자 이내 [예시 템플릿 사이]에 관련 분석을 추가하여 풍부한 내용 구성
                    - 필요시 [예시 템플릿] 내부 표현 변경 가능
                    - 자연스러운 한국어를 사용
                    - 리그오브레전드 게임임을 고려한 단어 선택 (그의 -> {player_champion_kr}의)
                    
                    응답은 반드시 다음 JSON 형식을 따라야 합니다:
                    {{
                        "text": "상세한 분석 내용 ({max_chars}자 이내)"
                        "chars": "생성한 text의 length"
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
        print(template_variables)

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
        patch = self.meta_data.anomaly_info.get("patch")
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
        counter_info = self.database.get_counter_champion(player_data['name_us'], player_data['position'], self.meta_data.anomaly_info.get("patch"))
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