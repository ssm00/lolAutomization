from pydantic import BaseModel, Field
from typing import Dict, List

class FirstPageResponse(BaseModel):
    title: str = Field(description="강조 표시(^)가 포함된 한 줄 제목")


class SecondPageResponse(BaseModel):
    text: str = Field(description="분석")

class ThirdPageResponse(BaseModel):
    text: str = Field(description="분석")

class FourthPageResponse(BaseModel):
    text: str = Field(description="분석")

class FifthPageResponse(BaseModel):
    text: str = Field(description="분석")
    chars: str = Field(description="생성한 text의 length")
