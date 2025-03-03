
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import os
from dotenv import load_dotenv
from datetime import datetime


class TextRefiner:

    def __init__(self):
        load_dotenv()
        model_name=os.getenv('MODEL_NAME', 'gpt-4o-mini')
        self.llm = ChatOpenAI(model_name=model_name, temperature=0.3)

        self.context_prompt = ChatPromptTemplate.from_template("""
            당신은 한국어 문장을 교정하는 전문가입니다. 
            주어진 문장에서 다음을 수행하세요:
            1. 오타 및 맞춤법 오류 수정
            2. 문법적으로 올바르게 수정
            3. 존재하지 않는 단어를 탐지한 뒤 문맥을 고려하여 단어 수정 
            4. 원본 문장 전체가 아닌 잘못된 단어만 수정
            
            입력 : {full_text}
            
            출력 형식은 반드시 다음과 같아야 합니다:
            - 원본: [입력된 문장]
            - 교정: [교정된 문장]
                """)

        self.chain = self.context_prompt | self.llm


    def refine_interview(self, document):
        refined_segments = self.chain.invoke({'full_text':document['full_text']})
        return {
            'original_id': document['_id'],
            'refined_segments': refined_segments,
        }


