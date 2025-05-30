import os
import shutil
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from ImageModifier.image_utils import BaseContentProcessor
from Ai.LangChain.article_generator import ArticleGenerator

class MatchResult(BaseContentProcessor):

    def __init__(self, database, meta_data, article_generator, pick_rate):
        super().__init__(database, meta_data)
        self.database = database
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info
        self.pick_rate = pick_rate

        self.assets_dir = Path(__file__).parent.parent / "Assets" / "MatchResult"
        self.title_background_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "title.png"
        self.main_background_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "main.png"
        self.set_result_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "set_result.png"
        self.gradient_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "gradient.png"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "MatchResult"

        #properties
        self.score_font_size = self.properties.get("match_result_score_font_size")
        self.player_name_font_size = self.properties.get("match_result_player_name_font_size")
        self.title_font_size = self.properties.get("title_font_size")

        self.article_generator = article_generator

    def title_page(self, match_id, player_name, detection_type):
        background = Image.open(self.title_background_dir)
        game_df = self.database.get_game_data(match_id)
        player_team = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        self.database.get_all_team_slug()
        opp_team_name = game_df[game_df['teamname'] != player_team]['teamname'].iloc[0]
        game_date = datetime.strftime(game_df['game_date'].iloc[0], "%Y/%m/%d")
        league_title = f"{game_df['game_year'].iloc[0]} {game_df['league'].iloc[0]} {game_df['split'].iloc[0]}"

        #선수
        player_image = self.get_player_image(player_name, 520, 497)
        background.paste(player_image, (470, 399), player_image)

        #팀로고
        player_team_icon = self.open_team_icon(player_team)
        opp_team_icon = self.open_team_icon(opp_team_name)
        player_team_icon = self.resize_image(player_team_icon, 200, 200)
        opp_team_icon = self.resize_image(opp_team_icon, 200, 200)
        background.paste(player_team_icon, (134,300), player_team_icon)
        background.paste(opp_team_icon, (134,666), opp_team_icon)

        #스코어, 리그, 날짜
        player_team_score, opp_team_score = self.database.get_sets_score(match_id, player_team, opp_team_name)
        self.add_text_box(background, player_team_score, 395, 327, 96, (255,255,255), self.anton_font_path)
        self.add_text_box(background, opp_team_score, 395, 693, 96, (255,255,255), self.anton_font_path)
        self.add_text_box(background, league_title, 134, 542, 45, (255,255,255), self.noto_font_bold_kr_path)
        self.add_text_box(background, game_date, 822, 209, 36, (255,255,255), self.noto_font_bold_kr_path)

        # 메인 제목
        title = self.article_generator.generate_match_result_title(detection_type, game_df, player_name)
        self.add_first_page_title(background, title)
        self.add_logo(background)
        self.save_image(background, match_id, "1")


    def set_page(self, match_id, player_name):
        today_date = datetime.today().date().strftime("%y_%m_%d")
        game_df = self.database.get_game_data(match_id)
        player_team = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        opp_team_name = game_df[game_df['teamname'] != player_team]['teamname'].iloc[0]
        game_id_list = self.database.get_sets_game_id(match_id, player_team, opp_team_name)['gameid']
        print(game_id_list)
        print(match_id, " ", player_name)
        page_index = 2
        for index, game_id in enumerate(game_id_list):
            save_path = self.output_dir / today_date / match_id / f"{page_index+index}.png"
            if game_id == match_id:
                self.one_set_page(game_id, player_name, save_path, True)
            else:
                self.one_set_page(game_id, player_name, save_path)
        return page_index + len(game_id_list) - 1

    def one_set_page(self, match_id, player_name, save_path, highlight_player=False):
        background = Image.open(self.set_result_dir)
        game_df = self.database.get_game_data(match_id)
        player_team_name = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        opp_team_name = game_df[game_df['teamname'] != player_team_name]['teamname'].iloc[0]

        # 팀 로고
        player_team_icon = self.open_team_icon(player_team_name)
        opp_team_icon = self.open_team_icon(opp_team_name)

        player_team_icon = self.resize_image(player_team_icon, 150, 150)
        opp_team_icon = self.resize_image(opp_team_icon, 150, 150)
        background.paste(player_team_icon, (158, 230), player_team_icon)
        background.paste(opp_team_icon, (771, 230), opp_team_icon)
        
        # 세트 정보, 승패 정보
        win_text = Image.open(self.assets_dir / "win.png")
        lose_text = Image.open(self.assets_dir / "lose.png")
        player_team_result = game_df[game_df['playername'] == player_name]['result'].iloc[0]
        set_info = f"{game_df[game_df['playername'] == player_name]['game'].iloc[0]} SET"
        if player_team_result == 1:
            background.paste(win_text, (364, 279), win_text)
            background.paste(lose_text, (663, 279), lose_text)
        else:
            background.paste(lose_text, (364, 279), lose_text)
            background.paste(win_text, (663, 279), win_text)
        self.add_text_box(background, set_info, 472, 275, 50, "#C89B3C", self.noto_font_bold_kr_path)

        # 경기 결과 테이블
        player_team = game_df[(game_df['teamname'] == player_team_name)]
        opp_player_team = game_df[(game_df['teamname'] == opp_team_name)]
        self.draw_result_table(background, player_team, opp_player_team, (42, 412))

        # 경기 전체 테이블
        mvp_score = self.database.calculate_mvp_score(game_df)
        table = Image.open(self.assets_dir / "table.png")
        background.paste(table, (42, 534), table)
        draw = ImageDraw.Draw(background)
        self.draw_ban_info(background, player_team, opp_player_team)
        if highlight_player:
            self.draw_table_info(background, player_team, opp_player_team, draw, mvp_score, player_name)
        else:
            self.draw_table_info(background, player_team, opp_player_team, draw, mvp_score)
        self.add_logo(background)
        background.save(save_path)

    def pick_rate_page(self, match_id, player_name, page_index):
        self.pick_rate.third_page(match_id, player_name, page_index, page_index+1, self.output_dir)
        self.pick_rate.fourth_page(match_id, player_name, page_index+2, page_index+3, self.output_dir)
        self.pick_rate.fifth_page(match_id, player_name, page_index+4, self.output_dir)
        return page_index+4

    # 전체 경기 평점 페이지 (맨 마지막 페이지)
    def main_page(self, match_id, player_name, page_index):
        background = Image.open(self.main_background_dir)
        game_df = self.database.get_game_data(match_id)
        player_team_name = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        opp_team_name = game_df[game_df['teamname'] != player_team_name]['teamname'].iloc[0]

        #팀 로고
        player_team_icon = self.open_team_icon(player_team_name)
        opp_team_icon = self.open_team_icon(opp_team_name)
        player_team_icon = self.resize_image(player_team_icon, 150, 150)
        opp_team_icon = self.resize_image(opp_team_icon, 150, 150)
        background.paste(player_team_icon, (159, 224), player_team_icon)
        background.paste(opp_team_icon, (772, 224), opp_team_icon)

        # 스코어
        player_team_score, opp_team_score = self.database.get_sets_score(match_id, player_team_name, opp_team_name)
        self.add_text_box(background, f"{player_team_score} - {opp_team_score}", 459, 224, 96, (255, 255, 255), self.anton_font_path)

        #이름 및 테이블
        overall_mvp_score = self.database.calculate_overall_mvp_score(game_df, match_id, player_name)
        self.draw_overall_mvp_table(background, overall_mvp_score, player_team_name, opp_team_name)
        self.add_logo(background)
        self.save_image(background, match_id, page_index+1)

    def draw_overall_mvp_table(self, background, overall_mvp_df, player_team, opp_team):
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        row_start_y = 448
        row_height = 147
        left_score_x = 380
        right_score_x = 640
        left_name_x = 138
        right_name_x = 790
        for i, position in enumerate(positions):
            current_y = row_start_y + (i * row_height)
            blue_player_data = overall_mvp_df[(overall_mvp_df['position'] == position) & (overall_mvp_df['teamname'] == player_team)].iloc[0]
            blue_mvp_score = blue_player_data['mvp_score']
            blue_player_name = blue_player_data['playername']
            red_player_data = overall_mvp_df[(overall_mvp_df['position'] == position) & (overall_mvp_df['teamname'] == opp_team)].iloc[0]
            red_mvp_score = red_player_data['mvp_score']
            red_player_name = red_player_data['playername']
            self.add_text_box_resize(background, f"{blue_mvp_score:.1f}", left_score_x, current_y, 88, 57, color=(255,255,255), font_path=self.anton_font_path, max_font_size=40)
            self.add_text_box_resize(background, f"{red_mvp_score:.1f}", right_score_x, current_y, 88, 57, color=(255,255,255), font_path=self.anton_font_path, max_font_size=40)
            self.add_text_box_resize(background, blue_player_name, left_name_x, current_y, 183, 72, color=(255,255,255), font_path=self.anton_font_path, max_font_size=48)
            self.add_text_box_resize(background, red_player_name, right_name_x, current_y, 183, 72, color=(255,255,255), font_path=self.anton_font_path, max_font_size=48)
        return background

    def draw_result_table(self, background, player_team, opp_player_team, position):
        if player_team['result'].iloc[0] == 1:
            result_table = Image.open(self.assets_dir / "win_result.png")
        else:
            result_table = Image.open(self.assets_dir / "defeat_result.png")
        win_team_name = player_team['teamname'].iloc[0]
        result_draw = ImageDraw.Draw(result_table)
        font = ImageFont.truetype(self.noto_font_bold_kr_path, 18)
        blue_bbox = font.getbbox(win_team_name)
        blue_text_width = blue_bbox[2] - blue_bbox[0]
        blue_x = 300 - (blue_text_width / 2)
        result_draw.text((blue_x, 15), win_team_name, font=font, fill='#AAA9B7')

        red_team_name = opp_player_team['teamname'].iloc[0]
        red_bbox = font.getbbox(red_team_name)
        red_text_width = red_bbox[2] - red_bbox[0]
        red_x = 700 - (red_text_width / 2)
        result_draw.text((red_x, 15), red_team_name, font=font, fill='#AAA9B7')
        background.paste(result_table, position, result_table)
    
    #왼쪽이 무조건 플레이어팀
    def draw_table_info(self, background, player_team, opp_player_team, draw, mvp_score, highlight_player=None):
        font = ImageFont.truetype(self.noto_font_bold_kr_path, 20)
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        row_start_y = 598
        row_height = 91
        left_side = {
            'champion': 60,
            'player': 210,
            'kda': 310,
            'damage': 430
        }
        right_side = {
            'damage': 570,
            'kda': 690,
            'player': 820,
            'champion': 920
        }
        for i, position in enumerate(positions):
            current_y = row_start_y + (i * row_height)
            blue_pos_data = player_team[player_team['position'] == position].iloc[0]
            blue_champion_icon = Image.open(self.champion_icon_dir / f"{blue_pos_data['name_us']}.png")
            blue_champion_icon = self.resize_image(blue_champion_icon, 100, 60)
            blue_champion_icon = self.add_gradient_border(blue_champion_icon, 10)
            background.paste(blue_champion_icon, (left_side['champion'], current_y))

            blue_kda = f"{blue_pos_data['kills']} / {blue_pos_data['deaths']} / {blue_pos_data['assists']}"
            blue_score = mvp_score[mvp_score['playername'] == blue_pos_data['playername']]['mvp_score'].iloc[0]
            if blue_pos_data['playername'] == highlight_player:
                color = "#ED2A2A"
            else:
                color = "white"
            draw.text((left_side['kda'], current_y + 20), blue_kda, font=font, fill=color)
            draw.text((left_side['player'], current_y + 5), str(blue_pos_data['playername']), font=font, fill=color)
            draw.text((left_side['player']+10, current_y + 40), f"{blue_score:.1f}", font=font, fill='#FFD700')
            blue_damage = "{:,}".format(blue_pos_data['damagetochampions'])
            draw.text((left_side['damage'], current_y + 20), blue_damage, font=font, fill=color)

            red_pos_data = opp_player_team[opp_player_team['position'] == position].iloc[0]
            red_champion_icon = Image.open(self.champion_icon_dir / f"{red_pos_data['name_us']}.png")
            red_champion_icon = self.resize_image(red_champion_icon, 100, 60)
            red_champion_icon = self.add_gradient_border(red_champion_icon, 10)
            background.paste(red_champion_icon, (right_side['champion'], current_y))
            if red_pos_data['playername'] == highlight_player:
                color = "#ED2A2A"
            else:
                color = "white"
            draw.text((right_side['damage'], current_y + 20),
                      "{:,}".format(red_pos_data['damagetochampions']),
                      font=font, fill=color)
            red_kda = f"{red_pos_data['kills']} / {red_pos_data['deaths']} / {red_pos_data['assists']}"
            draw.text((right_side['kda'], current_y + 20),
                      red_kda,
                      font=font, fill=color)

            red_score = mvp_score[mvp_score['playername'] == red_pos_data['playername']]['mvp_score'].iloc[0]
            draw.text((right_side['player'], current_y + 5), str(red_pos_data['playername']), font=font, fill=color)
            draw.text((right_side['player']+10, current_y + 40), f"{red_score:.1f}", font=font, fill='#FFD700')

    def draw_ban_info(self, background, player_team, opp_player_team):
        # 플레이팀이 왼쪽 배치
        ban_y = 471
        ban_spacing = 100
        blue_bans = [player_team.iloc[0][f'ban{i}'] for i in range(1, 6)]
        for i, ban in enumerate(blue_bans):
            if ban:
                try:
                    ban_icon = Image.open(self.champion_icon_dir / f"{ban}.png")
                    ban_icon = self.resize_image(ban_icon, 100, 60)
                    ban_icon = self.add_gradient_border(ban_icon, 10)
                    ban_icon = self.convert_to_grayscale(ban_icon)
                    background.paste(ban_icon, (42 + i * ban_spacing, ban_y))
                except Exception as e:
                    print(f"블루팀 ban 이미지 처리 중 오류: {e}")
        red_bans = [opp_player_team.iloc[0][f'ban{i}'] for i in range(1, 6)]
        for i, ban in enumerate(reversed(red_bans)):
            if ban:
                try:
                    ban_icon = Image.open(self.champion_icon_dir / f"{ban}.png")
                    ban_icon = self.resize_image(ban_icon, 100, 60)
                    ban_icon = self.add_gradient_border(ban_icon, 10)
                    ban_icon = self.convert_to_grayscale(ban_icon)
                    background.paste(ban_icon, (938 - i * ban_spacing, ban_y))
                except Exception as e:
                    print(f"레드팀 ban 이미지 처리 중 오류: {e}")

    def open_team_icon(self, player_team_name):
        player_team_name = self.database.get_team_icon_name_by_oracle_elixir(player_team_name)
        image = Image.open(self.team_icon_dir / f"{player_team_name}.png")
        return image.convert('RGBA')

    # match_result detection_type -> general, penta_kill, unmatch_line, two_bottom_choice
    def run(self, match_id, player_name, detection_type):
        # try:
        self.title_page(match_id, player_name, detection_type)
        last_page_index = self.set_page(match_id, player_name)
        last_page_index = self.pick_rate_page(match_id, player_name, last_page_index)
        self.main_page(match_id, player_name, last_page_index)
        # except Exception as e:
        #     today_date = datetime.today().date().strftime("%y_%m_%d")
        #     output_path = self.output_dir / today_date / match_id
        #     print(e)
        #     if os.path.exists(output_path):
        #         shutil.rmtree(output_path)

    def test_run(self, match_id, player_name, detection_type):
        self.title_page(match_id, player_name, detection_type)
        last_page = self.set_page(match_id, player_name)
        self.main_page(match_id, player_name, last_page)
