from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 使用阿里云千问API的兼容模式
QWEN_API_KEY = "sk-fa98b1c7dd81458c87c0b0c0616e1d90"
QWEN_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class AgentState(TypedDict):
    module_name: str
    table_data: str
    analysis_reasoning: str
    issues_report: str


def get_llm():
    return ChatOpenAI(
        api_key=QWEN_API_KEY,
        base_url=QWEN_API_BASE,
        model="qwen-plus",
        temperature=0.1
    )


# ─── Node 1: 合规数据逐条推断 ──────────────────────────────────
def analyze_data_node(state: AgentState):
    llm = get_llm()
    module_name = state["module_name"]
    table_data = state["table_data"]

    system_prompt = f"""角色：你是一名专注于劳动法合规领域的尽职调查律师，受投资方委托对目标公司进行合规审查。
任务：对目标公司【{module_name}】模块的数据进行逐项核查。
风格要求：语言简洁、结论明确、逻辑严密，遵循律师工作底稿的行文风格，避免冗余修辞。

【五险一金】模块必须严格按照以下7个核查要点逐一检验：

社保部分（养老、医疗、失业、工伤、生育）：
1. 是否为"全员"缴纳社保 — 对比各险种"实际缴费人数"与"签署劳动合同的员工人数"，判断是否存在未参保人员。
2. 是否以"实际工资"为基数缴纳社保 — 检查单位缴费基数、个人缴费基数是否与实际工资总额匹配，是否存在低基数申报或统一按最低基数缴纳等异常。
3. 是否从"员工入职"起开始缴纳社保 — 审查是否存在入职后延迟参保、试用期不缴纳等情形。

公积金部分（住房公积金）：
4. 是否为"全员"缴纳公积金 — 对比住房公积金实际缴费人数与签署劳动合同的员工人数，判断是否存在漏缴。
5. 是否以"实际工资"为基数缴纳公积金 — 检查公积金缴费基数是否与员工实际工资匹配。
6. 是否从"员工入职"起开始缴纳公积金 — 审查是否存在入职后延迟缴纳住房公积金的情形。

其他：
7. 是否存在委托第三方缴纳五险一金的情况 — 审查是否存在通过第三方人力资源公司或外包机构代为缴纳社保和公积金的情形（可能构成用工关系不清晰的法律风险）。

请严格按照上述7个要点逐条核查，每条给出"合规"或"存在风险"的明确判断，辅以简要数据依据。
重要：如果所提供的材料不足以支撑对某个要点的判断，请直接说明"本项所提供材料不足以判断，需补充[具体所需数据]"，不得在缺乏数据依据的情况下进行推测或臆断。"""

    human_msg = HumanMessage(
        content=f"目标公司提供的尽调材料（含数据表格及可能的补充说明）如下：\n{table_data}\n\n请结合全部材料内容，逐条核查并出具判断。"
    )
    response = llm.invoke([SystemMessage(content=system_prompt), human_msg])
    return {"analysis_reasoning": response.content}


# ─── Node 2: 结构化输出 Issue + 逐条投资人建议 ───────────────
def format_issues_node(state: AgentState):
    llm = get_llm()
    analysis_reasoning = state["analysis_reasoning"]

    system_prompt = """角色：你是一名代表投资方的合规律师，正在撰写尽调法律意见书中的合规风险提示章节。
风格要求：全文以律师法律意见书口吻行文，简明扼要，直击要害，杜绝冗余修辞和口语化表达。

请根据前序核查结论，提取所有存在合规风险的事项，并严格按以下格式逐条输出：

### [Issue编号]：[问题定性标题]

- **事实认定**：用1-2句话精准概括客观数据异常。例如："经核查，目标公司签署劳动合同员工15人，养老保险实际缴费13人，存在2人未参保的事实。"
- **法律依据**：援引具体法律条文原文，必须真实准确。例如："《社会保险法》第五十八条：'用人单位应当自用工之日起三十日内为其职工向社会保险经办机构申请办理社会保险登记。'"
- **风险评估与投资人建议**：站在投资人视角，简要评估该Issue对投资的具体风险敞口，并给出简明的应对建议。格式要求：先用1句话点明核心风险，再以编号列出建议，每条建议不超过1句话。例如：
  该事项构成劳动合规瑕疵，目标公司面临员工追缴请求及行政处罚风险，可能产生约[X]万元财务敞口。建议：
  （1）要求目标公司披露未参保人员明细及原因；
  （2）测算补缴金额及滞纳金，在交易对价中予以扣减；
  （3）将全员补缴完毕列为交割前提条件；
  （4）要求创始股东就该事项承担专项赔偿义务。

注意事项：
1. 每条Issue的建议必须针对该具体问题的风险敞口展开，不得泛泛而谈。
2. 如未发现实质性合规问题，输出"经核查，目标公司该模块暂未发现实质性合规风险"。
3. 仅输出有充分数据支撑的Issue。前序核查中标注为"材料不足"的项，不作为Issue输出，在末尾汇总说明即可。"""

    human_msg = HumanMessage(
        content=f"前序核查结论如下：\n{analysis_reasoning}\n\n请提取风险事项并按规定格式输出法律意见。"
    )
    response = llm.invoke([SystemMessage(content=system_prompt), human_msg])
    return {"issues_report": response.content}


# ─── 构建 LangGraph ────────────────────────────────────────────
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("format_issues", format_issues_node)

    workflow.set_entry_point("analyze_data")
    workflow.add_edge("analyze_data", "format_issues")
    workflow.add_edge("format_issues", END)

    app = workflow.compile()
    return app
