import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np
from pathlib import Path
import re as regex
from datetime import datetime
from Ai.article_generator import ArticleGenerator
from AnomalyDetection.champion_detection import ChampionDetection
from util.commonException import CommonError, ErrorCode
from AnomalyDetection.plt_draw import PltDraw
import pandas as pd

class PickRate:

    def __init__(self, database, meta_data, article_generator):
        self.database = database
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info
        self.champion_background_dir = Path(__file__).parent.parent / "Assets" / "Image" / "champion"
        self.champion_icon_dir = Path(__file__).parent.parent / "Assets" / "Image" / "champion_icon"
        self.player_dir = Path(__file__).parent.parent / "Assets" / "Image" / "player"
        self.team_icon_dir = Path(__file__).parent.parent / "Assets" / "Image" / "team_icon"
        self.background_dir = Path(__file__).parent.parent / "Assets" / "Image" / "background"
        self.pick_rate_assets_dir = Path(__file__).parent.parent / "Assets" / "PickRate"
        self.plt_dir = Path(__file__).parent.parent / "PltOutput"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "PickRate"
        self.title_font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"
        self.main_font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Noto_Sans_KR" / "static" / "NotoSansKR-Bold.ttf"
        self.anton_font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Anton,Noto_Sans_KR" / "Anton" / "Anton-Regular.ttf"
        self.noto_font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Noto_Sans_KR" / "NotoSansKR-VariableFont_wght.ttf"
        self.main_font_size = self.properties.get("main_font_size")
        self.main_line_spacing = self.properties.get("main_line_spacing")
        self.title_font_size = self.properties.get("title_font_size")
        self.black = self.properties.get("black")
        self.tier_color = self.properties.get("tier_color")
        self.plt_draw = PltDraw(database, meta_data)
        self.article_generator = ArticleGenerator(database, meta_data)

    def first_page(self, match_id, player_name):
        background_path = self.pick_rate_assets_dir / "1" / "background.png"
        game_df = self.database.get_game_data(match_id)
        name_us = game_df[game_df['playername'] == player_name]['name_us'].iloc[0]
        background = Image.open(background_path)

        champion_icon = Image.open(self.champion_icon_dir / f"{name_us}.png")
        champion_icon = self.resize_image(champion_icon, 450,450)
        champion_icon = self.add_gradient_border(champion_icon)

        player_path = self.get_player_image_path(player_name.lower())
        player_image = Image.open(player_path)
        player_image = self.resize_with_crop_image(player_image, 450, 450)
        player_image = self.add_bottom_gradient(player_image)

        background.paste(player_image, (64, 295), player_image)
        background.paste(champion_icon, (555, 294), champion_icon)
        background = self.add_top_gradient(background, 745)
        box_size = (948, 220)
        text = self.article_generator.generate_first_page_article(game_df, player_name, 15)
        self.add_first_page_title(background, text, 65, 790)
        self.save_image(background, match_id, "1")

    def second_page(self, match_id, player_name):
        background_path = self.pick_rate_assets_dir / "2" / "background.png"
        table_path = self.pick_rate_assets_dir / "2" / "Table.png"
        game_df = self.database.get_game_data(match_id)
        blue_team = game_df[game_df['side'] == 'Blue']
        red_team = game_df[game_df['side'] == 'Red']

        background = Image.open(background_path)
        background = self.resize_image_type1(background)
        self.add_title_text(background, "경기정보")

        self.draw_result_table(background, blue_team, red_team, (40, 200))

        mvp_score = self.database.calculate_mvp_score(game_df)
        table = Image.open(table_path)
        table = self.add_gradient_border(table,9)
        background.paste(table, (40, 360), table)
        draw = ImageDraw.Draw(background)
        self.draw_ban_info(background, blue_team, red_team)
        self.draw_table_info(background, blue_team, red_team, draw, mvp_score)

        box_size = (980,400)
        max_chars = self.calculate_text_max_chars(self.main_font_path, self.main_font_size, box_size)
        main_text = self.article_generator.generate_second_page_article(game_df, player_name, max_chars)
        self.add_main_text(background, main_text, (50, 890), box_size)
        self.save_image(background, match_id, "2")


    def third_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        background = Image.open(self.champion_background_dir / f"{name_us}.png")
        background = self.resize_image_type2(background)
        background = self.add_bottom_gradient(background, 2700)
        self.add_title_text(background, "성과지표 비교")
        self.draw_line(background, (50, 170))

        max_chars = self.calculate_text_max_chars(self.main_font_path, self.main_font_size, (1000, 500))
        main_text = self.article_generator.generate_third_page_article(game_df, player_name, max_chars)
        self.add_main_text(background, main_text, (50, 190), (1000,500))

        radar_chart_path = self.plt_draw.draw_radar_chart(match_id, player_name)
        radar_chart = Image.open(radar_chart_path)
        radar_chart = self.resize_image(radar_chart, 800, 630)

        background.paste(radar_chart, (50,700), radar_chart)
        self.plt_draw.draw_all_series(match_id, player_name)
        today_date = datetime.today().date().strftime("%y_%m_%d")
        series_dir = self.plt_dir / "PickRate" / "Series" / today_date
        gold = Image.open(series_dir / f"{match_id}_{player_name}_goldat.png")
        exp = Image.open(series_dir / f"{match_id}_{player_name}_xpat.png")
        gold = self.resize_image(gold, 1000, 580)
        exp = self.resize_image(exp, 1000, 580)
        background.paste(gold, (1124, 50), gold)
        background.paste(exp, (1124, 675), exp)

        self.split_and_save(background,  match_id, "3", "4")


    def fourth_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        champion_background = Image.open(self.champion_background_dir / f"{name_us}.png")
        champion_background = self.resize_image_type2(champion_background)
        champion_background = self.add_bottom_gradient(champion_background,2500)

        self.add_title_text(champion_background, "챔피언 픽률")

        champion_icon = Image.open(self.champion_icon_dir / f"{name_us}.png")
        champion_icon = self.resize_image(champion_icon, 175, 175)
        champion_icon = self.add_gradient_border(champion_icon, 20)
        champion_background.paste(champion_icon, (50, 200), champion_icon)

        self.draw_line(champion_background, (50,385))

        max_chars = self.calculate_text_max_chars(self.main_font_path, self.main_font_size, (1000, 700))
        main_text = self.article_generator.generate_fourth_page_article(game_df, player_name, max_chars)
        champion_background = self.add_main_text(champion_background, main_text, (50,410))
        champion_stats = self.database.get_champion_rate_table(name_us, self.meta_data.basic_info.get("patch"), player_df['position'])
        champion_background = self.add_pickrate_info_table(champion_background, champion_stats)
        save_path = self.plt_draw.draw_pick_rates_transparent(name_us, player_df['position'])

        pick_rate_graph = Image.open(save_path)
        pick_rate_graph = self.resize_image(pick_rate_graph, 1050, 1050)
        champion_background.paste(pick_rate_graph, (1130, 150), pick_rate_graph)

        self.split_and_save(champion_background,  match_id, "5", "6")

    def fifth_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        position = player_df['position']

        background = Image.open(self.background_dir / "background1.png")
        background = self.resize_image_type1(background)
        background = self.add_bottom_gradient(background, 1350)
        self.add_title_text(background, "카운터 픽")

        counter_info = self.database.get_counter_champion(name_us, position, self.meta_data.basic_info.get("patch"))

        table = Image.open(self.pick_rate_assets_dir / "5" / f"table3.png")
        background.paste(table, (11, 180), table)
        background = self.draw_table_5(background, player_df, counter_info)

        textbox_image = Image.open(self.background_dir / "textbox.png")
        background.paste(textbox_image, (29, 770), textbox_image)

        max_chars = self.calculate_text_max_chars(self.main_font_path, self.main_font_size, (1000, 500))
        main_text = self.article_generator.generate_fifth_page_article(match_id, player_name, max_chars)
        self.add_main_text(background, main_text, (50, 790), (1000, 500))
        self.save_image(background, match_id, 7)

    def sixth_pag_2(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        blue_team = game_df[(game_df['side'] == 'Blue') & (game_df['position'] == 'team')].iloc[0]
        red_team = game_df[(game_df['side'] == 'Red') & (game_df['position'] == 'team')].iloc[0]
        position = game_df[game_df['player_name'] == player_name]
        background = Image.open(self.background_dir / "background1.png")
        background = self.resize_image_type1(background)
        background = self.add_bottom_gradient(background, 2000)
        self.add_title_text(background, "경기 결과")

        blue_team_icon = Image.open(self.team_icon_dir / f"{blue_team['teamname']}.png")
        red_team_icon = Image.open(self.team_icon_dir / f"{red_team['teamname']}.png")
        blue_team_icon = self.resize_image(blue_team_icon, 175, 175)
        red_team_icon = self.resize_image(red_team_icon, 175, 175)

        background.paste(blue_team_icon, (95,235), blue_team_icon)
        background.paste(red_team_icon, (95,510), red_team_icon)
        self.draw_line(background, (80, 460), (890, 5), (255,255,255))

        blue_kda = f"{blue_team['kills']} / {blue_team['deaths']} / {blue_team['assists']}"
        red_kda = f"{red_team['kills']} / {red_team['deaths']} / {red_team['assists']}"
        result = blue_team['result']
        if result == 1:
            self.add_text_box(background, "승리", 550, 230, 64, "#0989ce")
            self.add_text_box(background, "패배", 550, 475, 64, "#e24647")
        else:
            self.add_text_box(background, "패배", 550, 230, 64, "#e24647")
            self.add_text_box(background, "승리", 550, 475, 64, "#0989ce")
        self.add_text_box(background, blue_kda, 430, 310, 64, (255,255,255))
        self.add_text_box(background, red_kda, 430, 555, 64, (255,255,255))

        main_text = "프로필에서 보이는 0.70%라는 픽률 낮은 픽률을 보여주고 있지만, 24.04%라는 높은 밴률을 가르고 있습니다. 미드 포지션에서 밴률이 매우 끼치면은 메타픽으로 판단하고 있다는 것을 보여줍니다. 47.40% 의 승률을 평균적인 스코어지만, 미드의 특성상 개인의 철저한 가르티리온로 플레이 수 있다는 것을 시사합니다."
        self.add_main_text(background, main_text, (80, 730), (980, 550))

        self.save_image(background, match_id, 8)

    def sixth_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        blue_team = game_df[(game_df['side'] == 'Blue') & (game_df['position'] == 'team')].iloc[0]
        red_team = game_df[(game_df['side'] == 'Red') & (game_df['position'] == 'team')].iloc[0]
        position = game_df[game_df['player_name'] == player_name]
        background = Image.open(self.background_dir / "background1.png")
        background = self.resize_image_type1(background)
        background = self.add_bottom_gradient(background, 2000)
        self.add_title_text(background, "경기 결과")

        blue_team_icon = Image.open(self.team_icon_dir / f"{blue_team['teamname']}.png")
        red_team_icon = Image.open(self.team_icon_dir / f"{red_team['teamname']}.png")
        blue_team_icon = self.resize_image(blue_team_icon, 175, 175)
        red_team_icon = self.resize_image(red_team_icon, 175, 175)

        background.paste(blue_team_icon, (95,235), blue_team_icon)
        background.paste(red_team_icon, (95,510), red_team_icon)
        self.draw_line(background, (80, 460), (890, 5), (255,255,255))

        blue_kda = f"{blue_team['kills']} / {blue_team['deaths']} / {blue_team['assists']}"
        red_kda = f"{red_team['kills']} / {red_team['deaths']} / {red_team['assists']}"
        result = blue_team['result']
        if result == 1:
            self.add_text_box(background, "승리", 550, 230, 64, "#0989ce")
            self.add_text_box(background, "패배", 550, 475, 64, "#e24647")
        else:
            self.add_text_box(background, "패배", 550, 230, 64, "#e24647")
            self.add_text_box(background, "승리", 550, 475, 64, "#0989ce")
        self.add_text_box(background, blue_kda, 430, 310, 64, (255,255,255))
        self.add_text_box(background, red_kda, 430, 555, 64, (255,255,255))

        main_text = "프로필에서 보이는 0.70%라는 픽률 낮은 픽률을 보여주고 있지만, 24.04%라는 높은 밴률을 가르고 있습니다. 미드 포지션에서 밴률이 매우 끼치면은 메타픽으로 판단하고 있다는 것을 보여줍니다. 47.40% 의 승률을 평균적인 스코어지만, 미드의 특성상 개인의 철저한 가르티리온로 플레이 수 있다는 것을 시사합니다."
        self.add_main_text(background, main_text, (80, 730), (980, 550))

        self.save_image(background, match_id, 8)

    def draw_result_table(self, background, blue_team, red_team, position):
        result_table = Image.open(self.pick_rate_assets_dir / "2" / "result.png")
        result_draw = ImageDraw.Draw(result_table)
        font = ImageFont.truetype(self.main_font_path, 18)
        blue_team_name = blue_team['teamname'].iloc[0]
        blue_bbox = font.getbbox(blue_team_name)
        blue_text_width = blue_bbox[2] - blue_bbox[0]
        blue_x = 300 - (blue_text_width / 2)
        result_draw.text((blue_x, 20), blue_team_name, font=font, fill='#AAA9B7')
        red_team_name = red_team['teamname'].iloc[0]
        red_bbox = font.getbbox(red_team_name)
        red_text_width = red_bbox[2] - red_bbox[0]
        red_x = 700 - (red_text_width / 2)
        result_draw.text((red_x, 20), red_team_name, font=font, fill='#AAA9B7')
        background.paste(result_table, position, result_table)

    def calculate_text_max_chars(self, font_path, font_size, box_size):
        font = ImageFont.truetype(font_path, font_size)
        box_width, box_height = box_size
        test_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(test_img)
        test_chars = "가나다라마바사아자차카타파하"
        avg_char_width = sum(draw.textlength(char, font=font) for char in test_chars) / len(test_chars)
        line_height = font_size * 1.1
        chars_per_line = int(box_width / avg_char_width)
        available_lines = int(box_height / line_height)
        max_chars = int(chars_per_line * available_lines)
        return max(1, max_chars)

    def draw_table_5(self, background, player_df, counter_info):
        layout = {
            'my_champion_start_x': 103,
            'my_champion_start_y': 226,
            'start_x': 96,
            'start_y': 416,
            'row_height': 107,
            'text_offsets': {
                'name_kr': 110,
                'winrate': 300,
                'kda_diff': 500,
                'counter_score': 680,
                'games': 860
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
        background.paste(my_champion_icon, (layout['my_champion_start_x'], layout['my_champion_start_y']), my_champion_icon)
        self.add_text_box(background, my_champion_kr, layout['my_champion_start_x'] + 120, layout['my_champion_start_y'] - 5, 30, colors['default'], self.noto_font_path)
        self.add_text_box(background, my_position_kr, layout['my_champion_start_x'] + 120, layout['my_champion_start_y'] + 40, 25, colors['default'], self.noto_font_path)
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
                self.add_text_box(background, data['text'], x, y, 30, data['color'], self.noto_font_path)
        return background

    def add_text_box(self, image, text, x, y, font_size=20, color=(0, 0, 0), font_path=None):
        draw = ImageDraw.Draw(image)
        if font_path is None: font_path = self.main_font_path
        font = ImageFont.truetype(font_path, font_size)
        draw.text((x, y), str(text), font=font, fill=color)

    def resize_circle(self, image, width, height, stroke_width=2):
        # 이미지 크기를 좀 더 크게 조정하여 안티앨리어싱을 위한 여유 공간 확보
        resize_ratio = 2
        temp_width = width * resize_ratio
        temp_height = height * resize_ratio

        image = image.resize((temp_width, temp_height), Image.Resampling.LANCZOS)
        image = image.convert('RGBA')
        mask = Image.new('L', (temp_width, temp_height), 0)
        draw = ImageDraw.Draw(mask)
        padding = stroke_width * resize_ratio
        draw.ellipse((padding, padding, temp_width - padding - 1, temp_height - padding - 1),
                     fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=resize_ratio))
        output = Image.new('RGBA', (temp_width, temp_height), (0, 0, 0, 0))
        output.paste(image, (0, 0), mask)
        output = output.resize((width, height), Image.Resampling.LANCZOS)
        return output

    def split_and_save(self, image, match_id, file_name1, file_name2):
        today_date = datetime.today().date().strftime("%y_%m_%d")
        output_path1 = self.output_dir / today_date / match_id / f"{file_name1}.png"
        output_path2 = self.output_dir / today_date / match_id / f"{file_name2}.png"
        os.makedirs(output_path1.parent, exist_ok=True)
        top_image = image.crop((0, 0, 1080, 1350))
        bottom_image = image.crop((1080, 0, 2160, 1350))
        top_image.save(output_path1)
        bottom_image.save(output_path2)

    def save_image(self, image, match_id, file_name):
        today_date = datetime.today().date().strftime("%y_%m_%d")
        output_path = self.output_dir / today_date / match_id / f"{file_name}.png"
        os.makedirs(output_path.parent, exist_ok=True)
        image.save(output_path)

    def draw_line(self, image, position, box_size=(440,15), color=("#bedcff")):
        x, y = position
        w, h = box_size
        draw = ImageDraw.Draw(image)
        draw.rectangle([x, y, x + w, y + h], fill=color)

    def add_main_text_line_split_by_dot(self, image, text, position, box_size=(900,700)):
        draw = ImageDraw.Draw(image)
        main_font = ImageFont.truetype(self.main_font_path, self.main_font_size)
        x,y = position
        max_width, max_height = box_size
        #draw.rectangle([x, y, x + max_width, y + max_height], fill=(1,1,1))
        words = text.split(' ')
        lines = []
        while words:
            line = ''
            while words and int(main_font.getlength(line + words[0])) <= max_width and (main_font.size + self.main_line_spacing) * (len(lines) + 1) <= max_height or line == '':
                if words[0].endswith("."):
                    line = line + (words.pop(0) + ' ')
                    break
                line = line + (words.pop(0) + ' ')
            lines.append(line.strip())
        for line in lines:
            draw.text((x, y), line, font=main_font, fill=(255,255,255))
            y += draw.textbbox((0, 0), line, font=main_font)[3] + self.main_line_spacing
        return image

    def add_main_text1(self, image, text, position, box_size=(1000, 700)):
        draw = ImageDraw.Draw(image)
        x, y = position
        box_width, box_height = box_size
        draw.rectangle([x, y, x + box_width, y + box_height], fill=(255, 255, 255, 30))
        main_font = ImageFont.truetype(self.main_font_path, self.main_font_size)
        main_text_color = (255, 255, 255)

        # 텍스트를 더 작은 단위로 나누기
        segments = []
        current_segment = ""

        # 한글과 영문을 모두 고려한 텍스트 분할
        for char in text:
            if char.isspace():
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
                continue
            current_segment += char
            # 현재 세그먼트가 너무 길어지면 분할
            if draw.textlength(current_segment, font=main_font) > box_width * 0.3:
                segments.append(current_segment)
                current_segment = ""
        if current_segment:
            segments.append(current_segment)

        # 줄 구성
        lines = []
        current_line = []
        current_width = 0
        space_width = draw.textlength(" ", font=main_font)

        for segment in segments:
            segment_width = draw.textlength(segment, font=main_font)
            # 새 줄의 시작인 경우
            if not current_line:
                current_line.append(segment)
                current_width = segment_width
                continue

            # 현재 줄에 세그먼트를 추가할 수 있는 경우
            if current_width + space_width + segment_width <= box_width * 0.98:  # 98%까지 사용
                current_line.append(segment)
                current_width += space_width + segment_width
            else:
                # 줄이 충분히 차지 않았다면 더 좁은 간격으로 시도
                if current_width < box_width * 0.9:
                    compressed_space = (box_width - current_width) / (len(current_line) - 1)
                    lines.append((current_line, compressed_space))
                else:
                    lines.append((current_line, space_width))
                current_line = [segment]
                current_width = segment_width

        if current_line:
            lines.append((current_line, space_width))

        # 텍스트 그리기
        line_height = self.main_font_size + self.main_line_spacing
        current_y = y

        for line, space_width in lines:
            if current_y > position[1] + box_height:
                break

            # 현재 줄의 시작 위치 계산
            current_x = x
            for i, segment in enumerate(line):
                draw.text((current_x, current_y), segment, font=main_font, fill=main_text_color)
                current_x += draw.textlength(segment, font=main_font) + space_width

            current_y += line_height

        return image

    def add_main_text(self, image, text, position, box_size=(1000, 700)):
        draw = ImageDraw.Draw(image)
        x, y = position
        box_width, box_height = box_size
        #draw.rectangle([x, y, x + box_width, y + box_height], fill=(255, 255, 255, 30))
        main_font = ImageFont.truetype(self.main_font_path, self.main_font_size)
        main_text_color = (255, 255, 255)
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        for word in words:
            word_width = draw.textlength(word + " ", font=main_font)
            if current_width + word_width <= box_width:
                current_line.append(word)
                current_width += word_width
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width
        if current_line:
            lines.append(" ".join(current_line))
        line_height = self.main_font_size + self.main_line_spacing
        for line in lines:
            draw.text((x, y), line, font=main_font, fill=main_text_color)
            y += line_height
            if y > position[1] + box_height:
                break
        return image

    def add_pickrate_info_table(self, image, stats):
        draw = ImageDraw.Draw(image)
        table = Image.open(self.pick_rate_assets_dir / "3" / "table.png")
        image.paste(table, (50, 1100), table)
        value_font = ImageFont.truetype(self.noto_font_path, 30)
        value_color = (255,255,255)
        stats_x = 110
        stats_y = 1120
        for i, (label, value) in enumerate(stats.items()):
            value_text = str(value)
            if label == "티어":
                value_color = self.tier_color[value_text]
                value_text = "   "+value_text
            if i >= 2:
                value_color = (255,255,255)
                value_text = f"{value:.2f}%"
            draw.text((stats_x + (i * 177), stats_y + 77), value_text, font=value_font, fill=value_color)
        return image

    def draw_ban_info(self, background, blue_team, red_team):
        # Ban 챔피언 이미지 위치
        ban_y = 260
        ban_size = 100
        ban_spacing = 100
        blue_bans = [blue_team.iloc[0][f'ban{i}'] for i in range(1, 6)]
        for i, ban in enumerate(blue_bans):
            if ban:
                try:
                    ban_icon = Image.open(self.champion_icon_dir / f"{ban}.png")
                    ban_icon = self.resize_image(ban_icon, ban_size, ban_size)
                    ban_icon = self.add_gradient_border(ban_icon, 10)
                    ban_icon = self.convert_to_grayscale(ban_icon)
                    background.paste(ban_icon, (40 + i * ban_spacing, ban_y))
                except Exception as e:
                    print(f"블루팀 ban 이미지 처리 중 오류: {e}")
        red_bans = [red_team.iloc[0][f'ban{i}'] for i in range(1, 6)]
        for i, ban in enumerate(reversed(red_bans)):
            if ban:
                try:
                    ban_icon = Image.open(self.champion_icon_dir / f"{ban}.png")
                    ban_icon = self.resize_image(ban_icon, ban_size, ban_size)
                    ban_icon = self.add_gradient_border(ban_icon, 10)
                    ban_icon = self.convert_to_grayscale(ban_icon)
                    background.paste(ban_icon, (940 - i * ban_spacing, ban_y))
                except Exception as e:
                    print(f"레드팀 ban 이미지 처리 중 오류: {e}")

    def draw_table_info(self, background, blue_team, red_team, draw, mvp_score):
        font = ImageFont.truetype(self.main_font_path, 20)
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        row_start_y = 425
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
            blue_pos_data = blue_team[blue_team['position'] == position].iloc[0]
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

            red_pos_data = red_team[red_team['position'] == position].iloc[0]
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

    def convert_to_grayscale(self, image):
        return image.convert('L').convert('RGBA')

    def add_title_text(self, image, text, x=50, y=50):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.title_font_path, self.title_font_size)
        shadow_color = '#2B2B2B'
        shadow_offset = 8
        for i in range(2):
            offset = shadow_offset + i
            draw.text((x + offset, y + offset), text,
                      font=font, fill=shadow_color)
        outline_thickness = 5
        for offset_x in range(-outline_thickness, outline_thickness + 1):
            for offset_y in range(-outline_thickness, outline_thickness + 1):
                if offset_x * offset_x + offset_y * offset_y <= outline_thickness * outline_thickness:
                    draw.text((x + offset_x, y + offset_y),
                              text, font=font, fill='black')
        draw.text((x, y), text, font=font, fill='white')

    def add_first_page_title(self, image, text, x, y, box_width=948, box_height=220):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.title_font_path, self.title_font_size)
        pattern = r'\^(.*?)\^'
        parts = regex.split(pattern, text)
        words = []
        for i, part in enumerate(parts):
            if not part:
                continue
            part_words = part.split()
            for word in part_words:
                words.append((word, i % 2 == 1))

        def calculate_line_width(line):
            total_width = 0
            for word, _ in line:
                bbox = draw.textbbox((0, 0), word + " ", font=font)
                total_width += bbox[2] - bbox[0]
            return total_width

        def draw_text_with_effects(x, y, word, is_highlighted):
            shadow_color = '#2B2B2B'
            shadow_offset = 8
            for i in range(2):
                offset = shadow_offset + i
                draw.text((x + offset, y + offset), word + " ",
                          font=font, fill=shadow_color)
            outline_thickness = 5
            for offset_x in range(-outline_thickness, outline_thickness + 1):
                for offset_y in range(-outline_thickness, outline_thickness + 1):
                    if offset_x * offset_x + offset_y * offset_y <= outline_thickness * outline_thickness:
                        draw.text((x + offset_x, y + offset_y),
                                  word + " ", font=font, fill='black')

            text_color = '#ef2c28' if is_highlighted else 'white'
            draw.text((x, y), word + " ", font=font, fill=text_color)

        current_x = x
        current_y = y
        line_height = 50
        current_line = []
        lines = []

        for word, is_highlighted in words:
            bbox = draw.textbbox((0, 0), word + " ", font=font)
            word_width = bbox[2] - bbox[0]

            if current_x + word_width > x + box_width:
                lines.append(current_line)
                current_line = []
                current_x = x

            current_line.append((word, is_highlighted))
            current_x += word_width

        if current_line:
            lines.append(current_line)
        for line in lines:
            if current_y + line_height > y + box_height:
                break
            line_width = calculate_line_width(line)
            start_x = x + (box_width - line_width) // 2
            current_x = start_x
            for word, is_highlighted in line:
                bbox = draw.textbbox((0, 0), word + " ", font=font)
                word_width = bbox[2] - bbox[0]
                draw_text_with_effects(current_x, current_y, word, is_highlighted)
                current_x += word_width
            current_y += self.main_font_size + line_height

    def add_gradient_border(self, image, border_size=20):
        width, height = image.size
        gradient_mask = Image.new('L', (width, height), 255)
        draw = ImageDraw.Draw(gradient_mask)
        inner_rect = (border_size, border_size, width - border_size, height - border_size)
        for i in range(border_size):
            rect = (i, i, width - i, height - i)
            value = int(255 * ((i / border_size) ** 2))
            draw.rectangle(rect, outline=value)
        draw.rectangle(inner_rect, fill=255)
        black_layer = Image.new('RGBA', (width, height), (0, 0, 0, 255))

        gradient_layer = Image.composite(
            Image.new('RGBA', (width, height), (0, 0, 0, 0)),
            black_layer,
            gradient_mask
        )
        result = Image.alpha_composite(image.convert('RGBA'), gradient_layer)
        return result

    def add_bottom_gradient(self, image, border_size=20):
        width, height = image.size
        gradient_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient_layer)
        for i in range(border_size):
            alpha = int(255 * ((i / border_size) ** 2))
            y_position = height - border_size + i
            draw.line((0, y_position, width, y_position), fill=(0, 0, 0, alpha))
        result = Image.alpha_composite(image.convert('RGBA'), gradient_layer)
        return result

    def add_top_gradient(self, image, border_size=15, max_alpha=255):
        width, height = image.size
        gradient_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient_layer)

        for i in range(border_size):
            progress = i / border_size
            alpha = int(max_alpha * (1 - progress))
            y_position = i
            draw.line((0, y_position, width, y_position), fill=(0, 0, 0, alpha))
        result = Image.alpha_composite(image.convert('RGBA'), gradient_layer)
        return result

    def resize_with_crop_image(self, image, width, height=None):
        if height is None:
            height = width
        original_aspect = image.width / image.height
        target_aspect = width / height

        if original_aspect > target_aspect:
            new_width = int(image.height * target_aspect)
            left = (image.width - new_width) // 2
            top = 0
            right = left + new_width
            bottom = image.height
        else:  # 원본이 더 세로로 긴 경우
            new_height = int(image.width / target_aspect)
            left = 0
            top = (image.height - new_height) // 2
            right = image.width
            bottom = top + new_height
        image = image.crop((left, top, right, bottom))
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def get_player_image_path(self, player_name):
        player_files = list(self.player_dir.glob('*.png'))
        file_mapping = {
            path.stem.lower(): path
            for path in player_files
        }
        player_name_lower = player_name.lower()
        if player_name_lower in file_mapping:
            return file_mapping[player_name_lower]
        return self.player_dir / "default.png"

    def add_icon_to_image(self, image, icon_path, position):
        icon = Image.open(icon_path).convert("RGBA")
        if icon is None:
            raise FileNotFoundError(f"Icon at path '{icon_path}' not found.")
        icon_width, icon_height = icon.size
        image.paste(icon, position, icon)
        return image

    def resize_image_by_height(self, image, target_height):
        original_width, original_height = image.size
        ratio = target_height / original_height
        target_width = int(original_width * ratio)
        return image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    def resize_image_by_width(self, image, target_width):
        original_width, original_height = image.size
        ratio = target_width / original_width
        target_height = int(original_height * ratio)
        return image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    def resize_image(self, image, width=None, height=None):
        if width and height:
            return self.resize_with_crop_image(image, width, height)
        if width:
            resized_image = self.resize_image_by_width(image, width)
        elif height:
            resized_image = self.resize_image_by_height(image, height)
        else:
            raise ValueError("가로 또는 세로 길이를 지정해야 합니다.")
        return resized_image

    def resize_image_type1(self, image):
        w, h = image.size
        target_size = (1080, 1350)
        target_height = target_size[1]
        target_width = target_size[0]
        proportion_h = target_size[1] / h
        proportion_w = target_size[0] / w

        # 가로가 긴 사진인 경우
        if w > h:
            new_height = target_height + 100
            new_width = int(proportion_h * w)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            start_x = (new_width - target_width) // 2
            resized_cropped_image = resized_image.crop((start_x, 100, start_x + target_width, new_height))
        # 세로가 긴 사진인 경우
        else:
            new_height = int(proportion_w * h)
            new_width = target_width
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            start_y = (new_height - target_height) // 2
            resized_cropped_image = resized_image.crop((0, start_y + 100, new_width, start_y + target_height + 100))
        return resized_cropped_image

    def resize_image_type2(self, image):
        """
            가로로 긴 사진 생성 사진이 새로 형식 사진이라면 이미지 비율이 너무 안맞아서 불가능 그냥 return 하기
            2160, 1350 resize
        """
        w, h = image.size
        target_size = (2160, 1350)
        target_height = target_size[1]
        target_width = target_size[0]
        proportion_h = target_size[1] / h
        proportion_w = target_size[0] / w

        if w > h:
            new_height = target_height
            new_width = int(proportion_h * w)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            start_x = (new_width - target_width) // 2
            resized_cropped_image = resized_image.crop((start_x, 0, start_x + target_width, new_height))
        else:
            raise CommonError(ErrorCode.size, "세로가 긴사진은 type2 불가", image.size)
        return resized_cropped_image



    def convert_png(self):
        image_extensions = ['.jpg', '.jpeg', '.JPG', '.JPEG']
        for file_path in (self.background_dir).iterdir():
            if file_path.suffix in image_extensions:
                try:
                    with Image.open(file_path) as img:
                        img = img.convert('RGBA')
                        new_path = file_path.with_suffix('.png')
                        img.save(new_path, 'PNG', optimize=True, quality=95)
                        os.remove(file_path)
                except Exception as e:
                    print(f"오류 발생 ({file_path.name}): {str(e)}")

    def create_champion_comparison(self, size=(800, 400)):
        # 기본 이미지 생성
        image = Image.new('RGB', size, color='#0f1525')
        draw = ImageDraw.Draw(image)

        # 폰트 설정 (시스템에 맞는 폰트 경로 사용 필요)
        try:
            title_font = ImageFont.truetype('malgun.ttf', 24)  # 한글 지원 폰트
            header_font = ImageFont.truetype('malgun.ttf', 18)
            normal_font = ImageFont.truetype('malgun.ttf', 16)
        except OSError:
            # 폰트를 찾을 수 없는 경우 기본 폰트 사용
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()

        # 헤더 영역 그리기
        header_color = '#1a1a2e'
        draw.rectangle([40, 20, 760, 110], fill=header_color, outline='#2d3748', width=1)

        # 챔피언 아이콘 자리 (원)
        draw.ellipse([70, 35, 130, 95], fill='#4a5568', outline='#c9d4e0', width=2)

        # 헤더 텍스트
        draw.text((150, 45), "대상 챔피언", fill='#e2e8f0', font=title_font)
        draw.text((150, 80), "탑 라인", fill='#94a3b8', font=header_font)

        # 컬럼 헤더
        column_headers = [
            (130, "상대 챔피언"),
            (300, "승률"),
            (450, "교전력"),
            (600, "매칭수")
        ]

        for x, text in column_headers:
            draw.text((x, 140), text, fill='#94a3b8', font=normal_font)

        # 구분선
        draw.line([40, 130, 760, 130], fill='#2d3748', width=1)

        # 데이터 행 그리기
        champion_data = [
            ("다리우스", "65.2%", "+2.3", "30"),
            ("오른", "45.8%", "-1.5", "25"),
            ("요릭", "55.3%", "+0.8", "40")
        ]

        for i, (champ, winrate, combat, matches) in enumerate(champion_data):
            y = 170 + (i * 80)
            # 행 배경
            draw.rectangle([40, y, 760, y + 70], fill='#242442', outline='#2d3748', width=1)

            # 챔피언 아이콘 원
            draw.ellipse([65, y + 10, 115, y + 60], fill='#4a5568', outline='#60a5fa', width=2)

            # 데이터 텍스트
            draw.text((130, y + 25), champ, fill='#e2e8f0', font=normal_font)


            # 승률 색상 조정 (높으면 초록, 낮으면 빨강)
            winrate_color = '#22c55e' if float(winrate[:-1]) > 50 else '#ef4444'
            draw.text((300, y + 25), winrate, fill=winrate_color, font=normal_font)

            # 교전력 색상 조정
            combat_color = '#22c55e' if combat.startswith('+') else '#ef4444'
            draw.text((450, y + 25), combat, fill=combat_color, font=normal_font)

            draw.text((600, y + 25), matches, fill='#94a3b8', font=normal_font)
        image.save(self.output_dir / "9.png")
        return image

    def run_all_page(self, match_id, player_name):
        self.first_page(match_id, player_name)
        self.second_page(match_id, player_name)
        self.third_page(match_id, player_name)
        self.fourth_page(match_id, player_name)
        self.fifth_page(match_id, player_name)
