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
import pandas as pd
from ImageModifier.image_utils import BaseContentProcessor


class MatchResult(BaseContentProcessor):

    def __init__(self, database, meta_data):
        super().__init__(database, meta_data)
        self.database = database
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info

        self.title_background_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "title.png"
        self.main_background_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "main.png"
        self.gradient_dir = Path(__file__).parent.parent / "Assets" / "MatchResult" / "gradient.png"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "MatchResult"

        #properties
        self.score_font_size = self.properties.get("match_result_score_font_size")
        self.player_name_font_size = self.properties.get("match_result_player_name_font_size")
        self.title_font_size = self.properties.get("title_font_size")

    def title_page(self, match_id, player_name):
        background = Image.open(self.title_background_dir)
        game_df = self.database.get_game_data(match_id)
        player_team = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        opp_team_name = game_df[game_df['teamname'] != player_team]['teamname'].iloc[0]
        name_us = game_df[game_df['teamname'] != player_team]['name_us'].iloc[0]
        league_title = f"{game_df['game_year'].iloc[0]} {game_df['league'].iloc[0]} {game_df['split'].iloc[0]}"

        #선수, 그라데이션
        player_image = self.get_player_image(player_name, 520, 467)
        background.paste(player_image, (470, 461), player_image)
        #gradient = Image.open(self.gradient_dir)
        #background.paste(gradient, (90,230), gradient)
        background = self.add_gradient_box(background, 90, 230, 900, 700)

        #팀로고
        player_team_icon = Image.open(self.team_icon_dir / f"{player_team}.png")
        opp_team_icon = Image.open(self.team_icon_dir / f"{opp_team_name}.png")
        player_team_icon = self.resize_image(player_team_icon, 200, 200)
        opp_team_icon = self.resize_image(opp_team_icon, 200, 200)
        background.paste(player_team_icon, (134,270), player_team_icon)
        background.paste(opp_team_icon, (134,636), opp_team_icon)

        #스코어
        player_team_score, opp_team_score = self.database.get_sets_score(match_id, player_team, opp_team_name)
        self.add_text_box(background, player_team_score, 395, 297, 96, (255,255,255), self.anton_font_path)
        self.add_text_box(background, opp_team_score, 395, 663, 96, (255,255,255), self.anton_font_path)

        self.add_text_box(background, league_title, 134, 512, 45, (255,255,255), self.main_font_path)
        self.add_first_page_title(background, "펜타킬 한 도란", 100,990)
        self.save_image(background, match_id, "1")

    def main_page(self, match_id, player_name):
        background = Image.open(self.main_background_dir)
        game_df = self.database.get_game_data(match_id)
        player_team_name = game_df[game_df['playername'] == player_name]['teamname'].iloc[0]
        opp_team_name = game_df[game_df['teamname'] != player_team_name]['teamname'].iloc[0]
        name_us = game_df[game_df['teamname'] != player_team_name]['name_us'].iloc[0]

        #팀 로고
        player_team_icon = Image.open(self.team_icon_dir / f"{player_team_name}.png")
        opp_team_icon = Image.open(self.team_icon_dir / f"{opp_team_name}.png")
        player_team_icon = self.resize_image(player_team_icon, 150, 150)
        opp_team_icon = self.resize_image(opp_team_icon, 150, 150)
        background.paste(player_team_icon, (154, 240), player_team_icon)
        background.paste(opp_team_icon, (768, 240), opp_team_icon)

        # 스코어
        player_team_score, opp_team_score = self.database.get_sets_score(match_id, player_team_name, opp_team_name)
        self.add_text_box(background, f"{player_team_score} - {opp_team_score}", 451, 231, 96, (255, 255, 255), self.anton_font_path)

        #이름 및 테이블
        overall_mvp_score = self.database.calculate_overall_mvp_score(game_df, match_id, player_name)
        self.draw_overall_mvp_table(background, overall_mvp_score, player_team_name, opp_team_name)
        self.save_image(background, match_id, "2")

    def draw_overall_mvp_table(self, background, overall_mvp_df, player_team, opp_team):
        draw = ImageDraw.Draw(background)
        positions = ['top', 'jungle', 'mid', 'bottom', 'support']
        row_start_y = 478
        row_height = 147

        left_score_x = 380
        right_score_x = 640

        left_name_x = 158
        right_name_x = 790

        score_font = ImageFont.truetype(self.anton_font_path, 40)
        name_font = ImageFont.truetype(self.anton_font_path, 48)

        for i, position in enumerate(positions):
            current_y = row_start_y + (i * row_height)
            blue_player_data = overall_mvp_df[(overall_mvp_df['position'] == position) &
                                              (overall_mvp_df['teamname'] == player_team)].iloc[0]
            blue_mvp_score = blue_player_data['mvp_score']
            blue_player_name = blue_player_data['playername']

            red_player_data = overall_mvp_df[(overall_mvp_df['position'] == position) &
                                             (overall_mvp_df['teamname'] == opp_team)].iloc[0]
            red_mvp_score = red_player_data['mvp_score']
            red_player_name = red_player_data['playername']

            draw.text((left_score_x, current_y), f"{blue_mvp_score:.1f}", font=score_font, fill='white', anchor='lm')
            draw.text((right_score_x, current_y), f"{red_mvp_score:.1f}", font=score_font, fill='white', anchor='lm')

            draw.text((left_name_x, current_y), blue_player_name, font=name_font, fill='white',anchor='lm')
            draw.text((right_name_x, current_y), red_player_name, font=name_font, fill='white',anchor='lm')

        return background
