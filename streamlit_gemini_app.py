import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·能量日历",
    page_icon="🧧",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'
if 'bazi_report' not in st.session_state:
    st.session_state.bazi_report = None

# ------- 2. 新中式 UI (视觉保留，布局修复) -------
st.markdown("""
<style>
    /* 引入宋体 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap');

    /* 全局背景：宣纸纹理 */
    .stApp {
        background-color: #F7F5F0;
        color: #2C2C2C;
        font-family: 'Noto Serif SC', serif;
    }
    
    /* 侧边栏美化 */
    [data-testid="stSidebar"] {
        background-color: #EAE6DA;
        border-right: 1px solid #D4CFC0;
    }

    /* 标题样式 */
    h1 {
        color: #3E2723;
        font-family: 'Noto Serif SC', serif;
        text-align: center;
        border-bottom: 2px solid #9E2A2B;
        padding-bottom: 15px;
        margin-bottom: 30px;
    }

    /* 输入框美化 (直接覆盖 Streamlit 原生样式，不再用 div 包裹) */
    .stDateInput, .stTextInput, .stTimeInput {
        background-color: white;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* 主按钮：朱砂红 (保留中国风视觉) */
    div.stButton > button {
        width: 100%;
        background-color: #9E2A2B;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 18px;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(158, 42, 43, 0.3);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #B22222;
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(158, 42, 43, 0.5);
        color: #fff;
    }
    
    /* 结果卡片：书卷样式 */
    .paper-card {
        background-color: #FFF;
        border: 1px solid #E0E0E0;
        border-left: 5px solid #9E2A2B;
        padding: 25px;
        margin-top: 20px;
        margin-bottom: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        border-radius: 6px;
    }

    /* 命主图腾 */
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
        box-shadow: 5px 5px 0px rgba(0,0,0,0.2);
    }
    .totem-char { font-size: 48px; font-weight: bold; color: #333; }
    .totem-sub { font-size: 14px; color: #9E2A2B; margin-top: 5px; font-weight: bold; }

    /* 评分 */
    .score-label { font-size: 12px; color: #666; margin-bottom: 5px; }
    .score-stars { color: #D4AF37; font-size: 16px; letter-spacing: 3px; }

    /* 宜忌 */
    .yi-box { background: rgba(46, 204, 113, 0.1); border: 1px solid #27ae60; color: #27ae60; padding: 10px; text-align: center; border-radius: 6px; }
    .ji-box { background: rgba(192, 57, 43, 0.1); border: 1px solid #c0392b; color: #c0392b; padding: 10px; text-align: center; border-radius: 6px; }

    /* 锦囊 */
    .advice-box {
        background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%);
        color: #333;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #FFF;
        box-shadow: 0 5px 15px rgba(253, 185, 49, 0.3);
    }

</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑部分 (回到现代文案) -------

# 日报 Prompt (改回现代/毒舌/职场风格)
DAILY_PROMPT = """
Role: 你是一位精通八字命理的现代职场策略顾问。
Goal: 基于用户日柱和流日，提供精准的运势评分、幸运色、黄金时辰、宜忌及锦囊。

Logic Rules:
1. **场景判断：** 区分工作日（搞钱/效率）与周末（桃花/放松）。
2. **建议风格：** 一针见血，现代口语化，带一点“玄学幽默”。不要讲古文。
3. **颜色建议：** 结合五行喜忌，给出具体的颜色名称。

Output Format (Strict JSON):
{
    "day_master": {"gan": "甲", "element": "木", "trait": "坚韧不拔的领袖"}, 
    "scores": {"money": 4, "career": 3, "love": 5, "energy": 3},
    "lucky_color": {"main": "颜色名", "hex": "#HEX", "reason": "理由"},
    "golden_hour": {"time": "时辰(几点-几点)", "action": "宜做之事"},
    "guide": {"lucky": "宜...", "taboo": "忌..."},
    "advice": "一条具体的行动建议",
    "quote": "一句职场/人生金句"
}
"""

FULL_ANALYSIS_PROMPT = """
Role: 资深命理分析师。
Goal: 真太阳时排盘与深度批断。
Task: 
1. 根据城市自动校正真太阳时。
2. 分析格局、性格、事业、婚姻。
Output Format (Markdown): 
请使用清晰的Markdown格式，标题现代化，例如【我的出厂设置】、【搞钱指南】、【感情黑盒】。
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
    st.title("🧧 命理书房")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ 密钥已加载")
    else:
        api_key = st.text_input("输入 API Key", type="password")
    
    st.markdown("---")
    if st.button("🏠 返回首页"):
        st.session_state.bazi_report = None
        switch_page('daily')

# ================= 页面 1: 首页 (Daily) =================
if st.session_state.page == 'daily':
    st.title("气色 · 能量日历")
    
    # 布局修复：不再使用 div 包裹，直接使用 columns
    # 并在 CSS 中对 stDateInput 进行了全局美化
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("查看日期", datetime.date.today())
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 按钮文案改回现代风格
    if st.button("⚡️ 开启今日能量"):
        if not api_key:
            st.error("请先在侧边栏输入 API Key")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在分析今日磁场...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # ---- 结果展示区 ----
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 1. 命主令牌 (UI保持中国风，内容现代)
                dm = data['day_master']
                st.markdown(f"""
                <div class="totem-box">
                    <div class="totem-char">{dm['gan']}</div>
                    <div class="totem-sub">{dm['element']} · 命</div>
                </div>
                <div style="text-align:center; color:#555; margin-bottom:30px; font-style:italic;">
                    “ {dm['trait']} ”
                </div>
                """, unsafe_allow_html=True)
                
                # 2. 纸质卡片容器
                st.markdown('<div class="paper-card">', unsafe_allow_html=True)
                
                # 评分
                st.markdown("#### 📊 能量雷达")
                c1, c2, c3, c4 = st.columns(4)
                def render_score(col, label, val):
                    col.markdown(f"""
                    <div style="text-align:center;">
                        <div class="score-label">{label}</div>
                        <div class="score-stars">{'★'*val}</div>
                    </div>""", unsafe_allow_html=True)
                
                render_score(c1, "财运", data['scores']['money'])
                render_score(c2, "事业", data['scores']['career'])
                render_score(c3, "桃花", data['scores']['love'])
                render_score(c4, "状态", data['scores']['energy'])
                
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
                st.info(f"⏳ **黄金时辰：{gh['time']}** — {gh['action']}")

                st.markdown('</div>', unsafe_allow_html=True)

                # 3. 锦囊 (独立)
                st.markdown(f"""
                <div class="advice-box">
                    <div style="font-weight:bold; color:#F57F17; margin-bottom:5px;">💡 锦囊妙计</div>
                    <div style="font-size:18px; font-weight:bold; color:#333;">{data['advice']}</div>
                    <div style="margin-top:15px; color:#666; font-size:12px;">“ {data['quote']} ”</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 4. 导流
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗝 解锁完整真太阳时命盘 →"):
                    switch_page('full_analysis')

        except Exception as e:
            st.error(f"连接中断: {e}")

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
    
    b_city = st.text_input("出生城市 (用于真太阳时校正)", "上海")
    
    if st.button("🚀 开始深度推演"):
        if not b_city or not api_key:
            st.error("请填写城市和 API Key")
            st.stop()

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在排盘与分析...'):
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
            st.error(f"推演失败: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.bazi_report:
        st.markdown('<div class="paper-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.bazi_report)
        st.markdown('</div>', unsafe_allow_html=True)
