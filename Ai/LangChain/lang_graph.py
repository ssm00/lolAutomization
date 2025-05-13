import os

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tracers import LangChainTracer
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableMap
from typing import TypedDict, List, Literal
from langchain_openai import ChatOpenAI
from langchain_mongodb import MongoDBAtlasVectorSearch
from Ai.LangChain.response_form import *

class RAGState(TypedDict):
    original_prompt: str
    query: str
    documents: List[Document]
    final_response: dict
    champion: str

class LangGraph:

    def __init__(self, mongo, database, meta_data, patch):
        load_dotenv()
        tracer = LangChainTracer(
            project_name=os.getenv('LANGCHAIN_PROJECT', 'default-project')
        )
        self.mongo = mongo
        self.database = database
        self.patch = patch
        self.prompt = meta_data.prompt
        self.embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.mongo.db['patch_info'],
            embedding=self.embedding,
            index_name="patch_search_index",
            text_key="text"
        )

    def rewrite_query(self, state: RAGState) -> RAGState:
        llm = ChatOpenAI(model="gpt-4o-mini")
        system_prompt = """
            아래의 프롬프트는 챔피언 추천 기사 생성을 위한 지침입니다.
            이 지침을 기반으로 Vector Search 에 적합한 간단한 핵심 질문 한 문장으로 요약해 주세요.
            예: "제드가 상대하기 쉬운 챔피언은 누구인가?"
            응답은 반드시 한 문장만 출력하세요.
            ---------
        """
        chain = PromptTemplate.from_template(system_prompt + "\n{original_prompt}") | llm
        query = chain.invoke({"original_prompt": state["original_prompt"]}).content.strip()
        state["query"] = query
        print("반환된 쿼리임", query)
        return state

    def retrieve_documents(self, state: RAGState) -> RAGState:
        docs = self.vector_store.similarity_search(
            query=state["query"],
            k=3,
            pre_filter={
                "champion": state["champion"],
                "patch_version": str(self.patch.version)
            }
        )
        state["documents"] = docs
        return state

    def generate_response(self, state: RAGState) -> RAGState:
        llm = ChatOpenAI(model="gpt-4o-mini")
        format_instructions = JsonOutputParser(pydantic_object=FifthPageResponse).get_format_instructions()
        final_prompt = PromptTemplate.from_template(f"""
        {{original_prompt}}\n관련 패치 정보:\n{{documents}}
        \n응답은 반드시 다음 JSON 형식을 따라야 합니다:
        {{format_instructions}}
        """)
        documents_text = "\n".join([doc.page_content for doc in state["documents"]])
        chain = final_prompt | llm | JsonOutputParser()
        result = chain.invoke({"original_prompt":state['original_prompt'], "documents": documents_text, "format_instructions":format_instructions})
        state["final_response"] = result
        return state

    def output_node(self, state: RAGState) -> dict:
        return state["final_response"]

    def run_page5_article_rag(self, match_id, player_name, max_chars):
        graph = StateGraph(RAGState)
        graph.add_node("rewrite_query", RunnableLambda(self.rewrite_query))
        graph.add_node("retriever", RunnableLambda(self.retrieve_documents))
        graph.add_node("generate", RunnableLambda(self.generate_response))
        graph.add_node("output", RunnableLambda(self.output_node))
        # 흐름 정의
        graph.set_entry_point("rewrite_query")
        graph.add_edge("rewrite_query", "retriever")
        graph.add_edge("retriever", "generate")
        graph.add_edge("generate", "output")
        graph.set_finish_point("output")
        app = graph.compile()
        #----------------------------------------
        prompt_template = PromptTemplate.from_template(self.prompt.get("pick_rate").get("long").get("page5_rag"))
        game_df = self.database.get_game_data(match_id)
        player_data = game_df[game_df["playername"] == player_name].iloc[0]
        counter_df = self.database.get_counter_champion(player_data["name_us"], player_data["position"], self.patch.version)
        top_counters = counter_df.head(3)
        line_kr = {"top": "탑", "jungle": "정글", "mid": "미드", "bottom": "원딜", "support": "서포터", }
        player_champion_kr = self.database.get_name_kr(player_data["name_us"])
        counters_payload = [
            {
                "name_kr": r["name_kr"],
                "win_rate": r["win_rate"],
                "games_played": r["games_played"],
                "kda_diff": r["kda_diff"],
                "counter_score": r["counter_score"],
            }
            for _, r in top_counters.iterrows()
        ]
        original_prompt = prompt_template.format(
            player_champion_kr=player_champion_kr,
            position=line_kr[player_data['position']],
            max_chars=max_chars,
            counters=counters_payload,
        )
        response = app.invoke({"original_prompt": original_prompt,"champion": player_champion_kr})
        return response['final_response']
