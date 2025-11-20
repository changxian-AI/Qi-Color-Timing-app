import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·命理书房",
    page_icon="🧧",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'
if 'bazi_report' not in st.session_state:
    st.session_state.bazi_report = None

# ------- 2. 新中式 UI (水墨书卷风) -------
st.markdown("""
<style>
    /* 引入外部字体 (尝试宋体风格) */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap');

    /* 全局背景：仿宣纸纹理 */
    .stApp {
        background-color: #F7F5F0; /* 米白 */
        color: #2C2C2C; /* 墨黑 */
        font-family: 'Noto Serif SC', serif;
    }
    
    /* 侧边栏：深木色 */
    [data-testid="stSidebar"] {
        background-color: #EAE6DA;
        border-right: 1px solid #D4Cfc0;
    }
    
    /* 输入框优化 (水墨风) */
    .stDateInput > label, .stTextInput > label, .stTimeInput > label {
        color: #5D4037 !important;
        font-weight: bold;
    }
    div[data-baseweb="input"] {
        background-color: #FFF !important;
        border: 1px solid #8D6E63 !important;
        border-radius: 4px !important; /* 方正一点 */
    }
    
    /* 按钮：朱砂红印章风格 */
    div.stButton > button {
        width: 100%;
        background-color: #9E2A2B; /* 朱砂红 */
        color: #FDFBF7;
        border: 1px solid #8A2526;
        padding: 12px 24px;
        border-radius: 6px;
        font-family: 'Noto Serif SC', serif;
        font-size: 18px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #B22222;
        color: #FFF;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* 次要按钮：淡墨 */
    .secondary-btn button {
        background-color: transparent;
        color: #555;
        border: 1px solid #999;
    }

    /* 标题样式 */
    h1 {
        color: #3E2723;
        text-align: center;
        font-weight: normal;
        letter-spacing: 4px;
        border-bottom: 2px solid #9E2A2B;
        padding-bottom: 10px;
        margin-bottom: 30px;
    }
    
    /* 卡片：书卷样式 */
    .paper-card {
        background-color: #FFF;
        border: 1px solid #E0E0E0;
        border-left: 6px solid #9E2A2B; /* 左侧红线装饰 */
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        border-radius: 4px;
    }
    
    /* 日主图腾：令牌样式 */
    .totem-box {
        text-align: center;
        padding: 20px;
        border: 2px solid #333;
        width: 120px;
        height: 160px;
        margin: 0 auto 20px auto;
        background-color: #FFF;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 4px 4px 0px #999;
    }
    .totem-char { font-size: 48px; font-weight: bold; color: #333; }
    .totem-sub { font-size: 14px; color: #9E2A2B; margin-top: 5px; font-weight: bold; }
    
    /* 评分：云纹 */
    .score-label { font-size: 12px; color: #666; margin-bottom: 5px; }
    .score-stars { color: #D4AF37; font-size: 16px; letter-spacing: 2px; } /* 鎏金色 */

    /* 宜忌框 */
    .yi-box {
        background-color: rgba(46, 204, 113, 0.1);
        border: 1px solid #27ae60;
        color: #27ae60;
        padding: 15px;
        text-align: center;
        border-radius: 4px;
    }
    .ji-box {
        background-color: rgba(192, 57, 43, 0.1);
        border: 1px solid #c0392b;
        color: #c0392b;
        padding: 15px;
        text-align: center;
        border-radius: 4px;
    }

    /* 锦囊：红帖 */
    .tips-card {
        background-color: #FFF8E1;
        border: 1px solid #FFECB3;
        padding: 20px;
        text-align: center;
        border-radius: 8px;
        position: relative;
    }
    .tips-title {
        color: #F57F17;
        font-weight: bold;
        font-size: 14px;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }

</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑部分 -------

# 日报 Prompt (语气调整为更沉稳)
DAILY_PROMPT = """
Role: 传统命理国学大师。
Goal: 输出JSON，包含四维评分、幸运色(用中国传统色名)、黄金时辰、宜忌、锦囊。
Logic:
1. 幸运色必须使用中国传统色名（如：靛蓝、朱红、月白、藤黄）。
2. 语气古朴典雅，但建议要现代实用。

Output Format (JSON):
{
    "day_master": {"gan": "甲", "element": "木", "trait": "栋梁之材，仁义为本"}, 
    "scores": {"money": 4, "career": 3, "love": 5, "energy": 3},
    "lucky_color": {"main": "传统色名", "hex": "#HEX", "reason": "理由"},
    "golden_hour": {"time": "XX时", "action": "宜做之事"},
    "guide": {"lucky": "宜...", "taboo": "忌..."},
    "advice": "一条指点迷津的建议",
    "quote": "一句国学经典或禅语"
}
"""

FULL_ANALYSIS_PROMPT = """
Role: 隐居宗师。
Goal: 真太阳时排盘与深度批断。
Output Format (Markdown): 
请以Markdown格式输出，使用古朴的标题风格（如【命局总纲】、【性情剖析】）。
"""

def get_bazi_simple(date_obj):
    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
    lunar = solar.getLunar()
    return {"full": f"{lunar.getDayInGanZhi()}", "gan": lunar.getDayGan()}

def switch_page(page_name):
    st.session_state.page = page_name
    st.rerun()

# ------- 4. 页面构建 -------

# 侧边栏
with st.sidebar:
    st.markdown("### 🧧 命理书房")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ 钥匙已备")
    else:
        api_key = st.text_input("输入 API Key", type="password")
    
    st.markdown("---")
    st.caption("“顺势而为，方得始终。”")
    if st.button("🏠 回到案前"):
        st.session_state.bazi_report = None
        switch_page('daily')

# ================= 页面 1: 首页 (Daily) =================
if st.session_state.page == 'daily':
    st.title("气色 · 能量日历")
    
    # 输入面板
    st.markdown('<div style="background:#FFF; padding:20px; border:1px solid #DDD; border-radius:8px;">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生辰", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("今日日期", datetime.date.today())
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🎋 批算今日流年"):
        if not api_key:
            st.error("请先在侧边栏出示钥匙 (API Key)")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('大师正在以此生辰入定推演...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # ---- 结果展示区 ----
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 1. 命主令牌
                dm = data['day_master']
                st.markdown(f"""
                <div class="totem-box">
                    <div class="totem-char">{dm['gan']}</div>
                    <div class="totem-sub">{dm['element']} · 命</div>
                </div>
                <div style="text-align:center; color:#666; font-style:italic; margin-bottom:30px;">
                    “ {dm['trait']} ”
                </div>
                """, unsafe_allow_html=True)
                
                # 2. 纸质卡片容器
                st.markdown('<div class="paper-card">', unsafe_allow_html=True)
                
                # 评分
                st.markdown("#### 📊 今日气运")
                c1, c2, c3, c4 = st.columns(4)
                def render_score(col, label, val):
                    col.markdown(f"""
                    <div style="text-align:center;">
                        <div class="score-label">{label}</div>
                        <div class="score-stars">{'★'*val}</div>
                    </div>""", unsafe_allow_html=True)
                
                render_score(c1, "财禄", data['scores']['money'])
                render_score(c2, "功名", data['scores']['career'])
                render_score(c3, "姻缘", data['scores']['love'])
                render_score(c4, "精气", data['scores']['energy'])
                
                st.markdown("---")
                
                # 幸运色
                lucky = data['lucky_color']
                st.markdown(f"""
                <div style="display:flex; align-items:center;">
                    <div style="width:50px; height:50px; background-color:{lucky['hex']}; border-radius:50%; border:3px solid #EEE; margin-right:15px;"></div>
                    <div>
                        <div style="font-weight:bold; font-size:18px;">{lucky['main']}</div>
                        <div style="color:#666; font-size:14px;">{lucky['reason']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # 宜忌
                col_l, col_r = st.columns(2)
                with col_l:
                     st.markdown(f"""<div class="yi-box"><b>宜</b><br>{data['guide']['lucky']}</div>""", unsafe_allow_html=True)
                with col_r:
                     st.markdown(f"""<div class="ji-box"><b>忌</b><br>{data['guide']['taboo']}</div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                
                # 黄金时辰
                gh = data['golden_hour']
                st.info(f"⏳ **良辰：{gh['time']}** — {gh['action']}")

                st.markdown('</div>', unsafe_allow_html=True)

                # 3. 锦囊 (独立)
                st.markdown(f"""
                <div class="tips-card">
                    <div class="tips-title">🎐 宗师锦囊</div>
                    <div style="font-size:18px; font-weight:bold; color:#333;">{data['advice']}</div>
                    <div style="margin-top:15px; color:#999; font-size:12px;">{data['quote']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 4. 导流
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                if st.button("🗝 开启真太阳时 · 终极排盘 →"):
                    switch_page('full_analysis')
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"推演中断: {e}")

# ================= 页面 2: 深度分析 (Full) =================
elif st.session_state.page == 'full_analysis':
    st.title("🗝 命盘全解")
    
    st.markdown('<div class="paper-card">', unsafe_allow_html=True)
    st.subheader("完善出生信息")
    col1, col2 = st.columns(2)
    with col1:
        b_date = st.date_input("出生日期", datetime.date(1984, 8, 25))
    with col2:
        b_time = st.time_input("出生时间", datetime.time(12, 00))
    
    b_city = st.text_input("出生城市 (用于天文校正)", "上海")
    
    if st.button("🚀 启卦推算"):
        if not b_city or not api_key:
            st.error("信息不全，无法推演")
            st.stop()

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在校正真太阳时，排布四柱八字...'):
                prompt = f"""
                {FULL_ANALYSIS_PROMPT}
                出生日期：{b_date}
                出生时间：{b_time}
                出生城市：{b_city}
                """
                response = model.generate_content(prompt)
                st.session_state.bazi_report = response.text
                st.rerun()

        except Exception as e:
            st.error(f"推算失败: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # 报告展示区
    if st.session_state.bazi_report:
        st.markdown('<div class="paper-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.bazi_report)
        st.markdown('</div>', unsafe_allow_html=True)
