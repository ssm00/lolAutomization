
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Dict, List

class FirstPageResponse(BaseModel):
    title: str = Field(description="강조 표시(^)가 포함된 한 줄 제목")


class SecondPageResponse(BaseModel):
    team_analysis: str = Field(description="팀 분석")
    ban_pick_strategy: str = Field(description="밴픽 전략 분석")
    player_performance: str = Field(description="선수 성과 분석")
    key_points: List[str] = Field(description="주요 포인트")

class ThirdPageResponse(BaseModel):
    champion_overview: str = Field(description="챔피언 개요")
    meta_analysis: str = Field(description="메타 분석")
    statistics: Dict = Field(description="통계 데이터")