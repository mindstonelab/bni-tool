# ==============================================================================
# 部署須知：
# 1. 部署前須將含有會員資料的 CSV 檔案更名為 "bni_data.csv"，並放置於與本程式 (app.py) 相同的目錄下。
# 2. 依賴套件 (requirements.txt)：streamlit, pandas, openai, httpx
# ==============================================================================

import json
import os
import httpx
import pandas as pd
import streamlit as st
from openai import APIConnectionError, APIStatusError, OpenAI

# 1. 頁面配置與配色設定（Flat Navy Theme & Rounded Corners）
st.set_page_config(
    page_title="BNI 人脈掘金",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Global Page Background & Fonts */
    .stApp {
        background-color: #0A192F;
        color: #E6F1FF;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #112240;
        border-right: 1px solid #1E2D4A;
    }
    
    /* Headers & Text */
    .main-header {
        color: #64FFDA;
        font-weight: 700;
        font-size: 2.2rem;
        letter-spacing: -0.5px;
        border-bottom: 2px solid #1E2D4A;
        padding-bottom: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .section-title {
        color: #64FFDA;
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 24px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Fix Field Label Contrast */
    .stTextArea label, .stTextInput label, .stSelectbox label {
        color: #E6F1FF !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
    }

    /* Flat Member Cards */
    .member-card {
        background-color: #112240;
        border: 1px solid #233554;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: none;
    }
    .card-title {
        color: #CCD6F6;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .card-meta {
        color: #8892B0;
        font-size: 0.95rem;
        margin-bottom: 14px;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .card-meta span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .card-reason {
        color: #8892B0;
        background-color: #172A45;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 14px;
    }
    
    /* Inputs, Buttons, & Code Blocks */
    .stTextArea textarea, .stTextInput input, .stSelectbox > div > div {
        background-color: #172A45 !important;
        color: #E6F1FF !important;
        border: 1px solid #233554 !important;
        border-radius: 12px !important;
    }
    .stTextArea textarea::placeholder {
        color: #8892B0 !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #64FFDA !important;
        box-shadow: none !important;
    }
    .stButton>button {
        background-color: #64FFDA;
        color: #0A192F;
        border-radius: 12px;
        border: none;
        font-weight: 600;
        font-size: 1rem;
        padding: 10px 24px;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #4CD9B3;
        color: #0A192F;
        border: none;
    }
    code {
        border-radius: 8px !important;
        background-color: #172A45 !important;
        color: #64FFDA !important;
    }
    
    /* Bootstrap SVG Icon Helper Alignment */
    .bi-icon {
        display: inline-block;
        vertical-align: -0.125em;
        fill: currentColor;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. 數據讀取（自動對應欄位，絕不提供下載或顯示原始 CSV 資料）
@st.cache_data(show_spinner=False)
def load_bni_data():
    csv_file = "bni_data.csv"
    if not os.path.exists(csv_file):
        return None
    try:
        df = pd.read_csv(csv_file)
        column_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if "name" in col_lower or "姓名" in col_lower:
                column_mapping[col] = "Name"
            elif "chapter" in col_lower or "分會" in col_lower:
                column_mapping[col] = "Chapter"
            elif (
                "industry" in col_lower
                or "行業" in col_lower
                or "profession" in col_lower
            ):
                column_mapping[col] = "Industry"
            elif (
                "green" in col_lower
                or "rank" in col_lower
                or "綠燈" in col_lower
                or "表現" in col_lower
            ):
                column_mapping[col] = "GreenLight Rank"

        df = df.rename(columns=column_mapping)
        return df
    except Exception:
        return None


# 3. 側邊欄：DeepSeek API Key 與端點設定
with st.sidebar:
    st.markdown(
        """
        <div style="color: #64FFDA; font-size: 1.2rem; font-weight: 600; margin-bottom: 16px;">
            <svg class="bi-icon" width="20" height="20" viewBox="0 0 16 16"><path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/><path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319z"/></svg>
            系統設定
        </div>
    """,
        unsafe_allow_html=True,
    )

    if "deepseek_api_key" not in st.session_state:
        st.session_state.deepseek_api_key = ""

    api_key_input = st.text_input(
        "請輸入 DeepSeek API Key",
        value=st.session_state.deepseek_api_key,
        type="password",
        help="金鑰僅會暫存於您的瀏覽器階段 (Session)，重新整理後自動維持。",
    )

    if api_key_input:
        st.session_state.deepseek_api_key = api_key_input.strip()

    endpoint_option = st.selectbox(
        "連線節點選擇",
        options=[
            "官方直連 (api.deepseek.com)",
            "海外加速通道 1 (api.chatanywhere.tech)",
            "海外加速通道 2 (api.openai-proxy.org/deepseek)",
            "自訂 Base URL",
        ],
        index=0,
        help="若使用 Streamlit Cloud 出現 Connection Error，請切換為【海外加速通道】（同樣使用你的 DeepSeek Key）。",
    )

    custom_url = ""
    if endpoint_option == "自訂 Base URL":
        custom_url = st.text_input(
            "輸入自訂 Base URL",
            value="https://api.deepseek.com/v1",
            placeholder="https://your-proxy-domain/v1",
        )

    st.markdown("---")
    st.markdown(
        """
    **使用說明：**
    1. 輸入有效的 DeepSeek 官方 API Key (`sk-...`)。
    2. 若 Streamlit Cloud 提示連線超時，請在上方切換為 **海外加速通道**。
    3. 在主畫面輸入引薦需求，點擊「搜尋人脈」。
    """
    )

# 4. 主畫面邏輯
st.markdown(
    """
    <h1 class="main-header">
        <svg class="bi-icon" width="32" height="32" viewBox="0 0 16 16"><path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1H7Zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-5.784 6A2.238 2.238 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.325 6.325 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1h4.216ZM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"/></svg>
        BNI 人脈掘金系統
    </h1>
""",
    unsafe_allow_html=True,
)

user_prompt = st.text_area(
    "請輸入您的搜尋需求（例如：尋找 3 位餐飲或食品相關會員，想洽談聯名禮盒合作）：",
    value="",
    height=130,
    placeholder="在此輸入您的人脈對接需求...",
)

search_button = st.button("搜尋人脈", use_container_width=True)


# 5. API 呼叫與解析函數
def clean_json_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def query_deepseek(
    api_key: str,
    dataset_text: str,
    requirement: str,
    endpoint_choice: str,
    custom_base: str,
):
    system_instruction = (
        "你是一個 BNI 人脈精準匹配專家。"
        "請仔細閱讀提供的 BNI 會員資料庫，並根據使用者的需求篩選出最匹配的會員。"
        "你必須且只能回傳合法的純 JSON 格式，嚴禁輸出任何 markdown 標籤或額外文字。"
        'JSON 格式標準如下：{ "results": [ { "name": "姓名", "chapter": "分會", "industry": "行業", "reason": "配對理由", "whatsapp_message": "破冰話術" } ] }。'
        '如果資料庫中找不到匹配的會員，請回傳：{ "results": [] }。'
    )

    prompt = (
        f"【BNI 會員數據庫】\n{dataset_text}\n\n【使用者需求】\n{requirement}"
    )

    if endpoint_choice == "海外加速通道 1 (api.chatanywhere.tech)":
        target_bases = ["[https://api.chatanywhere.tech/v1](https://api.chatanywhere.tech/v1)"]
    elif endpoint_choice == "海外加速通道 2 (api.openai-proxy.org/deepseek)":
        target_bases = ["[https://api.openai-proxy.org/deepseek/v1](https://api.openai-proxy.org/deepseek/v1)"]
    elif endpoint_choice == "自訂 Base URL":
        target_bases = [custom_base.strip().rstrip("/")]
    else:
        target_bases = [
            "[https://api.deepseek.com](https://api.deepseek.com)",
            "[https://api.deepseek.com/v1](https://api.deepseek.com/v1)",
        ]

    last_err = None

    for base_url in target_bases:
        http_client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(90.0, connect=25.0),
            follow_redirects=True,
        )

        try:
            client = OpenAI(
                api_key=api_key.strip(),
                base_url=base_url,
                http_client=http_client,
                max_retries=1,
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except (APIConnectionError, httpx.RequestError) as e:
            last_err = e
            continue
        except APIStatusError as e:
            raise e
        finally:
            http_client.close()

    if last_err:
        raise last_err


# 6. 搜尋執行流程
if search_button:
    current_key = st.session_state.get("deepseek_api_key", "").strip()

    if not current_key:
        st.error("請先在左側邊欄輸入有效的 DeepSeek API Key。")
    elif not user_prompt.strip():
        st.warning("請輸入搜尋需求內容。")
    else:
        df_bni = load_bni_data()
        if df_bni is None or df_bni.empty:
            st.error(
                "找不到 `bni_data.csv` 或檔案內容為空，請確認資料庫已放置於伺服器同目錄下。"
            )
        else:
            with st.spinner("正在檢索數據並由 AI 生成精準引薦分析..."):
                try:
                    dataset_text = df_bni.to_string(index=False)
                    raw_text = query_deepseek(
                        current_key,
                        dataset_text,
                        user_prompt.strip(),
                        endpoint_option,
                        custom_url,
                    )

                    cleaned_text = clean_json_response(raw_text)
                    data = json.loads(cleaned_text)
                    results = data.get("results", [])

                    if not results:
                        st.info(
                            "在現有資料庫中未找到符合該條件的會員，請嘗試更換關鍵字或擴大搜尋條件。"
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="section-title">
                                <svg class="bi-icon" width="22" height="22" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M11.354 4.646a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708l6-6a.5.5 0 0 1 .708 0z"/></svg>
                                為您匹配到 {len(results)} 位精準人脈：
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        for idx, item in enumerate(results, 1):
                            name = item.get("name", "未提供")
                            chapter = item.get("chapter", "未提供")
                            industry = item.get("industry", "未提供")
                            reason = item.get("reason", "無")
                            message = item.get("whatsapp_message", "")

                            st.markdown(
                                f"""
                                <div class="member-card">
                                    <div class="card-title">
                                        <svg class="bi-icon" width="20" height="20" viewBox="0 0 16 16"><path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H3zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/></svg>
                                        #{idx} {name}
                                    </div>
                                    <div class="card-meta">
                                        <span>
                                            <svg class="bi-icon" width="16" height="16" viewBox="0 0 16 16"><path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10zm0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/></svg>
                                            <b>分會：</b>{chapter}
                                        </span>
                                        <span>
                                            <svg class="bi-icon" width="16" height="16" viewBox="0 0 16 16"><path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v1.384l7.614 2.03a1.5 1.5 0 0 0 .772 0L16 5.884V4.5A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1h-3zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5z"/><path d="M0 12.5A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V6.85L8.741 8.826a2.5 2.5 0 0 1-1.482 0L0 6.85v5.65z"/></svg>
                                            <b>行業：</b>{industry}
                                        </span>
                                    </div>
                                    <div class="card-reason">
                                        <b>匹配理由：</b>{reason}
                                    </div>
                                </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            st.markdown(
                                "**複製 WhatsApp 破冰話術草稿：**"
                            )
                            st.code(message, language="text")
                            st.markdown("<br>", unsafe_allow_html=True)

                except json.JSONDecodeError:
                    st.error("解析模型回傳格式失敗，請重試或微調搜尋需求。")
                except APIStatusError as e:
                    if e.status_code == 401:
                        st.error(
                            "API Key 驗證失敗 (401 Unauthorized)。請確認輸入的 Key 是否正確。"
                        )
                    elif e.status_code == 402:
                        st.error(
                            "帳戶餘額不足 (402 Payment Required)。請前往 DeepSeek 官方後台充值餘額。"
                        )
                    else:
                        st.error(
                            f"API 請求失敗 (狀態碼 {e.status_code})：{e.message}"
                        )
                except APIConnectionError as e:
                    st.error(
                        f"連線至該端點失敗（連線超時或被攔截）。\n\n"
                        f"**詳細錯誤**：{e}\n\n"
                        f"👉 **解決方式**：請在左側邊欄將【連線節點選擇】切換為 **海外加速通道 1** 或 **海外加速通道 2** 重試！"
                    )
                except Exception as e:
                    st.error(f"執行時發生非預期錯誤：{e}")
