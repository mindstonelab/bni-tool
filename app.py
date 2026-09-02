st.markdown(
    """
    <style>
    /* Global Page Background & Fonts */
    .stApp {
        background-color: #0A192F;
        color: #E6F1FF;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar Background & Base Text */
    section[data-testid="stSidebar"] {
        background-color: #112240;
        border-right: 1px solid #1E2D4A;
    }
    section[data-testid="stSidebar"] * {
        color: #E6F1FF !important;
    }
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] li, 
    section[data-testid="stSidebar"] span {
        color: #8892B0 !important;
    }
    
    /* Input & Select Box Text Fixes */
    section[data-testid="stSidebar"] input, 
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #E6F1FF !important;
        background-color: #172A45 !important;
    }

    /* Headers & Title Styling */
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

    /* Form Field Labels */
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
