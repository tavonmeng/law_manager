import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

try:
    from backend.workflow import build_graph
except ModuleNotFoundError:
    from workflow import build_graph

# ─── 数据库 ───────────────────────────────────────────────────
import os
db_path = os.environ.get("DATABASE_PATH", "./test_records.db")
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL, echo=False)


class TestRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    module_name: str
    input_data: str
    analysis_reasoning: str
    issues_json: str
    evaluations_json: str


SQLModel.metadata.create_all(engine)


# ─── 数据模型 ─────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    module_name: str
    table_data: str


class IssueItem(BaseModel):
    title: str
    fact: str
    law: str
    suggestion: str   # 每条 issue 的针对性投资人建议


class AnalyzeResponse(BaseModel):
    analysis_reasoning: str
    issues: List[IssueItem]


class EvaluationItem(BaseModel):
    issue_title: str
    expected_answer: str
    improvement_notes: str


class SaveRecordRequest(BaseModel):
    module_name: str
    input_data: str
    analysis_reasoning: str
    issues: List[IssueItem]
    evaluations: List[EvaluationItem]


class RecordSummary(BaseModel):
    id: int
    created_at: str
    module_name: str
    issue_count: int


class RecordDetail(BaseModel):
    id: int
    created_at: str
    module_name: str
    input_data: str
    analysis_reasoning: str
    issues: List[IssueItem]
    evaluations: List[EvaluationItem]


# ─── FastAPI ──────────────────────────────────────────────────
app = FastAPI(
    title="合规尽调 Agent API",
    description="LangGraph 驱动的合规分析 + 评测持久化 API",
    version="3.1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

agent_workflow = build_graph()


def parse_issues_from_report(report_text: str) -> List[IssueItem]:
    """将 Agent 输出的 Markdown 按 ### 拆分，解析事实/法律/建议三段结构。"""
    issues = []
    sections = report_text.split("\n### ")
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.split("\n")
        title = lines[0].lstrip("# ").strip()
        fact = law = suggestion = ""
        current_field = None
        for line in lines[1:]:
            stripped = line.strip().lstrip("-").strip()
            if stripped.startswith("**事实认定**") or stripped.startswith("**第一点"):
                current_field = "fact"
                fact = stripped.split("**", 3)[-1].strip().lstrip("：:").strip()
            elif stripped.startswith("**法律依据**") or stripped.startswith("**第二点"):
                current_field = "law"
                law = stripped.split("**", 3)[-1].strip().lstrip("：:").strip()
            elif stripped.startswith("**风险评估与投资人建议**") or stripped.startswith("**投资人建议**") or stripped.startswith("**第三点"):
                current_field = "suggestion"
                suggestion = stripped.split("**", 3)[-1].strip().lstrip("：:").strip()
            elif current_field and stripped:
                # 多行续接
                if current_field == "fact":
                    fact += "\n" + stripped
                elif current_field == "law":
                    law += "\n" + stripped
                elif current_field == "suggestion":
                    suggestion += "\n" + stripped

        if title and "暂未发现" not in title:
            issues.append(IssueItem(title=title, fact=fact, law=law, suggestion=suggestion))

    return issues if issues else [IssueItem(
        title="未发现实质性合规风险",
        fact="经核查，目标公司该模块暂未发现实质性合规风险。",
        law="-",
        suggestion="-"
    )]


# ─── 路由 ────────────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    final = agent_workflow.invoke({
        "module_name": request.module_name,
        "table_data": request.table_data,
        "analysis_reasoning": "",
        "issues_report": "",
    })
    return AnalyzeResponse(
        analysis_reasoning=final.get("analysis_reasoning", ""),
        issues=parse_issues_from_report(final.get("issues_report", ""))
    )


@app.post("/api/records", response_model=dict)
async def save_record(req: SaveRecordRequest):
    record = TestRecord(
        module_name=req.module_name,
        input_data=req.input_data,
        analysis_reasoning=req.analysis_reasoning,
        issues_json=json.dumps([i.model_dump() for i in req.issues], ensure_ascii=False),
        evaluations_json=json.dumps([e.model_dump() for e in req.evaluations], ensure_ascii=False),
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return {"success": True, "record_id": record.id}


@app.get("/api/records", response_model=List[RecordSummary])
async def list_records():
    with Session(engine) as session:
        records = session.exec(select(TestRecord).order_by(TestRecord.id.desc())).all()
    return [
        RecordSummary(id=r.id, created_at=r.created_at, module_name=r.module_name,
                      issue_count=len(json.loads(r.issues_json)))
        for r in records
    ]


@app.get("/api/records/{record_id}", response_model=RecordDetail)
async def get_record(record_id: int):
    with Session(engine) as session:
        record = session.get(TestRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return RecordDetail(
        id=record.id, created_at=record.created_at, module_name=record.module_name,
        input_data=record.input_data, analysis_reasoning=record.analysis_reasoning,
        issues=[IssueItem(**i) for i in json.loads(record.issues_json)],
        evaluations=[EvaluationItem(**e) for e in json.loads(record.evaluations_json)],
    )
