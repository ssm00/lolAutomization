from pydantic import BaseModel, Field
from typing import Dict, List

class FirstPageResponse(BaseModel):
    title: str = Field(description="강조 표시(^)가 포함된 한 줄 제목")


class SecondPageResponse(BaseModel):
    text: str = Field(description="분석")
    chars: str = Field(description="생성한 text의 length")

class ThirdPageResponse(BaseModel):
    text: str = Field(description="분석")
    chars: str = Field(description="생성한 text의 length")

class FourthPageResponse(BaseModel):
    text: str = Field(description="분석")
    chars: str = Field(description="생성한 text의 length")

class FifthPageResponse(BaseModel):
    text: str = Field(description="분석")
    chars: str = Field(description="생성한 text의 length")
    recommend: str = Field(description="생성한 text의 length")

class InterviewSummary(BaseModel):
    subtitle: str = Field(description="인터뷰 섹션의 부제목")
    content: str = Field(description="인터뷰 내용의 요약")

class InterviewResponse(BaseModel):
    main_title: str = Field(description="전체 인터뷰를 대표하는 메인 타이틀")
    summaries: List[InterviewSummary] = Field(
        description="인터뷰의 주요 부분들에 대한 요약 (3-6개 사이)"
    )
