# ==============================================================================
# BNI Mobile Application Structure (Profile-Integrated Flow)
# ==============================================================================

import json
import os
import httpx
import pandas as pd
import streamlit as st
from openai import OpenAI

# 1. Page Configuration & Custom CSS
st.set_page_config(
    page_title="BNI 人脈掘金",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0A192F;
        color: #E6F1FF;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        padding-bottom: 90px !important;
    }
    header[data-testid="stHeader"] { visibility: hidden; height: 0px; }
    footer { visibility: hidden; }
    
    .bottom-nav {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        height: 65px;
        background-color: #112240;
        border-top: 1px solid #233554;
        display: flex;
        justify-content: space-around;
        align-items: center;
        z-index: 999999;
    }
    .nav-item {
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        color: #8892B0; text-decoration: none;
        font-size: 0.75rem; font-weight: 500; width: 33%;
    }
    .nav-item.active { color: #64FFDA; }
    
    .app-header {
        color: #64FFDA; font-weight: 700; font-size: 1.6rem;
        border-bottom: 1px solid #233554; padding-bottom: 12px; margin-bottom: 20px;
        display: flex; align-items: center; gap: 10px;
    }
    .notification-card {
        background-color: #112240; border-left: 4px solid #64FFDA;
        border-radius: 12px; padding: 16px; margin-bottom: 16px;
        border-top: 1px solid #233554; border-right: 1px solid #233554; border-bottom: 1px solid #233554;
    }
    .notification-title { color: #E6F1FF; font-size: 1.1rem; font-weight: 600; margin-bottom: 6px; }
    .notification-subtitle { color: #8892B0; font-size: 0.85rem; margin-bottom: 10px; }
    .notification-body { background-color: #172A45; border-radius: 8px; padding: 10px; color: #CCD6F6; font-size: 0.9rem; margin-bottom: 10px; }

    .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
        background-color: #172A45 !important; color: #E6F1FF !important;
        border: 1px solid #233554 !important; border-radius: 12px !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label { color: #E6F1FF !important; font-size: 0.9rem !important; }
    .stButton>button { background-color: #64FFDA; color: #0A192F; border-radius: 12px; border: none; font-weight: 700; width: 100%; padding: 12px; }
    .bi-icon { display: inline-block; vertical-align: -0.125em; fill: currentColor; }
    </style>
""",
    unsafe_allow_html=True,
)

# 2. Load Data
@st.cache_data(show_spinner=False)
def load_bni_data():
    csv_file = "bni_data.csv"
    if not os.path.exists(csv_file):
        return None
    try:
        df = pd.read_csv(csv_file)
        mapping = {}
        for col in df.columns:
            clow = str(col).lower().strip()
            if "name" in clow or "姓名" in clow: mapping[col] = "Name"
            elif "chapter" in clow or "分會" in clow: mapping[col] = "Chapter"
            elif "industry" in clow or "行業" in clow: mapping[col] = "Industry"
        return df.rename(columns=mapping)
    except Exception:
        return None

# 3. Session State Initialization
if "active_tab" not in st.session_state: st.session_state.active_tab = "Search"
if "latest_results" not in st.session_state: st.session_state.latest_results = []
if "deepseek_api_key" not in st.session_state: st.session_state.deepseek_api_key = ""
if "endpoint_option" not in st.session_state: st.session_state.endpoint_option = "官方直連 (api.deepseek.com)"

# User Profile Default Placeholders (No Real Names)
if "my_name" not in st.session_state: st.session_state.my_name = "[會員姓名]"
if "my_chapter" not in st.session_state: st.session_state.my_chapter = "[所屬分會]"
if "my_industry" not in st.session_state: st.session_state.my_industry = "[專業領域]"
if "my_strengths" not in st.session_state: st.session_state.my_strengths = "[請在 Profile 頁面設定您的業務核心與優勢亮點]"

params = st.query_params
if "tab" in params:
    st.session_state.active_tab = params["tab"]

def clean_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"): cleaned = cleaned[7:]
    elif cleaned.startswith("```"): cleaned = cleaned[3:]
    if cleaned.endswith("```"): cleaned = cleaned[:-3]
    return cleaned.strip()

def query_deepseek(api_key, dataset_text, req_prompt, endpoint_choice):
    sys_prompt = (
        "你是一個 BNI 人脈精準匹配專家。"
        "請根據會員資料庫與使用者需求篩選最匹配的會員。"
        "必須且只能回傳合法的純 JSON 格式："
        '{"results": [{"name": "姓名", "chapter": "分會", "industry": "行業", "reason": "配對理由", "whatsapp_message": "破冰話術"}]}'
    )
    bases = ["[https://api.deepseek.com/v1](https://api.deepseek.com/v1)"]
    if "海外加速通道 1" in endpoint_choice: bases = ["[https://api.chatanywhere.tech/v1](https://api.chatanywhere.tech/v1)"]
    elif "海外加速通道 2" in endpoint_choice: bases = ["[https://api.openai-proxy.org/deepseek/v1](https://api.openai-proxy.org/deepseek/v1)"]

    last_err = None
    for url in bases:
        client_http = httpx.Client(http2=False, timeout=httpx.Timeout(90.0, connect=25.0))
        try:
            client = OpenAI(api_key=api_key.strip(), base_url=url, http_client=client_http, max_retries=1)
            res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"【數據庫】\n{dataset_text}\n\n【需求】\n{req_prompt}"}],
                temperature=0.1, response_format={"type": "json_object"}
            )
            return res.choices[0].message.content
        except Exception as e: last_err = e
        finally: client_http.close()
    if last_err: raise last_err

# ==============================================================================
# TAB 1: HOME
# ==============================================================================
if st.session_state.active_tab == "Home":
    st.markdown('<div class="app-header">最新人脈通知</div>', unsafe_allow_html=True)
    results = st.session_state.latest_results

    if not results:
        st.markdown(
            f"""
            <div class="notification-card">
                <div class="notification-title">#1 {st.session_state.my_name} (預設 Profile 展示範例)</div>
                <div class="notification-subtitle">📍 分會: {st.session_state.my_chapter} | 💼 行業: {st.session_state.my_industry}</div>
                <div class="notification-body"><b>業務亮點:</b> {st.session_state.my_strengths}</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.caption("破冰話術草稿：")
        st.code(f"Hello, 我係 BNI {st.session_state.my_chapter} 分會嘅 {st.session_state.my_name}，從事{st.session_state.my_industry}。想跟你進行一次 1-on-1 交流！", language="text")
    else:
        for idx, item in enumerate(results, 1):
            st.markdown(
                f"""
                <div class="notification-card">
                    <div class="notification-title">#{idx} {item.get('name', 'N/A')}</div>
                    <div class="notification-subtitle">📍 分會: {item.get('chapter', 'N/A')} | 💼 行業: {item.get('industry', 'N/A')}</div>
                    <div class="notification-body"><b>匹配理由:</b> {item.get('reason', 'N/A')}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )
            st.caption("破冰話術草稿：")
            st.code(item.get("whatsapp_message", ""), language="text")

# ==============================================================================
# TAB 2: SEARCH (PRE-FILLED PROFILE DATA + GENERATE)
# ==============================================================================
elif st.session_state.active_tab == "Search":
    st.markdown('<div class="app-header">精準人脈搜尋</div>', unsafe_allow_html=True)

    st.markdown("**1. 我的 Profile 預設資料：**")
    col1, col2 = st.columns(2)
    with col1:
        s_name = st.text_input("會員姓名", value=st.session_state.my_name)
        s_chapter = st.text_input("所屬分會", value=st.session_state.my_chapter)
    with col2:
        s_industry = st.text_input("登記專業領域", value=st.session_state.my_industry)
        s_count = st.selectbox("匹配人數", options=[1, 2, 3, 5], index=2)

    s_strengths = st.text_area("業務核心 / 合作優勢", value=st.session_state.my_strengths, height=80)

    st.markdown("**2. 目標合作需求：**")
    target_goal = st.text_area("你想找什麼行業或合作機會？", placeholder="例如：尋找 3 位餐飲或食品相關會員，洽談聯名禮盒合作...", height=80)

    if st.button("🚀 Generate (執行配對)"):
        key = st.session_state.get("deepseek_api_key", "").strip()
        if not key:
            st.error("請先至 【Profile】 頁面設定您的 DeepSeek API Key。")
        else:
            df_bni = load_bni_data()
            if df_bni is None or df_bni.empty:
                st.error("找不到 bni_data.csv 或資料庫為空。")
            else:
                formatted_req = (
                    f"搜尋發起人: {s_name} ({s_chapter}分會, {s_industry})\n"
                    f"發起人核心優勢: {s_strengths}\n"
                    f"希望匹配人數: {s_count}\n"
                    f"目標尋找需求: {target_goal if target_goal else '不限，尋找最適合的合作夥伴'}"
                )
                with st.spinner("AI 精準分析匹配中..."):
                    try:
                        raw = query_deepseek(key, df_bni.to_string(index=False), formatted_req, st.session_state.endpoint_option)
                        parsed = json.loads(clean_json(raw))
                        st.session_state.latest_results = parsed.get("results", [])
                        st.success("匹配完成！已將結果更新至 Home 通知盒。")
                        st.query_params["tab"] = "Home"
                        st.rerun()
                    except Exception as e:
                        st.error(f"搜尋執行失敗: {e}")

# ==============================================================================
# TAB 3: PROFILE (DEFAULT DATA SETTINGS)
# ==============================================================================
elif st.session_state.active_tab == "Profile":
    st.markdown('<div class="app-header">個人 Profile 與系統設定</div>', unsafe_allow_html=True)

    st.markdown("**我的預設個人資料：**")
    st.session_state.my_name = st.text_input("會員姓名", value=st.session_state.my_name)
    st.session_state.my_chapter = st.text_input("所屬分會", value=st.session_state.my_chapter)
    st.session_state.my_industry = st.text_input("登記專業領域", value=st.session_state.my_industry)
    st.session_state.my_strengths = st.text_area("業務核心 / 優勢亮點", value=st.session_state.my_strengths, height=90)

    st.markdown("---")
    st.markdown("**API 設定：**")
    st.session_state.deepseek_api_key = st.text_input("DeepSeek API Key", value=st.session_state.deepseek_api_key, type="password")
    st.session_state.endpoint_option = st.selectbox("連線節點選擇", options=["官方直連 (api.deepseek.com)", "海外加速通道 1 (api.chatanywhere.tech)", "海外加速通道 2 (api.openai-proxy.org/deepseek)"])

    st.info("Profile 資料會自動備份，並直接連動至 Search 頁面與 Home 範例！")

# ==============================================================================
# NAVIGATION BAR
# ==============================================================================
h_active = "active" if st.session_state.active_tab == "Home" else ""
s_active = "active" if st.session_state.active_tab == "Search" else ""
p_active = "active" if st.session_state.active_tab == "Profile" else ""

st.markdown(
    f"""
    <div class="bottom-nav">
        <a href="?tab=Home" target="_self" class="nav-item {h_active}">Home</a>
        <a href="?tab=Search" target="_self" class="nav-item {s_active}">Search</a>
        <a href="?tab=Profile" target="_self" class="nav-item {p_active}">Profile</a>
    </div>
""",
    unsafe_allow_html=True,
)
