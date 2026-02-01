from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    job_id: int
    token_id: int
    contract: str
    symbol: str
    name: str
    stage: int
    data: dict
    tags: List[str]
    vibe_score: Optional[int]
    risk_level: Optional[str]
    short_comment: Optional[str]
    report: Optional[str]
    status: str  # 'passed', 'filtered', 'error'
    error_msg: Optional[str]
