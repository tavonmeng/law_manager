import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="合规尽调 Agent 评测平台",
    layout="wide",
    page_icon="⚖️",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #161b27; }
    .issue-card {
        background: #1a1f2e;
        border-left: 3px solid #4f8ef7;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

BASE_URL = "http://localhost:8000"


def markdown_to_df(md_text: str) -> pd.DataFrame:
    """Markdown 表格 → DataFrame"""
    try:
        lines = [l for l in md_text.strip().split("\n") if l.strip() and "---" not in l]
        if len(lines) < 2:
            return pd.DataFrame()
        cols = [c.strip() for c in lines[0].split("|") if c.strip()]
        rows = []
        for line in lines[1:]:
            row = [c.strip() for c in line.split("|") if c.strip()]
            if row:
                rows.append(row)
        return pd.DataFrame(rows, columns=cols[:len(rows[0])] if rows else cols)
    except Exception:
        return pd.DataFrame()


# ─── 侧边栏 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ 合规尽调 Agent")
    st.caption("投资方合规审查评测系统")
    st.divider()
    page = st.radio("导航", ["🧪 新建测试", "📂 历史记录"], label_visibility="collapsed")
    st.divider()
    module_options = ["五险一金", "劳动合同", "劳动纠纷", "劳务派遣"]
    selected_module = st.selectbox("分析模块", module_options)
    api_base = st.text_input("后端地址", value=BASE_URL)

# ═══════════════════════════════════════════════════════════════
# 页面 1：新建测试
# ═══════════════════════════════════════════════════════════════
if "新建测试" in page:
    st.title("🧪 新建合规尽调测试")
    st.markdown("编辑目标公司数据 → 运行 Agent → 审阅法律意见 → 填写评测 → 提交保存。")

    # ── 数据输入 ──────────────────────────────────────────────
    st.markdown("### 📊 目标公司业务数据")
    default_data = {
        "序号": [1, 2, 3, 4, 5, 6],
        "险种": ["养老保险", "医疗保险", "失业保险", "工伤保险", "生育保险", "住房公积金"],
        "实际缴费人数": [13, 13, 13, 13, 13, 12],
        "签署劳动合同的员工人数": [15, 15, 15, 15, 15, 15],
        "单位缴费基数": ["131300", "131300", "131300", "131300", "131300", "125300"],
        "个人缴费基数": ["131300", "131300", "131300", "—", "—", "125300"],
        "单位缴费比例": ["16%", "9%", "0.8%", "0.2%", "0.8%", "12%"],
        "个人缴费比例": ["8%", "2% + 3", "0.2%", "—", "—", "12%"]
    }
    edited_df = st.data_editor(
        pd.DataFrame(default_data), num_rows="dynamic",
        use_container_width=True, key="input_table"
    )

    run_btn = st.button("🚀 运行 Agent 合规分析", type="primary", use_container_width=True)

    if run_btn:
        for k in ["issues", "reasoning", "input_data", "module_name"]:
            st.session_state.pop(k, None)
        with st.spinner("Agent 正在核查数据并出具法律意见（约 20-40 秒）..."):
            try:
                payload = {
                    "module_name": selected_module,
                    "table_data": edited_df.to_markdown(index=False)
                }
                resp = requests.post(f"{api_base}/api/analyze", json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                st.session_state["issues"]      = data["issues"]
                st.session_state["reasoning"]   = data["analysis_reasoning"]
                st.session_state["input_data"]  = edited_df.to_markdown(index=False)
                st.session_state["module_name"] = selected_module
                st.success("✅ Agent 法律意见已生成，请审阅下方评测表。")
            except requests.exceptions.Timeout:
                st.error("⚠️ 请求超时，请重试。")
            except Exception as e:
                st.error(f"⚠️ 请求失败：{e}")

    # ── 输出区 ────────────────────────────────────────────────
    if "issues" in st.session_state:
        issues    = st.session_state["issues"]
        reasoning = st.session_state["reasoning"]

        st.divider()

        with st.expander("🔍 Agent 逐条核查工作底稿（展开查看）", expanded=False):
            st.markdown(reasoning)

        # ── 评测大表 ──────────────────────────────────────────
        st.markdown(f"### 📋 合规风险事项评测表（共 {len(issues)} 项）")
        st.caption("前四列为 Agent 法律意见输出（只读），后两列请评测人员填写。每条 Issue 均附有针对性的投资人建议。")

        table_rows = []
        for i, iss in enumerate(issues):
            table_rows.append({
                "编号": f"Issue {i+1}",
                "风险定性": iss["title"],
                "事实认定（Agent）": iss["fact"],
                "法律依据（Agent）": iss["law"],
                "投资人建议（Agent）": iss["suggestion"],
                "期待标准答案 ✏️": "",
                "输出问题与改进建议 ✏️": "",
            })

        edited_eval = st.data_editor(
            pd.DataFrame(table_rows),
            column_config={
                "编号": st.column_config.TextColumn(width="small"),
                "风险定性": st.column_config.TextColumn(width="medium"),
                "事实认定（Agent）": st.column_config.TextColumn(width="large"),
                "法律依据（Agent）": st.column_config.TextColumn(width="large"),
                "投资人建议（Agent）": st.column_config.TextColumn(width="large"),
                "期待标准答案 ✏️": st.column_config.TextColumn(width="large", help="填写您认为正确的标准答案"),
                "输出问题与改进建议 ✏️": st.column_config.TextColumn(width="large", help="描述 Agent 输出的问题及改进方向"),
            },
            disabled=["编号", "风险定性", "事实认定（Agent）", "法律依据（Agent）", "投资人建议（Agent）"],
            use_container_width=True,
            height=min(500, 90 + len(table_rows) * 60),
            hide_index=True,
            key="eval_table"
        )

        # ── 提交 ─────────────────────────────────────────────
        st.divider()
        submit_btn = st.button("💾 提交并保存测试记录", type="primary", use_container_width=True)

        if submit_btn:
            evaluations = []
            for _, row in edited_eval.iterrows():
                evaluations.append({
                    "issue_title": row["风险定性"],
                    "expected_answer": str(row["期待标准答案 ✏️"] or ""),
                    "improvement_notes": str(row["输出问题与改进建议 ✏️"] or ""),
                })
            save_payload = {
                "module_name": st.session_state["module_name"],
                "input_data": st.session_state["input_data"],
                "analysis_reasoning": reasoning,
                "issues": issues,
                "evaluations": evaluations,
            }
            try:
                resp = requests.post(f"{api_base}/api/records", json=save_payload, timeout=15)
                resp.raise_for_status()
                result = resp.json()
                st.success(f"✅ 已保存！记录 ID：#{result['record_id']}")
                for k in ["issues", "reasoning", "input_data", "module_name"]:
                    st.session_state.pop(k, None)
            except Exception as e:
                st.error(f"⚠️ 保存失败：{e}")

# ═══════════════════════════════════════════════════════════════
# 页面 2：历史记录
# ═══════════════════════════════════════════════════════════════
else:
    st.title("📂 历史测试记录")
    st.button("🔄 刷新")

    try:
        resp = requests.get(f"{api_base}/api/records", timeout=10)
        resp.raise_for_status()
        records = resp.json()
    except Exception as e:
        st.error(f"无法读取：{e}")
        records = []

    if not records:
        st.info("暂无记录。")
    else:
        summary_df = pd.DataFrame(records)
        summary_df.columns = ["ID", "创建时间", "模块", "Issue 数"]
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.divider()
        selected_id = st.selectbox(
            "选择记录查看详情",
            options=[r["id"] for r in records],
            format_func=lambda x: (
                f"#{x}  ·  "
                + next((r["created_at"] for r in records if r["id"] == x), "")
                + "  ·  "
                + next((r["module_name"] for r in records if r["id"] == x), "")
            )
        )

        if st.button("📖 查看详情"):
            try:
                resp = requests.get(f"{api_base}/api/records/{selected_id}", timeout=10)
                resp.raise_for_status()
                d = resp.json()

                st.subheader(f"记录 #{d['id']} — {d['module_name']} | {d['created_at']}")

                # 原始输入数据
                st.markdown("#### 📊 原始业务数据")
                input_df = markdown_to_df(d["input_data"])
                if not input_df.empty:
                    st.dataframe(input_df, use_container_width=True, hide_index=True)
                else:
                    st.code(d["input_data"])

                with st.expander("🔍 Agent 核查工作底稿", expanded=False):
                    st.markdown(d["analysis_reasoning"])

                st.markdown("#### 📋 合规风险评测明细")
                evals = {e["issue_title"]: e for e in d["evaluations"]}
                rows = []
                for i, iss in enumerate(d["issues"]):
                    ev = evals.get(iss["title"], {})
                    rows.append({
                        "编号": f"Issue {i+1}",
                        "风险定性": iss["title"],
                        "事实认定": iss["fact"],
                        "法律依据": iss["law"],
                        "投资人建议": iss["suggestion"],
                        "期待标准答案": ev.get("expected_answer", ""),
                        "改进建议": ev.get("improvement_notes", ""),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"读取失败：{e}")
