import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, T5ForConditionalGeneration
import pandas as pd
from tqdm import tqdm
import nltk
from nltk.translate.bleu_score import sentence_bleu
from sklearn.metrics import accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

# NLTK 다운로드 (BLEU 스코어 계산용)
try:
    nltk.download('punkt')
except:
    pass


class KoreanTextCorrector:
    """
    언어 모델 기반 한국어 텍스트 교정 클래스
    """

    def __init__(self, model_name="KETI-AIR/ke-t5-base", device=None):
        """
        한국어 언어 모델 기반 교정기 초기화

        Args:
            model_name (str): 사용할 모델 이름
                - "KETI-AIR/ke-t5-base": 한국어 T5 모델
                - "gogamza/kobart-base": 한국어 BART 모델
            device (str): 사용할 장치 ('cuda', 'cpu')
        """
        self.model_name = model_name

        # 장치 설정 (GPU 사용 가능 시 GPU 사용)
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        print(f"모델 '{model_name}'을(를) '{self.device}' 장치에 로드합니다...")

        # 토크나이저 로드 (use_fast=False로 설정)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # 모델 로드
        if 't5' in model_name.lower():
            self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        elif 'roberta' in model_name.lower():
            from transformers import RobertaForMaskedLM
            self.model = RobertaForMaskedLM.from_pretrained(model_name)
        else:  # BART 또는 다른 Seq2Seq 모델
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        self.model.to(self.device)
        self.model.eval()  # 평가 모드로 설정

        # 한국어 도메인 특화 사전 (필요시 확장)
        self.domain_dict = {
            "LCK": True,
            "DRX": True,
            "POM": True,
            "1아운드": "1라운드",
            "플레인": "플레이",
            "승민 축하": "승리 축하"
        }

        # 작업별 프롬프트 템플릿
        self.prompt_templates = {
            "correction": "오류 수정: {text}",
            "grammar": "문법 교정: {text}",
            "spell": "맞춤법 교정: {text}",
            "context": "문맥에 맞게 교정: {text}"
        }

        print("모델 로드 완료!")

    def correct_text(self, text, task="correction", max_length=512, num_beams=5,
                     apply_domain_rules=True):
        """
        텍스트 교정 수행

        Args:
            text (str): 교정할 텍스트
            task (str): 교정 작업 유형 ('correction', 'grammar', 'spell', 'context')
            max_length (int): 생성할 최대 토큰 수
            num_beams (int): 빔 서치 크기
            apply_domain_rules (bool): 도메인 특화 규칙 적용 여부

        Returns:
            str: 교정된 텍스트
        """
        # 도메인 특화 규칙 적용 (간단한 치환)
        if apply_domain_rules:
            for error, correction in self.domain_dict.items():
                if isinstance(correction, str) and error in text:
                    text = text.replace(error, correction)

        # 프롬프트 생성
        prompt = self.prompt_templates.get(task, self.prompt_templates["correction"])
        input_text = prompt.format(text=text)

        # 토큰화
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=max_length,
                                truncation=True, padding="max_length")
        inputs = inputs.to(self.device)

        # 텍스트 생성
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_length=max_length,
                num_beams=num_beams,
                early_stopping=True,
                do_sample=False  # 결정적 결과를 위해 샘플링 비활성화
            )

        # 디코딩 및 후처리
        corrected_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # KE-T5 모델의 경우 프롬프트를 반복하는 경우가 있어서 제거
        if "오류 수정: " in corrected_text:
            corrected_text = corrected_text.replace("오류 수정: ", "")
        elif "문법 교정: " in corrected_text:
            corrected_text = corrected_text.replace("문법 교정: ", "")
        elif "맞춤법 교정: " in corrected_text:
            corrected_text = corrected_text.replace("맞춤법 교정: ", "")
        elif "문맥에 맞게 교정: " in corrected_text:
            corrected_text = corrected_text.replace("문맥에 맞게 교정: ", "")

        return corrected_text

    def batch_correct(self, texts, task="correction", batch_size=8, **kwargs):
        """
        배치 텍스트 교정

        Args:
            texts (list): 교정할 텍스트 목록
            task (str): 교정 작업 유형
            batch_size (int): 배치 크기

        Returns:
            list: 교정된 텍스트 목록
        """
        results = []

        # 배치 단위로 처리
        for i in tqdm(range(0, len(texts), batch_size), desc="배치 처리 중"):
            batch = texts[i:i + batch_size]
            batch_results = [self.correct_text(text, task=task, **kwargs) for text in batch]
            results.extend(batch_results)

        return results

    def evaluate(self, test_data, gold_data, metrics=None):
        """
        교정 결과 평가

        Args:
            test_data (list): 교정할 텍스트 목록
            gold_data (list): 정답 텍스트 목록
            metrics (list): 사용할 평가 지표 목록 (기본값: ['exact_match', 'bleu'])

        Returns:
            dict: 평가 결과
        """
        if metrics is None:
            metrics = ['exact_match', 'bleu']

        # 교정 수행
        corrected = self.batch_correct(test_data)

        results = {}

        # 평가 지표 계산
        if 'exact_match' in metrics:
            exact_matches = [1 if c == g else 0 for c, g in zip(corrected, gold_data)]
            results['exact_match'] = sum(exact_matches) / len(exact_matches)

        if 'bleu' in metrics:
            bleu_scores = []
            for c, g in zip(corrected, gold_data):
                c_tokens = list(c)  # 한국어는 문자 단위로 토큰화
                g_tokens = list(g)
                bleu = sentence_bleu([g_tokens], c_tokens)
                bleu_scores.append(bleu)
            results['bleu'] = sum(bleu_scores) / len(bleu_scores)

        if 'word_accuracy' in metrics:
            word_correct = 0
            word_total = 0
            for c, g in zip(corrected, gold_data):
                c_words = c.split()
                g_words = g.split()

                # 두 문장의 길이가 다를 수 있으므로 최소 길이만큼만 비교
                min_len = min(len(c_words), len(g_words))
                word_correct += sum([1 for i in range(min_len) if c_words[i] == g_words[i]])
                word_total += max(len(c_words), len(g_words))  # 모든 단어 고려

            results['word_accuracy'] = word_correct / word_total if word_total > 0 else 0

        # 교정 예시 함께 반환
        results['examples'] = list(zip(test_data, corrected, gold_data))

        return results

    def finetune(self, train_data, valid_data=None, epochs=3, batch_size=8,
                 learning_rate=5e-5, save_path=None):
        """
        교정 작업을 위한 미세 조정 (파인튜닝)

        Args:
            train_data (list or tuple): 훈련 데이터
                - list일 경우: [(오류 텍스트, 정답 텍스트), ...]
                - pandas.DataFrame일 경우: 'error', 'correct' 열 필요
            valid_data: 검증 데이터 (형식은 train_data와 동일)
            epochs (int): 훈련 에폭 수
            batch_size (int): 배치 크기
            learning_rate (float): 학습률
            save_path (str): 모델 저장 경로

        Returns:
            dict: 훈련 결과 (손실 등)
        """
        # 파이토치 훈련 코드 구현
        # (실제 구현은 훈련 데이터 형식과 모델에 따라 달라질 수 있음)

        print("미세 조정 기능은 아직 구현되지 않았습니다.")
        return {"status": "not_implemented"}


