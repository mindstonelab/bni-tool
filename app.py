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

# 1. 頁面配置與配色設定（深藍色 #003366 與 金色 #C9A96E）
st.set_page_config(
    page_title="BNI 人脈掘金",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --primary-blue: #003366;
        --accent-gold: #C9A96E;
    }
    .main-header {
        color: var(--primary-blue);
        font-weight: 800;
        border-bottom: 2px solid var(--accent-gold);
        padding-bottom: 8px;
        margin-bottom: 20px;
    }
    .member-card {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-left: 5px solid var(--accent-gold);
        border-radius: 8px;
        padding: 18px 22px;
        margin-bottom: 18px;
        box-shadow: 0 4px 6px rgba(0, 51, 102, 0.05);
    }
    .card-title {
        color: var(--primary-blue);
        font-size: 1.25rem;
        font-weight: bold;
        margin-bottom: 6px;
    }
    .card-meta {
        color: #555555;
        font-size: 0.95rem;
        margin-bottom: 12px;
    }
    .card-reason {
        color: #333333;
        background-color: #F8F9FA;
        padding: 10px;
        border-radius: 6px;
        font-size: 0.95rem;
        margin-bottom: 12px;
    }
    .stButton>button {
        background-color: var(--primary-blue);
        color: #FFFFFF;
        border-radius: 6px;
        border: 1px solid var(--accent-gold);
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #002244;
        color: var(--accent-gold);
        border-color: var(--accent-gold);
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
    st.markdown("### ⚙️ 系統設定")

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

    # 端點選擇：避免海外伺服器連線官方被封
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
    3. 在主畫面輸入引薦需求，點擊「🚀 搜尋人脈」。
    """
    )

# 4. 主畫面邏輯（無歷史紀錄，每次刷新對話框必為空白）
st.markdown(
    '<h1 class="main-header">🤝 BNI 人脈掘金系統</h1>', unsafe_allow_html=True
)

user_prompt = st.text_area(
    "請輸入您的搜尋需求（例如：尋找 3 位餐飲或食品相關會員，想洽談聯名禮盒合作）：",
    value="",
    height=130,
    placeholder="在此輸入您的人脈對接需求...",
)

search_button = st.button("🚀 搜尋人脈", use_container_width=True)


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

    # 決定呼叫節點
    if endpoint_choice == "海外加速通道 1 (api.chatanywhere.tech)":
        target_bases = ["[https://api.chatanywhere.tech/v1](https://api.chatanywhere.tech/v1)"]
    elif endpoint_choice == "海外加速通道 2 (api.openai-proxy.org/deepseek)":
        target_bases = ["[https://api.openai-proxy.org/deepseek/v1](https://api.openai-proxy.org/deepseek/v1)"]
    elif endpoint_choice == "自訂 Base URL":
        target_bases = [custom_base.strip().rstrip("/")]
    else:
        # 官方端點
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
        st.error("❌ 請先在左側邊欄輸入有效的 DeepSeek API Key。")
    elif not user_prompt.strip():
        st.warning("⚠️ 請輸入搜尋需求內容。")
    else:
        df_bni = load_bni_data()
        if df_bni is None or df_bni.empty:
            st.error(
                "❌ 找不到 `bni_data.csv` 或檔案內容為空，請確認資料庫已放置於伺服器同目錄下。"
            )
        else:
            with st.spinner(
                "🔍 正在檢索數據並由 AI 生成精準引薦分析..."
            ):
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
                            "💡 在現有資料庫中未找到符合該條件的會員，請嘗試更換關鍵字或擴大搜尋條件。"
                        )
                    else:
                        st.markdown(
                            f"### 🎯 為您匹配到 {len(results)} 位精準人脈："
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
                                    <div class="card-title">#{idx} {name}</div>
                                    <div class="card-meta">📍 <b>分會：</b>{chapter} ｜ 💼 <b>行業：</b>{industry}</div>
                                    <div class="card-reason">💡 <b>匹配理由：</b>{reason}</div>
                                </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            st.markdown(
                                "**📋 複製 WhatsApp 破冰話術草稿：**"
                            )
                            st.code(message, language="text")
                            st.markdown("<br>", unsafe_allow_html=True)

                except json.JSONDecodeError:
                    st.error(
                        "❌ 解析模型回傳格式失敗，請重試或微調搜尋需求。"
                    )
                except APIStatusError as e:
                    if e.status_code == 401:
                        st.error(
                            "❌ API Key 驗證失敗 (401 Unauthorized)。請確認輸入的 Key 是否正確。"
                        )
                    elif e.status_code == 402:
                        st.error(
                            "❌ 帳戶餘額不足 (402 Payment Required)。請前往 DeepSeek 官方後台充值餘額。"
                        )
                    else:
                        st.error(
                            f"❌ API 請求失敗 (狀態碼 {e.status_code})：{e.message}"
                        )
                except APIConnectionError as e:
                    st.error(
                        f"❌ 連線至該端點失敗（連線超時或被攔截）。\n\n"
                        f"**詳細錯誤**：{e}\n\n"
                        f"👉 **解決方式**：請在左側邊欄將【連線節點選擇】切換為 **海外加速通道 1** 或 **海外加速通道 2** 重試！"
                    )
                except Exception as e:
                    st.error(f"❌ 執行時發生非預期錯誤：{e}")
