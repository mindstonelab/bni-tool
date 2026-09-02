# ==============================================================================
# BNI Mobile Application Structure (Professional Flat Design)
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
    /* Global Page Styling */
    .stApp {
        background-color: #0B132B;
        color: #E0E6ED;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        padding-bottom: 90px !important;
    }
    header[data-testid="stHeader"] { visibility: hidden; height: 0px; }
    footer { visibility: hidden; }

    /* Typography & Headers */
    .app-header {
        color: #C9A96E;
        font-weight: 700;
        font-size: 1.5rem;
        border-bottom: 1px solid #1C2541;
        padding-bottom: 12px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Fixed Bottom Navigation Bar (No Underlines) */
    .bottom-nav {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        height: 65px;
        background-color: #1C2541;
        border-top: 1px solid #2A385B;
        display: flex;
        justify-content: space-around;
        align-items: center;
        z-index: 999999;
    }
    .nav-item {
        display: flex; 
        flex-direction: column;
        align-items: center; 
        justify-content: center;
        color: #8D99AE; 
        text-decoration: none !important;
        font-size: 0.75rem; 
        font-weight: 500; 
        width: 33%;
    }
    .nav-item:hover, .nav-item:focus, .nav-item:visited {
        text-decoration: none !important;
    }
    .nav-item.active { 
        color: #C9A96E; 
    }

    /* Notification Cards */
    .notification-card {
        background-color: #1C2541;
        border-left: 4px solid #C9A96E;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border-top: 1px solid #2A385B;
        border-right: 1px solid #2A385B;
        border-bottom: 1px solid #2A385B;
    }
    .notification-title { color: #FFFFFF; font-size: 1.05rem; font-weight: 600; margin-bottom: 6px; }
    .notification-subtitle { color: #8D99AE; font-size: 0.85rem; margin-bottom: 10px; }
    .notification-body { background-color: #0B132B; border-radius: 8px; padding: 12px; color: #E0E6ED; font-size: 0.9rem; margin-bottom: 10px; }

    /* Form Fields & Placeholders */
    .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
        background-color: #1C2541 !important; 
        color: #FFFFFF !important;
        border: 1px solid #2A385B !important; 
        border-radius: 10px !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #7289DA !important;
        opacity: 1 !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label { 
        color: #E0E6ED !important; 
        font-size: 0.9rem !important; 
        font-weight: 500 !important;
    }

    /* Professional Action Button */
    .stButton>button { 
        background-color: #C9A96E; 
        color: #0B132B; 
        border-radius: 10px; 
        border: none; 
        font-weight: 700; 
        width: 100%; 
        padding: 12px; 
        font-size: 0.95rem;
        transition: background-color 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #B59357;
        color: #0B132B;
    }

    /* Bootstrap Icon Helper */
    .bi-icon { display: inline-block; vertical-align: -0.125em; fill: currentColor; }
    </style>
""",
    unsafe_allow_html=True,
)

# 2. Data Loader
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

# User Profile Placeholders
if "my_name" not in st.session_state: st.session_state.my_name = ""
if "my_chapter" not in st.session_state: st.session_state.my_chapter = ""
if "my_industry" not in st.session_state: st.session_state.my_industry = ""
if "my_strengths" not in st.session_state: st.session_state.my_strengths = ""

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
    st.markdown(
        """
        <div class="app-header">
            <svg class="bi-icon" width="20" height="20" viewBox="0 0 16 16"><path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2zM8 1.918l-.797.161A4.002 4.002 0 0 0 4 6c0 .628-.134 2.197-.459 3.742-.16.767-.376 1.566-.663 2.258h10.244c-.287-.692-.502-1.49-.663-2.258C12.134 8.197 12 6.628 12 6a4.002 4.002 0 0 0-3.203-3.92L8 1.917z"/></svg>
            最新人脈通知
        </div>
    """,
        unsafe_allow_html=True,
    )
    
    results = st.session_state.latest_results

    if not results:
        # User Profile State Sample
        display_name = st.session_state.my_name if st.session_state.my_name else "[會員姓名]"
        display_chapter = st.session_state.my_chapter if st.session_state.my_chapter else "[所屬分會]"
        display_industry = st.session_state.my_industry if st.session_state.my_industry else "[專業領域]"
        display_strengths = st.session_state.my_strengths if st.session_state.my_strengths else "[請在 Profile 頁面設定您的業務核心與優勢]"

        st.markdown(
            f"""
            <div class="notification-card">
                <div class="notification-title">#1 {display_name} (預設 Profile 展示範例)</div>
                <div class="notification-subtitle">分會: {display_chapter} | 行業: {display_industry}</div>
                <div class="notification-body"><b>核心優勢:</b> {display_strengths}</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # Database Result Sample
        st.markdown(
            """
            <div class="notification-card">
                <div class="notification-title">#1 Michelle Chu</div>
                <div class="notification-subtitle">分會: Venture | 行業: 會計服務</div>
                <div class="notification-body">
                    <b>匹配理由:</b> 同行人數統計：該會員具備相同/相近專業的會計經驗，專注中小企外判理帳與稅務審查。
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.caption("破冰話術草稿：")
        st.code("Hello Michelle, 我是 BNI 會員，看到您在 Venture 分會從事會計服務，希望進行一次 1-on-1 交流！", language="text")
    else:
        for idx, item in enumerate(results, 1):
            st.markdown(
                f"""
                <div class="notification-card">
                    <div class="notification-title">#{idx} {item.get('name', 'N/A')}</div>
                    <div class="notification-subtitle">分會: {item.get('chapter', 'N/A')} | 行業: {item.get('industry', 'N/A')}</div>
                    <div class="notification-body"><b>匹配理由:</b> {item.get('reason', 'N/A')}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )
            st.caption("破冰話術草稿：")
            st.code(item.get("whatsapp_message", ""), language="text")

# ==============================================================================
# TAB 2: SEARCH
# ==============================================================================
elif st.session_state.active_tab == "Search":
    st.markdown(
        """
        <div class="app-header">
            <svg class="bi-icon" width="20" height="20" viewBox="0 0 16 16"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg>
            精準人脈搜尋
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("**1. 我的 Profile 預設資料：**")
    col1, col2 = st.columns(2)
    with col1:
        s_name = st.text_input("會員姓名", value=st.session_state.my_name, placeholder="[請輸入姓名]")
        s_chapter = st.text_input("所屬分會", value=st.session_state.my_chapter, placeholder="[請輸入分會]")
    with col2:
        s_industry = st.text_input("登記專業領域", value=st.session_state.my_industry, placeholder="[請輸入專業領域]")
        s_count = st.selectbox("匹配人數", options=[1, 2, 3, 5], index=2)

    s_strengths = st.text_area("業務核心與優勢", value=st.session_state.my_strengths, placeholder="[請輸入業務核心內容]", height=80)

    st.markdown("**2. 目標合作需求：**")
    target_goal = st.text_area("目標對接需求", placeholder="例如：尋找 3 位餐飲相關會員洽談合作...", height=80)

    if st.button("執行精準配對"):
        key = st.session_state.get("deepseek_api_key", "").strip()
        if not key:
            st.error("請先至 【Profile】 頁面設定您的 DeepSeek API Key。")
        else:
            df_bni = load_bni_data()
            if df_bni is None or df_bni.empty:
                st.error("找不到 bni_data.csv 或資料庫內容為空。")
            else:
                formatted_req = (
                    f"搜尋發起人: {s_name} ({s_chapter}分會, {s_industry})\n"
                    f"發起人核心優勢: {s_strengths}\n"
                    f"希望匹配人數: {s_count}\n"
                    f"目標尋找需求: {target_goal if target_goal else '不限，尋找最適合的合作夥伴'}"
                )
                with st.spinner("分析匹配中..."):
                    try:
                        raw = query_deepseek(key, df_bni.to_string(index=False), formatted_req, st.session_state.endpoint_option)
                        parsed = json.loads(clean_json(raw))
                        st.session_state.latest_results = parsed.get("results", [])
                        st.success("匹配完成，已更新至 Home 通知。")
                        st.query_params["tab"] = "Home"
                        st.rerun()
                    except Exception as e:
                        st.error(f"配對失敗: {e}")

# ==============================================================================
# TAB 3: PROFILE
# ==============================================================================
elif st.session_state.active_tab == "Profile":
    st.markdown(
        """
        <div class="app-header">
            <svg class="bi-icon" width="20" height="20" viewBox="0 0 16 16"><path d="M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"/><path d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2zm12 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1v-1c0-1-1-4-6-4s-6 3-6 4v1a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12z"/></svg>
            個人 Profile 與系統設定
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("**我的預設個人資料：**")
    st.session_state.my_name = st.text_input("會員姓名", value=st.session_state.my_name, placeholder="[請輸入姓名]")
    st.session_state.my_chapter = st.text_input("所屬分會", value=st.session_state.my_chapter, placeholder="[請輸入分會]")
    st.session_state.my_industry = st.text_input("登記專業領域", value=st.session_state.my_industry, placeholder="[請輸入專業領域]")
    st.session_state.my_strengths = st.text_area("業務核心與優勢", value=st.session_state.my_strengths, placeholder="[請輸入業務核心內容]", height=90)

    st.markdown("---")
    st.markdown("**API 設定：**")
    st.session_state.deepseek_api_key = st.text_input("DeepSeek API Key", value=st.session_state.deepseek_api_key, type="password", placeholder="sk-...")
    st.session_state.endpoint_option = st.selectbox("連線節點選擇", options=["官方直連 (api.deepseek.com)", "海外加速通道 1 (api.chatanywhere.tech)", "海外加速通道 2 (api.openai-proxy.org/deepseek)"])

    st.info("Profile 資料將自動備份並連動至 Search 頁面。")

# ==============================================================================
# FIXED BOTTOM NAVIGATION BAR
# ==============================================================================
h_active = "active" if st.session_state.active_tab == "Home" else ""
s_active = "active" if st.session_state.active_tab == "Search" else ""
p_active = "active" if st.session_state.active_tab == "Profile" else ""

st.markdown(
    f"""
    <div class="bottom-nav">
        <a href="?tab=Home" target="_self" class="nav-item {h_active}">
            <svg class="bi-icon" width="18" height="18" viewBox="0 0 16 16"><path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293L8.707 1.5Z"/></path></svg>
            Home
        </a>
        <a href="?tab=Search" target="_self" class="nav-item {s_active}">
            <svg class="bi-icon" width="18" height="18" viewBox="0 0 16 18"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></path></svg>
            Search
        </a>
        <a href="?tab=Profile" target="_self" class="nav-item {p_active}">
            <svg class="bi-icon" width="18" height="18" viewBox="0 0 16 16"><path d="M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"/><path d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"/></path></svg>
            Profile
        </a>
    </div>
""",
    unsafe_allow_html=True,
)