# 예시 실행 코드
if __name__ == "__main__":
    # 교정기 초기화
    corrector = KoreanTextCorrector()

    # 예시 텍스트
    test_examples = [
        "2020 LCK컵 플레인 1아운드 두 번째 매치 하나 생명과 DRX의 대결 승리한 하나 생명의 POM으로 선정된 재카 선수 만나보겠습니다.",
        "승민 축하드립니다. 감사합니다.",
        "오늘 승리의 요인은 뭐다고 생각하세요?",
        "몇일 전부터 챔피언 연승률이 잘롷지 않아서 연습을 많이 했습니다.",
        "탑랜이 정글에서 활약을 많이 해줘서 게인이 수월했습니다."
    ]

    # 정답 텍스트
    gold_examples = [
        "2020 LCK컵 플레이 1라운드 두 번째 매치 하나 생명과 DRX의 대결 승리한 하나 생명의 POM으로 선정된 재커 선수 만나보겠습니다.",
        "승리 축하드립니다. 감사합니다.",
        "오늘 승리의 요인은 뭐라고 생각하세요?",
        "며칠 전부터 챔피언 승률이 좋지 않아서 연습을 많이 했습니다.",
        "탑 라인이 정글에서 활약을 많이 해줘서 게임이 수월했습니다."
    ]

    print("=== 단일 텍스트 교정 예시 ===")
    for text in test_examples:
        corrected = corrector.correct_text(text)
        print(f"원본: {text}")
        print(f"교정: {corrected}")
        print("-" * 50)

    print("\n=== 배치 텍스트 교정 예시 ===")
    batch_results = corrector.batch_correct(test_examples)
    for original, corrected in zip(test_examples, batch_results):
        print(f"원본: {original}")
        print(f"교정: {corrected}")
        print("-" * 50)

    print("\n=== 평가 예시 ===")
    eval_results = corrector.evaluate(test_examples, gold_examples,
                                      metrics=['exact_match', 'bleu', 'word_accuracy'])

    print(f"정확 일치율: {eval_results['exact_match']:.4f}")
    print(f"BLEU 점수: {eval_results['bleu']:.4f}")
    print(f"단어 정확도: {eval_results['word_accuracy']:.4f}")

    print("\n=== 교정 예시 ===")
    for original, corrected, gold in eval_results['examples'][:3]:  # 처음 3개만 출력
        print(f"원본: {original}")
        print(f"교정: {corrected}")
        print(f"정답: {gold}")
        print("-" * 50)