import os
import shutil

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import datetime
from Ai.LangChain.article_generator import ArticleGenerator
from ImageModifier.image_utils import BaseContentProcessor
from AnomalyDetection.plt_draw import PltDraw


class PickRate(BaseContentProcessor):

    def __init__(self, database, meta_data, article_generator, patch):
        super().__init__(database, meta_data)
        self.database = database
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info
        self.patch = patch
        self.background_dir = Path(__file__).parent.parent / "Assets" / "Image" / "background"
        self.pick_rate_assets_dir = Path(__file__).parent.parent / "Assets" / "PickRate"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "PickRate"
        self.main_font_size = self.properties.get("main_font_size")
        self.main_line_spacing = self.properties.get("main_line_spacing")
        self.title_font_size = self.properties.get("title_font_size")
        self.black = self.properties.get("black")
        self.tier_color = self.properties.get("tier_color")
        self.plt_draw = PltDraw(database, self.patch)
        self.article_generator = article_generator

    def first_page(self, match_id, player_name):
        background_path = self.pick_rate_assets_dir / "1" / "background.png"
        game_df = self.database.get_game_data(match_id)
        name_us = game_df[game_df['playername'] == player_name]['name_us'].iloc[0]
        background = Image.open(background_path)

        #선수 얼굴
        player_path = self.get_player_image_path(player_name)
        player_image = Image.open(player_path)
        player_image = self.resize_with_crop_image(player_image, 400, 400)
        player_image = self.add_bottom_gradient(player_image)
        background.paste(player_image, (544, 383), player_image)

        #챔피언 얼굴
        champion_icon = Image.open(self.champion_icon_dir / f"{name_us}.png")
        champion_icon = self.resize_image(champion_icon, 350,350)
        champion_icon = self.add_gradient_border(champion_icon)
        background.paste(champion_icon, (165, 433), champion_icon)

        #그라데이션
        background = self.add_gradient_box(background, 90, 230, 900, 700, 190, 40)

        #기사 제목
        text = self.article_generator.generate_first_page_article(game_df, player_name, 15)
        self.add_first_page_title(background, text, 100, 990)
        self.add_logo(background)
        self.save_image(background, match_id, "1")

    def second_page(self, match_id, player_name):
        background_path = self.pick_rate_assets_dir / "2" / "background2.png"
        table_path = self.pick_rate_assets_dir / "2" / "Table2.png"
        game_df = self.database.get_game_data(match_id)
        win_team = game_df[(game_df['result'] == 1)]
        lose_team = game_df[(game_df['result'] == 0)]
        background = Image.open(background_path)

        #경기 승리 정보
        self.draw_result_table(background, win_team, lose_team, (42, 202))

        #경기 스탯 정보 kda, score 등등
        mvp_score = self.database.calculate_mvp_score(game_df)
        table = Image.open(table_path)
        background.paste(table, (42, 326), table)
        draw = ImageDraw.Draw(background)
        self.draw_ban_info(background, win_team, lose_team)
        self.draw_match_result_table(background, win_team, lose_team, draw, mvp_score)

        box_size = (995,472)
        max_chars = self.calculate_text_max_chars(self.noto_font_bold_kr_path, self.main_font_size, box_size)
        main_text = self.article_generator.generate_second_page_article(game_df, player_name, max_chars)
        self.add_main_text(background, main_text, (45, 850), box_size, 45)
        self.add_logo(background)
        self.save_image(background, match_id, "2")

    def third_page(self, match_id, player_name, left_save_name="3", right_save_name="4", output_dir=None):
        game_df = self.database.get_game_data(match_id)
        left_background = Image.open(self.pick_rate_assets_dir / "3" / "background.png")
        right_background = Image.open(self.pick_rate_assets_dir / "3" / "background.png")

        # 왼쪽
        # 방사형 차트
        radar_chart_path = self.plt_draw.draw_radar_chart(match_id, player_name)
        radar_chart = Image.open(radar_chart_path)
        radar_chart = self.resize_image(radar_chart, 800, 630)
        left_background.paste(radar_chart, (120,209), radar_chart)

        # 텍스트
        max_chars = self.calculate_text_max_chars(self.noto_font_bold_kr_path, self.main_font_size, (1000, 500))
        main_text = self.article_generator.generate_third_page_article(game_df, player_name, max_chars)
        self.add_main_text(left_background, main_text, (76, 850), (1000,500))

        # 오른쪽
        self.plt_draw.draw_all_series(match_id, player_name)
        today_date = datetime.today().date().strftime("%y_%m_%d")
        series_dir = self.plt_dir / "PickRate" / "Series" / today_date
        gold = Image.open(series_dir / f"{match_id}_{player_name}_goldat.png")
        exp = Image.open(series_dir / f"{match_id}_{player_name}_xpat.png")
        gold = self.resize_image(gold, 909, 528)
        exp = self.resize_image(exp, 909, 528)
        right_background.paste(gold, (82, 202), gold)
        right_background.paste(exp, (82, 752), exp)
        self.add_logo(left_background)
        self.add_logo(right_background)
        self.save_image(left_background, match_id, left_save_name, output_dir)
        self.save_image(right_background, match_id, right_save_name, output_dir)

    #챔피언 스탯
    def fourth_page(self, match_id, player_name, left_save_name="5", right_save_name="6", output_dir=None):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        stat_background = Image.open(self.pick_rate_assets_dir / "4" / "background.png")
        right_background = Image.open(self.pick_rate_assets_dir / "4" / "background.png")

        # 챔피언 아이콘, 이름
        champion_icon = Image.open(self.champion_icon_dir / f"{name_us}.png")
        champion_icon = self.resize_image(champion_icon, 175, 175)
        champion_icon = self.add_gradient_border(champion_icon, 20)
        stat_background.paste(champion_icon, (92, 281), champion_icon)
        champion_name_kr = self.database.get_name_kr(name_us)
        line_dict = {"top":"탑","jungle":"정글","mid":"미드","bottom":"원딜","support":"서포터"}
        line_kr = line_dict.get(player_df['position'])
        self.add_text_box(stat_background, champion_name_kr, 296, 281, 77, "#E2E8F0", self.noto_font_regular_path)
        self.add_text_box(stat_background, line_kr, 296, 381, 50, "#94A3B8", self.noto_font_regular_path)

        # 챔피언 통계 설명 text, 통계 테이블
        max_chars = self.calculate_text_max_chars(self.noto_font_bold_kr_path, self.main_font_size, (900, 474))
        main_text = self.article_generator.generate_fourth_page_article(game_df, player_name, max_chars)
        stat_background = self.add_main_text(stat_background, main_text, (77,806))
        champion_stats = self.database.get_champion_rate_table(name_us, self.patch.version, player_df['position'])
        stat_background = self.draw_pickrate_stat_table(stat_background, champion_stats)

        #오른쪽 픽률 그래프
        save_path = self.plt_draw.draw_pick_rates_transparent(name_us, player_df['position'])
        pick_rate_graph = Image.open(save_path)
        pick_rate_graph = self.resize_image(pick_rate_graph, 920, 920)
        right_background.paste(pick_rate_graph, (81, 259), pick_rate_graph)
        self.add_logo(stat_background)
        self.add_logo(right_background)
        self.save_image(stat_background, match_id, left_save_name, output_dir)
        self.save_image(right_background, match_id, right_save_name, output_dir)

    def fifth_page(self, match_id, player_name, save_name="7", output_dir=None):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        position = player_df['position']

        background = Image.open(self.pick_rate_assets_dir / "5" / "background.png")
        counter_info = self.database.get_counter_champion(name_us, position, self.patch.version)

        table = Image.open(self.pick_rate_assets_dir / "5" / f"table3_3.png")
        background.paste(table, (38, 58), table)
        background = self.draw_counter_table(background, player_df, counter_info)
        
        #텍스트
        max_chars = self.calculate_text_max_chars(self.noto_font_bold_kr_path, self.main_font_size, (940, 626))
        result = self.article_generator.generate_fifth_page_article_rag(match_id, player_name, max_chars)
        recommend = result['recommend']
        basic_recommend_ment = f'DLK 종합 평가 : '
        if recommend == "적극 추천":
            stamp_path = "highly_recommend.png"
        elif recommend == "추천":
            stamp_path = "recommend.png"
        elif recommend == "보류":
            stamp_path = "on_hold.png"
        stamp = Image.open(self.pick_rate_assets_dir / "5" / stamp_path)
        background.paste(stamp, (702, 1061), stamp)
        self.add_main_text(background, result['text'], (72, 626), (940, 626))
        self.add_main_text(background, basic_recommend_ment, (408, 1146), (365, 67))
        self.add_logo(background)
        self.save_image(background, match_id, save_name, output_dir)

    def draw_result_table(self, background, win_team, lose_team, position):
        result_table = Image.open(self.pick_rate_assets_dir / "2" / "result2.png")
        result_draw = ImageDraw.Draw(result_table)
        font = ImageFont.truetype(self.noto_font_bold_path, 18)
        win_team_name = win_team['teamname'].iloc[0]
        blue_bbox = font.getbbox(win_team_name)
        blue_text_width = blue_bbox[2] - blue_bbox[0]
        blue_x = 300 - (blue_text_width / 2)
        result_draw.text((blue_x, 20), win_team_name, font=font, fill='#AAA9B7')

        red_team_name = lose_team['teamname'].iloc[0]
        red_bbox = font.getbbox(red_team_name)
        red_text_width = red_bbox[2] - red_bbox[0]
        red_x = 700 - (red_text_width / 2)
        result_draw.text((red_x, 20), red_team_name, font=font, fill='#AAA9B7')
        background.paste(result_table, position, result_table)

    def draw_counter_table(self, background, player_df, counter_info):
        layout = {
            'my_champion_start_x': 125,
            'my_champion_start_y': 238,
            'start_x': 118,
            'start_y': 282,
            'row_height': 100,
            'text_offsets': {
                'name_kr': 100,
                'winrate': 290,
                'kda_diff': 490,
                'counter_score': 650,
                'games': 810
            },
            'text_y_offset': 10
        }
        colors = {
            'default': "#E2E8F0",
            'positive': '#22C55E',
            'negative': '#EF4444'
        }
        my_champion_kr = self.database.get_name_kr(player_df['name_us'])
        position_kr_list = {'top':'탑', 'jungle':'정글', 'mid':'미드', 'bottom':'바텀', 'support':'서포터'}
        my_position_kr = position_kr_list[player_df['position']]
        my_champion_icon = Image.open(self.champion_icon_dir / f"{player_df['name_us']}.png")
        my_champion_icon = self.resize_circle(my_champion_icon, 80, 80)
        #background.paste(my_champion_icon, (layout['my_champion_start_x'], layout['my_champion_start_y']), my_champion_icon)
        #self.add_text_box(background, my_champion_kr, layout['my_champion_start_x'] + 120, layout['my_champion_start_y'] - 5, 30, colors['default'], self.noto_font_regular_path)
        #self.add_text_box(background, my_position_kr, layout['my_champion_start_x'] + 120, layout['my_champion_start_y'] + 40, 25, colors['default'], self.noto_font_regular_path)
        num_counters = min(len(counter_info), 3)
        for i in range(num_counters):
            counter = counter_info.iloc[i]
            current_y = layout['start_y'] + (i * layout['row_height'])
            champ_icon = Image.open(self.champion_icon_dir / f"{counter['opponent_champ']}.png")
            champ_icon = self.resize_circle(champ_icon, 68, 68)
            background.paste(champ_icon, (layout['start_x'], current_y), champ_icon)
            kda_diff = counter['kda_diff']
            if kda_diff > 0:
                kda_text = f"+ {abs(kda_diff):.1f}"
                kda_color = colors['positive']
            else:
                kda_text = f"- {abs(kda_diff):.1f}"
                kda_color = colors['negative']
            text_data = {
                'name_kr': {'text': f"{counter['name_kr']}", 'color': colors['default']},
                'winrate': {'text': f"{counter['win_rate']:.1f}%", 'color': colors['default']},
                'kda_diff': {'text': kda_text, 'color': kda_color},
                'counter_score': {'text': f"{counter['counter_score']:.1f}", 'color': colors['default']},
                'games': {'text': f"{int(counter['games_played'])}", 'color': colors['default']}
            }
            for key, data in text_data.items():
                x = layout['start_x'] + layout['text_offsets'][key]
                y = current_y + layout['text_y_offset']
                self.add_text_box(background, data['text'], x, y, 30, data['color'], self.noto_font_light_path)
        return background

    def draw_pickrate_stat_table(self, image, stats):
        draw = ImageDraw.Draw(image)
        table = Image.open(self.pick_rate_assets_dir / "4" / "table.png")
        image.paste(table, (91, 545), table)
        value_font = ImageFont.truetype(self.noto_font_regular_path, 30)
        value_color = (255,255,255)
        stats_x = 150
        stats_y = 570
        for i, (label, value) in enumerate(stats.items()):
            value_text = str(value)
            if label == "티어":
                value_color = self.tier_color[value_text]
                value_text = "   "+value_text
            if i >= 2:
                value_color = (255,255,255)
                value_text = f"{value:.2f}%"
            draw.text((stats_x + (i * 175), stats_y + 77), value_text, font=value_font, fill=value_color)
        return image

    def draw_ban_info(self, background, win_team, lose_team):
        # Ban 챔피언 이미지 위치
        ban_y = 263
        ban_spacing = 100
        blue_bans = [win_team.iloc[0][f'ban{i}'] for i in range(1, 6)]
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
        red_bans = [lose_team.iloc[0][f'ban{i}'] for i in range(1, 6)]
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

    def draw_match_result_table(self, background, win_team, lose_team, draw, mvp_score):
        font = ImageFont.truetype(self.noto_font_bold_kr_path, 20)
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        row_start_y = 390
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
            blue_pos_data = win_team[win_team['position'] == position].iloc[0]
            blue_champion_icon = Image.open(self.champion_icon_dir / f"{blue_pos_data['name_us']}.png")
            blue_champion_icon = self.resize_image(blue_champion_icon, 100, 60)
            blue_champion_icon = self.add_gradient_border(blue_champion_icon, 10)
            background.paste(blue_champion_icon, (left_side['champion'], current_y))

            blue_kda = f"{blue_pos_data['kills']} / {blue_pos_data['deaths']} / {blue_pos_data['assists']}"
            blue_score = mvp_score[mvp_score['playername'] == blue_pos_data['playername']]['mvp_score'].iloc[0]
            draw.text((left_side['kda'], current_y + 20), blue_kda, font=font, fill='white')
            draw.text((left_side['player'], current_y + 5), str(blue_pos_data['playername']), font=font, fill='white')
            draw.text((left_side['player']+10, current_y + 40), f"{blue_score:.1f}", font=font, fill='#FFD700')

            blue_damage = "{:,}".format(blue_pos_data['damagetochampions'])
            draw.text((left_side['damage'], current_y + 20), blue_damage, font=font, fill='white')

            red_pos_data = lose_team[lose_team['position'] == position].iloc[0]
            red_champion_icon = Image.open(self.champion_icon_dir / f"{red_pos_data['name_us']}.png")
            red_champion_icon = self.resize_image(red_champion_icon, 100, 60)
            red_champion_icon = self.add_gradient_border(red_champion_icon, 10)
            background.paste(red_champion_icon, (right_side['champion'], current_y))

            draw.text((right_side['damage'], current_y + 20),
                      "{:,}".format(red_pos_data['damagetochampions']),
                      font=font, fill='white')

            red_kda = f"{red_pos_data['kills']} / {red_pos_data['deaths']} / {red_pos_data['assists']}"
            draw.text((right_side['kda'], current_y + 20),
                      red_kda,
                      font=font, fill='white')

            red_score = mvp_score[mvp_score['playername'] == red_pos_data['playername']]['mvp_score'].iloc[0]
            draw.text((right_side['player'], current_y + 5), str(red_pos_data['playername']), font=font, fill='white')
            draw.text((right_side['player']+10, current_y + 40), f"{red_score:.1f}", font=font, fill='#FFD700')

    def run(self, match_id, player_name):
        try:
            self.first_page(match_id, player_name)
            self.second_page(match_id, player_name)
            self.third_page(match_id, player_name)
            self.fourth_page(match_id, player_name)
            self.fifth_page(match_id, player_name)
        except Exception as e:
            print(f"픽률 탐지 기사 생성 오류 {match_id}, {player_name}" , e)
            today_date = datetime.today().date().strftime("%y_%m_%d")
            output_path = self.output_dir / today_date / match_id
            if os.path.exists(output_path):
                shutil.rmtree(output_path)
