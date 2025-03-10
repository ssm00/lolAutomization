from abc import ABC
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from datetime import datetime
from util.commonException import CommonError, ErrorCode
import re as regex

class BaseContentProcessor(ABC):

    def __init__(self, database, meta_data):
        self.database = database
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info
        self._setup_common_paths()
        self._setup_fonts()

    def _setup_common_paths(self):
        base_path = Path(__file__).parent.parent
        self.champion_background_dir = base_path / "Assets" / "Image" / "champion"
        self.team_icon_dir = base_path / "Assets" / "Image" / "team_icon"
        self.champion_icon_dir = base_path / "Assets" / "Image" / "champion_icon"
        self.player_dir = base_path / "Assets" / "Image" / "player"
        self.background_dir = base_path / "Assets" / "Image" / "background"
        self.plt_dir = Path(__file__).parent.parent / "PltOutput"

    def _setup_fonts(self):
        base_path = Path(__file__).parent.parent / "Assets" / "Font"
        self.cafe24_font_path = base_path / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"
        self.noto_font_bold_path = base_path / "Noto_Sans_KR" / "static" / "NotoSansKR-Bold.ttf"
        self.noto_font_regular_path = base_path / "Noto_Sans_KR" / "NotoSansKR-VariableFont_wght.ttf"
        self.anton_font_path = base_path / "Anton,Noto_Sans_KR" / "Anton" / "Anton-Regular.ttf"
        self.main_font_size = self.properties.get("main_font_size")
        self.main_line_spacing = self.properties.get("main_line_spacing")

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

    def add_text_box(self, image, text, x, y, font_size=20, color=(0, 0, 0), font_path=None):
        draw = ImageDraw.Draw(image)
        if font_path is None: font_path = self.noto_font_bold_path
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

    def draw_line(self, image, position, box_size=(440,15), color=("#C89B3C")):
        x, y = position
        w, h = box_size
        draw = ImageDraw.Draw(image)
        draw.rectangle([x, y, x + w, y + h], fill=color)

    def convert_to_grayscale(self, image):
        return image.convert('L').convert('RGBA')

    def add_main_text(self, image, text, position, box_size=(990, 700), font_size=50):
        draw = ImageDraw.Draw(image)
        x, y = position
        box_width, box_height = box_size
        #draw.rectangle([x, y, x + box_width, y + box_height], fill=(255, 255, 255, 30))
        main_font = ImageFont.truetype(self.noto_font_bold_path, font_size)
        main_text_color = (255, 255, 255)
        number_color = "#C89B3C"

        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        is_first_word = True
        for word in words:
            word_width = draw.textlength(word + " ", font=main_font)
            if (not is_first_word and (word == "ㆍ" or word == "\u200b")) or (current_width + word_width > box_width):
                if word == "\u200b":
                    lines.append(" ".join(current_line))
                    current_line = []
                    continue
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width
            else:
                current_line.append(word)
                current_width += word_width

            is_first_word = False
        if current_line:
            lines.append(" ".join(current_line))
        line_height = self.main_font_size + self.main_line_spacing
        for line in lines:
            current_x = x
            for word in line.split():
                word_start_x = current_x
                for char in word:
                    is_numeric = char.isdigit() or char == 'ㆍ' or char == '%'
                    char_width = draw.textlength(char, font=main_font)
                    color = number_color if is_numeric else main_text_color
                    draw.text((current_x, y), char, font=main_font, fill=color)
                    current_x += char_width
                space_width = draw.textlength(" ", font=main_font)
                current_x += space_width
            y += line_height
            if y > position[1] + box_height:
                break
        return image

    def add_sub_title_text(self, image, text, x=50, y=50):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.cafe24_font_path, self.title_font_size)
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

    def add_first_page_title(self, image, text, x=120, y=990, box_width=890, box_height=150):
        min_font_size = 50
        current_font_size = self.title_font_size
        draw = ImageDraw.Draw(image)
        pattern = r'\^(.*?)\^'
        parts = regex.split(pattern, text)
        words = []
        for i, part in enumerate(parts):
            if not part:
                continue
            part_words = part.split()
            for word in part_words:
                words.append((word, i % 2 == 1))
        while current_font_size >= min_font_size:
            font = ImageFont.truetype(self.cafe24_font_path, current_font_size)

            def calculate_line_width(line):
                total_width = 0
                for word, _ in line:
                    bbox = draw.textbbox((0, 0), word + " ", font=font)
                    total_width += bbox[2] - bbox[0]
                return total_width
            test_line = [(word, highlight) for word, highlight in words]
            total_width = calculate_line_width(test_line)
            line_height = int(current_font_size + current_font_size * 0.2)
            test_lines = []
            test_line = []
            test_x = 0

            for word, is_highlighted in words:
                bbox = draw.textbbox((0, 0), word + " ", font=font)
                word_width = bbox[2] - bbox[0]

                if test_x + word_width > box_width:
                    test_lines.append(test_line)
                    test_line = []
                    test_x = 0

                test_line.append((word, is_highlighted))
                test_x += word_width
            if test_line:
                test_lines.append(test_line)
            total_height = len(test_lines) * line_height
            if total_width <= box_width or (current_font_size == min_font_size and total_height <= box_height):
                break
            current_font_size -= 10
        if current_font_size < min_font_size:
            current_font_size = min_font_size
            font = ImageFont.truetype(self.cafe24_font_path, current_font_size)
        def draw_text_with_effects(x, y, word, is_highlighted):
            shadow_color = '#2B2B2B'
            shadow_offset = max(3, int(current_font_size / self.title_font_size * 8))
            for i in range(2):
                offset = shadow_offset + i
                draw.text((x + offset, y + offset), word + " ",
                          font=font, fill=shadow_color)
            outline_thickness = max(2, int(current_font_size / self.title_font_size * 5))
            for offset_x in range(-outline_thickness, outline_thickness + 1):
                for offset_y in range(-outline_thickness, outline_thickness + 1):
                    if offset_x * offset_x + offset_y * offset_y <= outline_thickness * outline_thickness:
                        draw.text((x + offset_x, y + offset_y),
                                  word + " ", font=font, fill='black')

            text_color = '#ef2c28' if is_highlighted else 'white'
            draw.text((x, y), word + " ", font=font, fill=text_color)
        # draw.rectangle([x, y, x + box_width, y + box_height], fill=(0, 0, 255, 128))  # 디버깅용
        line_height = int(current_font_size + current_font_size * 0.2)
        current_x = x
        current_line = []
        lines = []
        for word, is_highlighted in words:
            bbox = draw.textbbox((0, 0), word + " ", font=font)
            word_width = bbox[2] - bbox[0]
            if current_x + word_width > x + box_width:
                if len(current_line) == 0:
                    current_line.append((word, is_highlighted))
                    lines.append(current_line)
                    current_line = []
                    current_x = x
                else:
                    lines.append(current_line)
                    current_line = [(word, is_highlighted)]
                    current_x = x + word_width
                    continue
            else:
                current_line.append((word, is_highlighted))
                current_x += word_width
        if current_line:
            lines.append(current_line)
        total_lines_height = len(lines) * line_height
        if total_lines_height > box_height:
            line_height = min(line_height, int(box_height / len(lines)))
            total_lines_height = len(lines) * line_height
        vertical_padding = max(0, (box_height - total_lines_height) // 2)
        current_y = y + vertical_padding
        use_center_align = (len(lines) == 1)
        for line in lines:
            if current_y + line_height > y + box_height:
                break
            if use_center_align:
                line_width = sum(
                    draw.textbbox((0, 0), word + " ", font=font)[2] - draw.textbbox((0, 0), word + " ", font=font)[0]
                    for word, _ in line)
                start_x = x + (box_width - line_width) // 2
            else:
                start_x = x
            current_x = start_x
            for word, is_highlighted in line:
                bbox = draw.textbbox((0, 0), word + " ", font=font)
                word_width = bbox[2] - bbox[0]
                draw_text_with_effects(current_x, current_y, word, is_highlighted)
                current_x += word_width
            current_y += line_height


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

    def add_gradient_box(self, image, x, y, width, height, max_alpha=200, min_alpha=50):
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        gradient_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient_layer)
        for i in range(height):
            progress = 1 - (i / height) ** 2
            alpha = int(min_alpha + progress * (max_alpha - min_alpha))
            draw.line((0, height - i - 1, width - 1, height - i - 1), fill=(0, 0, 0, alpha))
        full_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
        full_layer.paste(gradient_layer, (x, y))
        result = Image.alpha_composite(image, full_layer)
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

    def get_player_image(self, player_name, width, height):
        player_path = self.get_player_image_path(player_name.lower())
        player_image = Image.open(player_path)
        return self.resize_with_crop_image(player_image, width, height)