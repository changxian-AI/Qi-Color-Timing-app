import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 & 状态管理 -------
st.set_page_config(
    page_title="气色·命运罗盘",
    page_icon="🧿",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'
if 'bazi_report' not in st.session_state:
    st.session_state.bazi_report = None

# ------- 2. 颜值急救包 (CSS 修复) -------
st.markdown("""
<style>
    /* 1. 强制覆盖侧边栏和主背景，统一色调 */
    [data-testid="stAppViewContainer"], .stApp {
        background: radial-gradient(circle at 50% 20%, #2e1c59, #0f0c29, #000000);
        color: #E0E0E0;
    }
    
    /* 2. 修复侧边栏颜色 */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 12, 41, 0.95);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    /* 3. 输入框区域美化 (控制台风格) */
    .input-panel {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
    }
    
    /* 4. 按钮特效 (更强的兼容性) */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(45deg, #FF0080, #7928CA);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 18px;
        box-shadow: 0 4px 15px rgba(255, 0, 128, 0.4);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 0, 128, 0.6);
        color: #fff;
    }

    /* 5. 文字和标题优化 */
    h1 {
        text-shadow: 0 0 20px rgba(121, 40, 202, 0.8);
        font-weight: 800 !important;
    }
    
    /* 6. 结果卡片美化 */
    .result-card {
        background: rgba(20, 20, 40, 0.6);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    /* 7. 锦囊特效 */
    .advice-box {
        background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%);
        color: #333;
        padding: 20px;
        border-radius: 12px;
        margin-top: 20px;
        font-weight: bold;
        box-shadow: 0 0 20px rgba(253, 185, 49, 0.4);
        border: 2px solid #fff;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑部分 (保持 v3.0 功能) -------

# 日报 Prompt
DAILY_PROMPT = """
Role: 赛博命理师。
Goal: 输出JSON，包含四维评分、幸运色、黄金时辰、宜忌、锦囊。
Output Format (JSON):
{
    "day_master": {"gan": "甲", "element": "木", "trait": "参天大树，正直仁慈"}, 
    "scores": {"money": 4, "career": 3, "love": 5, "energy": 3},
    "lucky_color": {"main": "色名", "hex": "#HEX", "reason": "理由"},
    "golden_hour": {"time": "时辰", "action": "宜做之事"},
    "guide": {"lucky": "宜...", "taboo": "忌..."},
    "advice": "一条直击痛点的建议",
    "quote": "玄学金句"
}
"""

# 深度分析 Prompt
FULL_ANALYSIS_PROMPT = """
Role: 宗师级命理顾问。
Goal: 基于用户提供的出生时间（含城市），**自行推算真太阳时**，进行八字排盘和深度分析。
Output Format (Markdown): 
输出优美的Markdown报告，包含：真太阳时排盘、格局分析、性格、事业、婚姻、宗师寄语。
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
    st.title("🔮 命理中枢")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ 灵力已链接")
    else:
        api_key = st.text_input("输入 API Key", type="password")
    
    st.markdown("---")
    if st.button("🏠 返回首页"):
        st.session_state.bazi_report = None
        switch_page('daily')

# ================= 页面 1: 首页 (Daily) =================
if st.session_state.page == 'daily':
    st.markdown("# 🧿 今日能量场")
    st.caption("Cyber-Metaphysics Energy Guide")
    
    # 输入控制台 (包在一个半透明容器里)
    st.markdown('<div class="input-panel">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("预测日期", datetime.date.today())
    st.markdown('</div>', unsafe_allow_html=True)

    # 巨大的紫色按钮
    if st.button("⚡️ 开启今日运势"):
        if not api_key:
            st.error("请在左侧配置 API Key")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('🔮 正在下载宇宙信号...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # ---- 结果展示区 ----
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                
                # 1. 命主图腾
                dm = data['day_master']
                st.markdown(f"""
                <div style="text-align:center; margin-bottom:20px;">
                    <div style="font-size:48px; font-weight:bold; color:#FFF; text-shadow:0 0 20px #7928CA;">
                        {dm['gan']} <span style="font-size:20px; opacity:0.8;">{dm['element']}命</span>
                    </div>
                    <div style="color:#AAA; font-size:14px;">{dm['trait']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. 评分
                st.markdown("### 📊 能量雷达")
                c1, c2, c3, c4 = st.columns(4)
                def render_score(col, label, val):
                    col.markdown(f"""
                    <div style="text-align:center; background:rgba(0,0,0,0.3); padding:8px; border-radius:8px;">
                        <div style="color:#888; font-size:12px;">{label}</div>
                        <div style="color:#FFD700; font-size:16px;">{'⚡'*val}</div>
                    </div>""", unsafe_allow_html=True)
                
                render_score(c1, "财运", data['scores']['money'])
                render_score(c2, "事业", data['scores']['career'])
                render_score(c3, "桃花", data['scores']['love'])
                render_score(c4, "状态", data['scores']['energy'])
                
                # 3. 幸运色
                lucky = data['lucky_color']
                st.markdown(f"""
                <div style="margin-top:20px; padding:15px; border-left:5px solid {lucky['hex']}; background:rgba(255,255,255,0.05);">
                    <b>👕 穿搭 OOTD：</b> {lucky['main']} <span style="opacity:0.6;">| {lucky['reason']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 4. 黄金时辰
                gh = data['golden_hour']
                st.markdown(f"""
                <div style="margin-top:10px; padding:10px; background:linear-gradient(90deg, #F2994A, #F2C94C); color:#000; border-radius:50px; text-align:center; font-weight:bold;">
                    ⏳ {gh['time']}：{gh['action']}
                </div>
                """, unsafe_allow_html=True)

                # 5. 宜忌
                col_l, col_r = st.columns(2)
                with col_l:
                     st.success(f"**宜：** {data['guide']['lucky']}")
                with col_r:
                     st.error(f"**忌：** {data['guide']['taboo']}")

                # 6. 锦囊
                st.markdown(f"""
                <div class="advice-box">
                    <div>📜 锦囊</div>
                    <div style="font-size:18px; margin-top:5px;">{data['advice']}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 7. 导流按钮
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 想要更深的答案？")
                if st.button("🗝 解锁完整真太阳时命盘 →"):
                    switch_page('full_analysis')

        except Exception as e:
            st.error(f"连接中断: {e}")

# ================= 页面 2: 深度分析 (Full) =================
elif st.session_state.page == 'full_analysis':
    st.markdown("# 🗝 命运全息解码")
    st.caption("AI 宗师级批命 · 真太阳时校正")
    
    # 输入面板
    st.markdown('<div class="input-panel">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        b_date = st.date_input("出生日期", datetime.date(1984, 8, 25))
    with col2:
        b_time = st.time_input("出生时间", datetime.time(12, 00))
    
    b_city = st.text_input("出生城市 (用于经纬度排盘)", "上海")
    st.caption("⚠️ 系统将根据城市自动推算真太阳时")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🚀 开始深度推演"):
        if not b_city or not api_key:
            st.error("请完善信息和 API Key")
            st.stop()

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在进行天文计算与因果推演...'):
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

    # 报告展示区
    if st.session_state.bazi_report:
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.bazi_report)
        st.markdown('</div>', unsafe_allow_html=True)
