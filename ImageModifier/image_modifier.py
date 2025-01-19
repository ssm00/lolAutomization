import os

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np
from pathlib import Path
import re as regex
from Ai.api_call import GenAiAPI

class PickRate:

    def __init__(self, database, properties, gen_api):
        self.database = database
        self.properties = properties
        self.champion_background_dir = Path(__file__).parent.parent / "Assets" / "Image" / "champion"
        self.champion_icon_dir = Path(__file__).parent.parent / "Assets" / "Image" / "champion_icon"
        self.player_dir = Path(__file__).parent.parent / "Assets" / "Image" / "player"
        self.team_icon_dir = Path(__file__).parent.parent / "Assets" / "Image" / "team_icon"
        self.pick_rate_assets_dir = Path(__file__).parent.parent / "Assets" / "PickRate"
        self.font_path = Path(__file__).parent.parent / "Assets" / "Font" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "PickRate"
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

        self.addFont(background, "픽률 ^0.1프로^의 뽀삐?", 65, 790, self.font_path)

        background.save(self.output_dir / "1.png")


    def addFont(self, image, text, x, y, font_path, box_width=948, box_height=220, font_size=96):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(font_path, font_size)
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
            current_y += font_size + line_height

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
            return image.resize((width, height), Image.Resampling.LANCZOS)
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

    def apply_alpha_gradient_type1(self, image):
        image = image.convert("RGB")

        w, h = image.size

        first_start_height = 700
        first_end_height = 800
        second_start_height = 800
        second_end_height = 1150
        third_start_height = 1150
        third_end_height = 1250
        fourth_start_height = 1250
        fourth_end_height = 1350

        first_gradient_height = first_end_height - first_start_height
        second_gradient_height = second_end_height - second_start_height
        third_gradient_height = third_end_height - third_start_height
        fourth_gradient_height = fourth_end_height - fourth_start_height

        def create_alpha_array(start, end, height, width):
            alpha = np.linspace(start, end, height).reshape(-1, 1)
            alpha = np.repeat(alpha, width, axis=1)
            return alpha

        alpha1 = create_alpha_array(1, 0.3, first_gradient_height, w)
        alpha2 = create_alpha_array(0.3, 0.2, second_gradient_height, w)
        alpha3 = create_alpha_array(0.2, 0.1, third_gradient_height, w)
        alpha4 = create_alpha_array(0.1, 0, fourth_gradient_height, w)

        black_background = Image.new("RGB", (w, h), (0, 0, 0))

        result_image = image.copy()

        def blend_image_section(image, alpha, start_height, end_height):
            section = image.crop((0, start_height, w, end_height))
            black_section = black_background.crop((0, start_height, w, end_height))
            alpha_img = Image.fromarray((alpha * 255).astype(np.uint8), mode='L')
            blended_section = Image.composite(section, black_section, alpha_img)
            image.paste(blended_section, (0, start_height))

        blend_image_section(result_image, alpha1, first_start_height, first_end_height)
        blend_image_section(result_image, alpha2, second_start_height, second_end_height)
        blend_image_section(result_image, alpha3, third_start_height, third_end_height)
        blend_image_section(result_image, alpha4, fourth_start_height, fourth_end_height)

        self.add_icon_to_image(result_image, self.logo_path,(500,1270))
        return result_image

    def convert_png(self):
        image_extensions = ['.jpg', '.jpeg', '.JPG', '.JPEG']
        for file_path in (self.player_dir.parent.parent / "PickRate" / "1").iterdir():
            if file_path.suffix in image_extensions:
                try:
                    with Image.open(file_path) as img:
                        img = img.convert('RGBA')
                        new_path = file_path.with_suffix('.png')
                        img.save(new_path, 'PNG', optimize=True, quality=95)
                        os.remove(file_path)
                except Exception as e:
                    print(f"오류 발생 ({file_path.name}): {str(e)}")
