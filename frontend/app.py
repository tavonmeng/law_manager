import os
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
    
    /* 自定义卡片样式 */
    .issue-card {
        background-color: #1e2638;
        border-left: 4px solid #f43f5e; /* 玫瑰红提示风险 */
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .issue-title {
        color: #fff;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .issue-label {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.8rem;
        margin-bottom: 0.2rem;
    }
    .issue-content {
        color: #e2e8f0;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
        line-height: 1.6;
    }
    .advise-box {
        background-color: rgba(59, 130, 246, 0.1); 
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 6px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .db-record-card {
        background-color: #1f2937;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #374151;
    }
</style>
""", unsafe_allow_html=True)

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


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
    page = st.radio("导航菜单", ["🧪 新建评测任务", "📂 历史评测记录"], label_visibility="collapsed")
    st.divider()
    
    st.markdown("**配置项**")
    module_options = ["五险一金", "劳动合同", "劳动纠纷", "劳务派遣"]
    selected_module = st.selectbox("当前分析模块", module_options)
    api_base = st.text_input("后端 API 地址", value=BASE_URL)

# ═══════════════════════════════════════════════════════════════
# 页面 1：新建测试
# ═══════════════════════════════════════════════════════════════
if "新建" in page:
    st.title("🧪 新建合规尽调任务")
    st.markdown("输入目标公司业务数据 → 运行 Agent 推理 → 检阅法律意见卡片 → 输入人工评测改进意见。")
    st.divider()

    # ── 数据输入区 ──
    st.markdown("##### 📊 目标公司业务数据（支持混合输入）")
    
    st.caption("1. 基础数据表格（可动态增减行列、直接编辑内容）")
    default_data = {
        "序号": [1, 2, 3, 4, 5, 6],
        "险种": ["养老保险", "医疗保险", "失业保险", "工伤保险", "生育保险", "住房公积金"],
        "实际缴费人数": [13, 13, 13, 13, 13, 12],
        "签署劳动合同员工数": [15, 15, 15, 15, 15, 15],
        "单位缴费基数": ["131300", "131300", "131300", "131300", "131300", "125300"],
        "个人缴费基数": ["131300", "131300", "131300", "—", "—", "125300"],
        "单位缴费比例": ["16%", "9%", "0.8%", "0.2%", "0.8%", "12%"],
        "个人缴费比例": ["8%", "2% + 3", "0.2%", "—", "—", "12%"]
    }
    edited_df = st.data_editor(
        pd.DataFrame(default_data), num_rows="dynamic",
        use_container_width=True, key="input_table",
        height=280
    )

    st.caption("2. 补充说明材料（选填，其它相关的文字描述、额外表格等，支持 Markdown 格式）")
    extra_context = st.text_area("补充材料文本框", label_visibility="collapsed", height=150, placeholder="由于Agent无法凭空核实一些前提条件，您可以将相关的补充性说明、额外的文字描述或访谈纪要粘贴到这里...")

    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 运行 Agent 开始合规分析", type="primary", use_container_width=True)

    if run_btn:
        for k in ["issues", "reasoning", "input_data", "module_name"]:
            st.session_state.pop(k, None)
        with st.spinner("Agent 正在充当尽调律师核查数据，并出具法律意见... (约20~30秒)"):
            try:
                # 拼接数据与文本
                combined_data = "【基础数据表格】\n\n" + edited_df.to_markdown(index=False)
                if extra_context.strip():
                    combined_data += "\n\n\n【补充说明材料】\n\n" + extra_context.strip()

                payload = {
                    "module_name": selected_module,
                    "table_data": combined_data
                }
                resp = requests.post(f"{api_base}/api/analyze", json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                st.session_state["issues"]      = data["issues"]
                st.session_state["reasoning"]   = data["analysis_reasoning"]
                st.session_state["input_data"]  = combined_data
                st.session_state["module_name"] = selected_module
                st.success("✅ Agent 法律意见已生成，请在下方滚动查看并评测。")
            except Exception as e:
                st.error(f"⚠️ 请求失败：{e}")

    # ── 输出区 ──
    if "issues" in st.session_state:
        issues    = st.session_state["issues"]
        reasoning = st.session_state["reasoning"]

        st.divider()
        st.markdown(f"### 📋 合规分析报告及人工评测评 (共发现 {len(issues)} 项 Issue)")
        
        with st.expander("🔍 查看 Agent 逐条核查工作底稿 (推理思维链)", expanded=False):
            st.markdown(reasoning)

        # 遍历展示结构化卡片与评测输入
        evaluations_dict = {}
        
        for i, iss in enumerate(issues):
            st.markdown(f"""
            <div class="issue-card">
                <div class="issue-title">🔴 风险项 #{i+1}：{iss['title']}</div>
                
                <div class="issue-label">事实认定</div>
                <div class="issue-content">{iss['fact']}</div>
                
                <div class="issue-label">法律依据</div>
                <div class="issue-content">{iss['law']}</div>
                
                <div class="advise-box">
                    <div class="issue-label" style="margin-top: 0; color: #60a5fa;">投资人风险评估与建议</div>
                    <div class="issue-content" style="margin-bottom: 0; color: #bfdbfe;">
                        {iss['suggestion'].replace(chr(10), '<br>')}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- 下方放对应的人工评测表单 ---
            with st.container():
                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    exp_val = st.text_area("期待标准答案 ✏️", key=f"exp_{i}", 
                                         placeholder="您认为更专业的法律意见该怎么写？", height=100)
                with ecol2:
                    imp_val = st.text_area("问题指出与改进建议 ✏️", key=f"imp_{i}", 
                                         placeholder="Agent 的输出存在什么瑕疵？提示词需要如何优化？", height=100)
                
                evaluations_dict[iss["title"]] = {
                    "expected": exp_val,
                    "improve": imp_val
                }
            st.markdown("<br>", unsafe_allow_html=True)

        # ── 提交按钮 ──
        st.divider()
        submit_btn = st.button("💾 将此次测试与评测意见保存入库", type="primary", use_container_width=True)

        if submit_btn:
            eval_list = []
            for issue_title, ev in evaluations_dict.items():
                eval_list.append({
                    "issue_title": issue_title,
                    "expected_answer": ev["expected"],
                    "improvement_notes": ev["improve"],
                })
            
            save_payload = {
                "module_name": st.session_state["module_name"],
                "input_data": st.session_state["input_data"],
                "analysis_reasoning": reasoning,
                "issues": issues,
                "evaluations": eval_list,
            }
            try:
                resp = requests.post(f"{api_base}/api/records", json=save_payload, timeout=15)
                resp.raise_for_status()
                res = resp.json()
                st.success(f"✅ 保存成功！记录 ID：#{res['record_id']}，请前往「历史评测记录」页面查看。")
                for k in ["issues", "reasoning", "input_data", "module_name"]:
                    st.session_state.pop(k, None)
            except Exception as e:
                st.error(f"⚠️ 保存失败：{e}")

# ═══════════════════════════════════════════════════════════════
# 页面 2：历史记录
# ═══════════════════════════════════════════════════════════════
else:
    st.title("📂 历史评测记录库")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()

    try:
        resp = requests.get(f"{api_base}/api/records", timeout=10)
        resp.raise_for_status()
        records = resp.json()
    except Exception as e:
        st.error(f"无法读取后端数据：{e}")
        records = []

    if not records:
        st.info("暂无历史记录，请先运行任务并保存。")
    else:
        # 左侧列表，右侧详情的布局
        list_col, detail_col = st.columns([2, 5])
        
        with list_col:
            st.markdown("##### 记录列表")
            selected_id = st.radio(
                "请选择一条记录",
                options=[r["id"] for r in records],
                format_func=lambda x: next((f"#{x} · {r['module_name']} (Issue: {r['issue_count']})" for r in records if r["id"] == x), "")
            )
            
        with detail_col:
            if selected_id:
                try:
                    res = requests.get(f"{api_base}/api/records/{selected_id}", timeout=10)
                    res.raise_for_status()
                    d = res.json()
                    
                    st.markdown(f"### 📋 评测记录 #{d['id']} 详情")
                    st.caption(f"分析模块：**{d['module_name']}** | 创建时间：{d['created_at']}")
                    
                    tab1, tab2, tab3 = st.tabs(["📊 原始业务数据", "🔍 尽调核查底稿", "⚖️ 法律意见与评测档案"])
                    
                    with tab1:
                        # 使用 st.markdown 直接渲染完整的输入数据内容（支持表格和文本混排展示）
                        st.markdown(d["input_data"])
                            
                    with tab2:
                        st.markdown("<div class='db-record-card'>" + d["analysis_reasoning"].replace('\n', '<br>') + "</div>", unsafe_allow_html=True)
                        
                    with tab3:
                        evals_map = {e["issue_title"]: e for e in d["evaluations"]}
                        for i, iss in enumerate(d["issues"]):
                            ev = evals_map.get(iss["title"], {})
                            st.markdown(f"""
                            <div class="issue-card" style="margin-bottom: 5px;">
                                <div class="issue-title" style="font-size:1.1rem;">🔴 {iss['title']}</div>
                                <div class="issue-label">事实认定</div>
                                <div class="issue-content">{iss['fact']}</div>
                                <div class="issue-label">法律依据</div>
                                <div class="issue-content">{iss['law']}</div>
                                <div class="advise-box" style="padding: 0.8rem;">
                                    <div class="issue-label" style="margin-top:0;">风险评估与投资人建议</div>
                                    <div class="issue-content" style="margin-bottom:0;">{iss['suggestion'].replace(chr(10), '<br>')}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.info(f"**期望答案:** {ev.get('expected_answer', '无')}\n\n**改进建议:** {ev.get('improvement_notes', '无')}")
                            st.markdown("<hr style='margin: 1rem 0; opacity: 0.2'>", unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"读取详情失败：{e}")
