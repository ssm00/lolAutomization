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



class Interview:

    def __init__(self, database, meta_data):
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

    def title_page(self):
        pass

    def main_page(self):
        pass
