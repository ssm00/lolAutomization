
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

        # 1단계: 전체 문맥 파악을 위한 프롬프트
        self.context_prompt = ChatPromptTemplate.from_template("""
                    You are a helpful assistant for the company ZyntriQix. Your task is to correct 
                    any spelling discrepancies in the transcribed text. Make sure that the names of 
                    the following products are spelled correctly: ZyntriQix, Digique Plus, 
                    CynapseFive, VortiQore V8, EchoNix Array, OrbitalLink Seven, DigiFractal 
                    Matrix, PULSE, RAPT, B.R.I.C.K., Q.U.A.R.T.Z., F.L.I.N.T. Only add necessary 
                    punctuation such as periods, commas, and capitalization, and use only the 
                    context provided.
                """)

        # 2단계: 세그먼트 수정을 위한 프롬프트
        self.segment_prompt = ChatPromptTemplate.from_template("""
                    앞서 파악한 인터뷰 맥락을 바탕으로, 수정이 필요한 단어를 올바르게 수정해주세요.

                    시작 시간: {start_time}
                    종료 시간: {end_time}
                    원본 텍스트: {text}

                    다음 사항을 고려해주세요:
                    1. 수정이 필요없는 부분은 그대로 반환
                    2. 존재하지 않는 한국어 단어의 경우 문맥 추론을 바탕으로 옳은 단어로 수정
                    3. 문맥상 올바르지 않은 한국어는 올바른 한국어로 수정
                    
                """)
        self.chain = LLMChain(llm=self.llm, prompt=self.context_prompt)  # 올바른 프롬프트 사용


    def refine_interview(self, document):
        try:
            refined_segments = []

            context_chain = LLMChain(llm=self.llm, prompt=self.context_prompt)
            context = context_chain.run(full_text=document['full_text'])

            # 세그먼트별 수정
            segment_chain = LLMChain(llm=self.llm, prompt=self.segment_prompt)

            for segment in document['segments']:
                refined_text = segment_chain.run(
                    start_time=segment['start_time'],
                    end_time=segment['end_time'],
                    text=segment['text']
                )

                refined_segments.append({
                    **segment,
                    'refined_text': refined_text
                })

            return {
                'original_id': document['_id'],
                'refined_segments': refined_segments,
                'context_analysis': context
            }

        except Exception as e:
            print(f"텍스트 개선 중 에러 발생: {str(e)}")
            return None