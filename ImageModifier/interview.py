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
        super().__init__(database, meta_data)
        self.database = database
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info

        #path
        self.title_background_dir = Path(__file__).parent.parent / "Assets" / "Interview" / "title.png"
        self.main_background_dir = Path(__file__).parent.parent / "Assets" / "Interview" / "main.png"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "Interview"

        # properties
        self.title_font_size = self.properties.get("title_font_size")

    def title_page(self):
        pass

    def main_page(self):
        pass
