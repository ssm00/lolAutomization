import os
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np
from pathlib import Path
import re as regex
from datetime import datetime
from Ai.api_call import GenAiAPI
from AnomalyDetection.champion_detection import ChampionDetection
from util.commonException import CommonError, ErrorCode
from AnomalyDetection.plt_draw import PltDraw


class PickRate:

    def __init__(self, database, meta_data, gen_api):
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
        self.font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"
        self.anton_font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Anton,Noto_Sans_KR" / "Anton" / "Anton-Regular.ttf"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "PickRate"
        self.main_font_size = self.properties.get("main_font_size")
        self.main_line_spacing = self.properties.get("main_line_spacing")
        self.title_font_size = self.properties.get("title_font_size")
        self.black = self.properties.get("black")
        self.tier_color = self.properties.get("tier_color")
        self.plt_draw = PltDraw(database, meta_data)
        self.gen_api = gen_api

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

        self.add_first_page_title(background, "픽률 ^0.1프로^의 뽀삐?", 65, 790)

        background.save(self.output_dir / "1.png")

    def second_page(self, match_id, player_name):
        background_path = self.pick_rate_assets_dir / "2" / "background.png"
        table_path = self.pick_rate_assets_dir / "2" / "Table.png"
        game_df = self.database.get_game_data(match_id)
        blue_team = game_df[game_df['side'] == 'Blue']
        red_team = game_df[game_df['side'] == 'Red']

        background = Image.open(background_path)
        background = self.resize_image_type1(background)
        self.add_title_text(background, "경기정보")

        table = Image.open(table_path)
        table = self.add_gradient_border(table,9)
        background.paste(table, (40, 300), table)
        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype(self.font_path, 20)

        self.draw_ban_info(background, blue_team, red_team)
        self.draw_table_info(background, blue_team, red_team, draw, font)

        main_text = "프로필에서 보이는 0.70%라는 픽률 낮은 픽률을 보여주고 있지만, 24.04%라는 높은 밴률을 가르고 있습니다. 미드 포지션에서 밴률이 매우 끼치면은 메타픽으로 판단하고 있다는 것을 보여줍니다. 47.40% 의 승률을 평균적인 스코어지만, 미드의 특성상 개인의 철저한 가르티리온로 플레이 수 있다는 것을 시사합니다."
        self.add_main_text(background, main_text, (50, 830), (980, 400))

        background.save(self.output_dir / "2.png")

    def third_page(self, match_id, player_name):
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

        main_text = "프로필에서 보이는 0.70%라는 픽률 낮은 픽률을 보여주고 있지만, 24.04%라는 높은 밴률을 가르고 있습니다. 미드 포지션에서 밴률이 매우 끼치면은 메타픽으로 판단하고 있다는 것을 보여줍니다. 47.40% 의 승률을 평균적인 스코어지만, 미드의 특성상 개인의 철저한 가르티리온로 플레이 수 있다는 것을 시사합니다."
        self.draw_line(champion_background, (50,385))

        champion_background = self.add_main_text(champion_background, main_text, (50,410))
        champion_stats = self.database.get_champion_stats(name_us, self.meta_data.anomaly_info.get("patch"), player_df['position'])
        champion_background = self.add_page3_table(champion_background, champion_stats)
        save_path = self.plt_draw.draw_pick_rates_transparent(name_us, player_df['position'])

        pick_rate_graph = Image.open(save_path)
        pick_rate_graph = self.resize_image(pick_rate_graph, 1050, 1050)
        champion_background.paste(pick_rate_graph, (1130, 150), pick_rate_graph)

        self.split_and_save(champion_background, self.output_dir / "3.png", self.output_dir / "4.png")

    def fourth_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        background = Image.open(self.champion_background_dir / f"{name_us}.png")
        background = self.resize_image_type2(background)
        background = self.add_bottom_gradient(background, 2700)
        self.add_title_text(background, "성과지표 비교")
        self.draw_line(background, (50, 170))

        main_text = "프로필에서 보이는 0.70%라는 픽률 낮은 픽률을 보여주고 있지만, 24.04%라는 높은 밴률을 가르고 있습니다. 미드 포지션에서 밴률이 매우 끼치면은 메타픽으로 판단하고 있다는 것을 보여줍니다. 47.40% 의 승률을 평균적인 스코어지만, 미드의 특성상 개인의 철저한 가르티리온로 플레이 수 있다는 것을 시사합니다."
        self.add_main_text(background, main_text, (50, 190), (1000,500))

        radar_chart_path = self.plt_draw.draw_radar_chart(game_df, player_name)
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

        self.split_and_save(background, self.output_dir / "5.png", self.output_dir / "6.png")

    def fifth_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        player_df = game_df[game_df['playername'] == player_name].iloc[0]
        name_us = player_df['name_us']
        position = player_df['position']

        background = Image.open(self.background_dir / "background1.png")
        background = self.resize_image_type1(background)
        background = self.add_bottom_gradient(background, 1350)
        self.add_title_text(background, "추천 경기")

        counter_info = self.database.get_counter_champion(name_us, position, self.meta_data.anomaly_info.get("patch"))
        counter_info = counter_info.dropna()
        num_counters = min(len(counter_info), 3)

        table = Image.open(self.pick_rate_assets_dir / "5" / f"table{num_counters}.png")
        background.paste(table, (50, 180), table)
        background = self.draw_table_5(background, counter_info, num_counters)

        main_text = "프로필에서 보이는 0.70%라는 픽률 낮은 픽률을 보여주고 있지만, 24.04%라는 높은 밴률을 가르고 있습니다. 미드 포지션에서 밴률이 매우 끼치면은 메타픽으로 판단하고 있다는 것을 보여줍니다. 47.40% 의 승률을 평균적인 스코어지만, 미드의 특성상 개인의 철저한 가르티리온로 플레이 수 있다는 것을 시사합니다."
        self.draw_line(background,(50,650))
        self.add_main_text(background, main_text, (50, 680), (980, 600))

        background.save(self.output_dir / "7.png")

    def sixth_page(self, match_id, player_name):
        game_df = self.database.get_game_data(match_id)
        blue_team = game_df[(game_df['side'] == 'Blue') & (game_df['position'] == 'team')].iloc[0]
        red_team = game_df[(game_df['side'] == 'Red') & (game_df['position'] == 'team')].iloc[0]

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

        background.save(self.output_dir / "8.png")


    def draw_table_5(self, background, counter_info, num_counters):
        layout = {
            'start_x': 90,
            'start_y': 260,
            'row_height': 127,
            'text_offsets': {
                'winrate': 160,
                'kda_diff': 400,
                'counter_score': 600,
                'games': 800
            },
            'text_y_offset': 5
        }
        colors = {
            'default': (255, 255, 255),
            'positive': '#0aaf9d',
            'negative': '#ed1b58'
        }
        for i in range(num_counters):
            counter = counter_info.iloc[i]
            current_y = layout['start_y'] + (i * layout['row_height'])
            champ_icon = Image.open(self.champion_icon_dir / f"{counter['opponent_champ']}.png")
            champ_icon = self.resize_circle(champ_icon, 100, 100)
            background.paste(champ_icon,
                             (layout['start_x'], current_y),
                             champ_icon)
            kda_diff = counter['kda_diff']
            if kda_diff > 0:
                kda_text = f"{abs(kda_diff):.1f}"
                kda_color = colors['positive']
            else:
                kda_text = f"{abs(kda_diff):.1f}"
                kda_color = colors['negative']
            text_data = {
                'winrate': {'text': f"{counter['win_rate']:.1f}%", 'color': colors['default']},
                'kda_diff': {'text': kda_text, 'color': kda_color},
                'counter_score': {'text': f"{counter['counter_score']:.1f}", 'color': colors['default']},
                'games': {'text': f"{int(counter['games_played'])}", 'color': colors['default']}
            }
            for key, data in text_data.items():
                x = layout['start_x'] + layout['text_offsets'][key]
                y = current_y + 20
                self.add_text_box(background, data['text'], x, y, 40, data['color'])
        return background

    def add_text_box(self, image, text, x, y, font_size=20, color=(0, 0, 0)):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.font_path, font_size)
        draw.text((x, y), str(text), font=font, fill=color)

    def resize_circle(self, image, width, height, stroke_width=2):
        image = image.resize((width, height))
        image = image.convert('RGBA')
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, width - 1, height - 1), fill=255)
        stroke = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        for x in range(-stroke_width, stroke_width + 1):
            for y in range(-stroke_width, stroke_width + 1):
                if x * x + y * y <= stroke_width * stroke_width:
                    offset = Image.new('RGBA', (width, height), (0, 0, 0, 255))
                    stroke.paste(offset, (x, y), mask)
        output = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        output.paste(stroke, (0, 0))
        output.paste(image, (0, 0), mask)
        return output

    def split_and_save(self, image, save_path1, save_path2):
        top_image = image.crop((0, 0, 1080, 1350))
        bottom_image = image.crop((1080, 0, 2160, 1350))
        top_image.save(save_path1)
        bottom_image.save(save_path2)

    def draw_line(self, image, position, box_size=(440,15), color=("#bedcff")):
        x, y = position
        w, h = box_size
        draw = ImageDraw.Draw(image)
        draw.rectangle([x, y, x + w, y + h], fill=color)

    def add_main_text_line_split_by_dot(self, image, text, position, box_size=(900,700)):
        draw = ImageDraw.Draw(image)
        main_font = ImageFont.truetype(self.font_path, self.main_font_size)
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

    def add_main_text(self, image, text, position, box_size=(1000, 700)):
        draw = ImageDraw.Draw(image)
        x, y = position
        box_width, box_height = box_size
        #draw.rectangle([x, y, x + box_width, y + box_height], fill=(255, 255, 255))
        main_font = ImageFont.truetype(self.font_path, self.main_font_size)
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

    def add_page3_table(self, image, stats):
        draw = ImageDraw.Draw(image)
        table = Image.open(self.pick_rate_assets_dir / "3" / "table.png")
        image.paste(table, (50, 1100), table)
        stats_font = ImageFont.truetype(self.font_path, 50)
        value_font = ImageFont.truetype(self.font_path, 40)
        stat_title_color = self.black
        value_color = self.black
        stats_x = 100
        stats_y = 1110

        labels = ["라인", "티어", "승률", "픽률", "밴률"]
        spacing = 177
        for i, (label, value) in enumerate(stats.items()):
            draw.text((stats_x + (i * spacing), stats_y), labels[i], font=stats_font, fill=stat_title_color)
            value_text = str(value)
            if label == "티어":
                value_color = self.tier_color[value_text]
                value_text = "   "+value_text
            if i >= 2:
                value_color = self.black
                value_text = f"{value:.2f}"
            draw.text((stats_x + (i * 174), stats_y + 77), value_text, font=value_font, fill=value_color)
        return image

    def draw_ban_info(self, background, blue_team, red_team):
        # Ban 챔피언 이미지 위치
        ban_y = 200
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

    def draw_table_info(self, background, blue_team, red_team, draw, font):
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        # table text 위치
        row_start_y = 365
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

            draw.text((left_side['player'], current_y + 20),
                      str(blue_pos_data['playername']),
                      font=font, fill='white')

            blue_kda = f"{blue_pos_data['kills']} / {blue_pos_data['deaths']} / {blue_pos_data['assists']}"
            draw.text((left_side['kda'], current_y + 20),
                      blue_kda,
                      font=font, fill='white')

            blue_damage = "{:,}".format(blue_pos_data['damagetochampions'])
            draw.text((left_side['damage'], current_y + 20),
                      blue_damage,
                      font=font, fill='white')

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

            draw.text((right_side['player'], current_y + 20),
                      str(red_pos_data['playername']),
                      font=font, fill='white')

    def convert_to_grayscale(self, image):
        return image.convert('L').convert('RGBA')

    def add_title_text(self, image, text, x=50, y=50):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.font_path, self.title_font_size)
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
        font = ImageFont.truetype(self.font_path, self.title_font_size)
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
        line_height = 15
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

    # def apply_alpha_gradient_type1(self, image):
    #     image = image.convert("RGB")
    #
    #     w, h = image.size
    #
    #     first_start_height = 700
    #     first_end_height = 800
    #     second_start_height = 800
    #     second_end_height = 1150
    #     third_start_height = 1150
    #     third_end_height = 1250
    #     fourth_start_height = 1250
    #     fourth_end_height = 1350
    #
    #     first_gradient_height = first_end_height - first_start_height
    #     second_gradient_height = second_end_height - second_start_height
    #     third_gradient_height = third_end_height - third_start_height
    #     fourth_gradient_height = fourth_end_height - fourth_start_height
    #
    #     def create_alpha_array(start, end, height, width):
    #         alpha = np.linspace(start, end, height).reshape(-1, 1)
    #         alpha = np.repeat(alpha, width, axis=1)
    #         return alpha
    #
    #     alpha1 = create_alpha_array(1, 0.3, first_gradient_height, w)
    #     alpha2 = create_alpha_array(0.3, 0.2, second_gradient_height, w)
    #     alpha3 = create_alpha_array(0.2, 0.1, third_gradient_height, w)
    #     alpha4 = create_alpha_array(0.1, 0, fourth_gradient_height, w)
    #
    #     black_background = Image.new("RGB", (w, h), (0, 0, 0))
    #
    #     result_image = image.copy()
    #
    #     def blend_image_section(image, alpha, start_height, end_height):
    #         section = image.crop((0, start_height, w, end_height))
    #         black_section = black_background.crop((0, start_height, w, end_height))
    #         alpha_img = Image.fromarray((alpha * 255).astype(np.uint8), mode='L')
    #         blended_section = Image.composite(section, black_section, alpha_img)
    #         image.paste(blended_section, (0, start_height))
    #
    #     blend_image_section(result_image, alpha1, first_start_height, first_end_height)
    #     blend_image_section(result_image, alpha2, second_start_height, second_end_height)
    #     blend_image_section(result_image, alpha3, third_start_height, third_end_height)
    #     blend_image_section(result_image, alpha4, fourth_start_height, fourth_end_height)
    #
    #     self.add_icon_to_image(result_image, self.logo_path,(500,1270))
    #     return result_image

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
