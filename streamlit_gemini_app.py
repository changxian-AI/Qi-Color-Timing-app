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
    page_icon="🔮",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'
if 'bazi_report' not in st.session_state:
    st.session_state.bazi_report = None

# ------- 2. UI 样式 (Notion 风格 + 对齐优化) -------
st.markdown("""
<style>
    /* 全局清爽白底 */
    .stApp {
        background-color: #FFFFFF;
        color: #333;
    }
    
    /* 按钮优化 */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        transition: all 0.2s;
    }
    div.stButton > button:hover { transform: translateY(-1px); opacity: 0.9; }
    
    /* 次要按钮 */
    .secondary-btn button {
        background: transparent;
        border: 1px solid #764ba2;
        color: #764ba2;
        box-shadow: none;
    }

    /* --- 核心组件：能量对撞条 (Me vs Today) --- */
    .battle-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 15px 20px;
        margin-bottom: 20px;
    }
    .battle-side {
        text-align: center;
        width: 30%;
    }
    .battle-center {
        text-align: center;
        width: 40%;
        color: #666;
        font-size: 14px;
        font-weight: bold;
        border-bottom: 2px solid #E9ECEF;
        padding-bottom: 5px;
    }
    .bazi-char { font-size: 24px; font-weight: bold; color: #333; display: block; }
    .bazi-desc { font-size: 12px; color: #888; background: #eee; padding: 2px 6px; border-radius: 4px; }
    
    /* 幸运色卡片 */
    .lucky-card {
        background-color: #FFF;
        border: 1px solid #E0E0E0;
        border-left: 8px solid #333; /* 动态颜色 */
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }

    /* --- 对齐布局组件 --- */
    .grid-box {
        padding: 15px;
        border-radius: 8px;
        height: 100%; /* 强制等高 */
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    
    /* 颜色定义 */
    .bg-blue { background-color: #E3F2FD; color: #1565C0; }   /* 黄金时辰 */
    .bg-green { background-color: #E8F5E9; color: #2E7D32; }  /* 宜 */
    .bg-red { background-color: #FFEBEE; color: #C62828; }    /* 忌 */
    .bg-gold { background-color: #FFF8E1; color: #F57F17; border: 1px solid #FFECB3; } /* 锦囊 */

    /* 评分项 */
    .score-item { text-align: center; }
    .score-val { font-size: 16px; color: #FBC02D; letter-spacing: 1px; }
    .score-label { font-size: 12px; color: #999; }

</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑部分 -------

# Prompt 更新：增加今日五行字段，强调对比关系
DAILY_PROMPT = """
Role: 现代命理策略顾问。
Goal: 输出 JSON。
Logic:
1. 场景：工作日(效率) vs 周末(生活)。
2. **核心分析：** 必须解释【用户日主】与【今日干支】的生克关系（如：甲木克戊土，为偏财）。
3. 必须提供今日干支的五行属性。

Output Format (Strict JSON):
{
    "user": {"gan": "辛", "element": "金", "label": "我 (日主)"}, 
    "today": {"ganzhi": "甲午", "element": "木火", "relation_desc": "金克木，今日是您的【正财日】"},
    "scores": {"money": 4, "career": 3, "love": 5, "energy": 3},
    "lucky_color": {"main": "白色", "hex": "#FFFFFF", "reason": "财多身弱，需金帮身..."},
    "golden_hour": {"time": "15:00-17:00 (申时)", "action": "头脑风暴"},
    "guide": {"lucky": "请客吃饭", "taboo": "与长辈顶撞"},
    "advice": "详细的行动锦囊...",
    "quote": "金句"
}
"""

FULL_ANALYSIS_PROMPT = """
Role: 资深命理分析师。
Task: 自动校正真太阳时，排盘，深度批断。
Output: Markdown格式报告。
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
    st.title("🔮 设置")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ API Key 已加载")
    else:
        api_key = st.text_input("输入 API Key", type="password")
    
    st.markdown("---")
    if st.button("🏠 返回首页"):
        st.session_state.bazi_report = None
        switch_page('daily')

# ================= 页面 1: 首页 (Daily) =================
if st.session_state.page == 'daily':
    st.title("气色 · 全场景能量日历")
    st.caption("Powered by Gemini 2.5 + LunarPython")
    
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("查看日期", datetime.date.today())
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀 获取今日指引"):
        if not api_key:
            st.error("请先配置 API Key")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在分析五行磁场...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                st.markdown("<br>", unsafe_allow_html=True)

                # ---- 1. 能量对撞条 (Me vs Today) ----
                # 这是一个横向的 Flex 布局，左边是我，右边是天，中间是关系
                u = data['user']
                t = data['today']
                
                st.markdown(f"""
                <div class="battle-bar">
                    <div class="battle-side">
                        <span class="bazi-desc">{u['label']}</span>
                        <span class="bazi-char">{u['gan']}</span>
                        <span style="color:#999; font-size:12px;">五行属{u['element']}</span>
                    </div>
                    <div class="battle-center">
                        ⚡ {t['relation_desc']} ⚡
                    </div>
                    <div class="battle-side">
                        <span class="bazi-desc">今日能量</span>
                        <span class="bazi-char">{t['ganzhi']}</span>
                        <span style="color:#999; font-size:12px;">五行属{t['element']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # ---- 2. 幸运色卡片 ----
                lucky = data['lucky_color']
                st.markdown(f"""
                <div class="lucky-card" style="border-left-color: {lucky['hex']};">
                    <div style="font-size: 20px; font-weight: bold; color: #333; display: flex; align-items: center;">
                        👕 今日幸运色：{lucky['main']}
                    </div>
                    <div style="margin-top: 8px; color: #555; line-height: 1.5;">
                        {lucky['reason']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ---- 3. 评分雷达 ----
                c1, c2, c3, c4 = st.columns(4)
                scores = data['scores']
                def render_score(col, label, val):
                    col.markdown(f"""<div class="score-item"><div class="score-label">{label}</div><div class="score-val">{'★'*val}</div></div>""", unsafe_allow_html=True)
                
                render_score(c1, "财运", scores['money'])
                render_score(c2, "事业", scores['career'])
                render_score(c3, "人缘", scores['love'])
                render_score(c4, "状态", scores['energy'])
                
                st.markdown("---")

                # ---- 4. 行动指南 (严格对齐布局) ----
                
                # 第一行：黄金时辰 (通栏)
                gh = data['golden_hour']
                st.markdown(f"""
                <div class="grid-box bg-blue" style="margin-bottom: 15px;">
                    <span style="font-size:18px;">⏰ 黄金时辰：{gh['time']}</span><br>
                    <span style="opacity:0.8; font-size:14px;">宜：{gh['action']}</span>
                </div>
                """, unsafe_allow_html=True)

                # 第二行：宜 vs 忌 (两列等宽等高)
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f"""<div class="grid-box bg-green">✅ 宜：{data['guide']['lucky']}</div>""", unsafe_allow_html=True)
                with col_r:
                    st.markdown(f"""<div class="grid-box bg-red">🚫 忌：{data['guide']['taboo']}</div>""", unsafe_allow_html=True)

                # 第三行：锦囊 (通栏，放在最下面，作为总结)
                st.markdown(f"""
                <div class="grid-box bg-gold" style="margin-top: 15px;">
                    <span style="font-size:16px;">💡 <b>锦囊：</b>{data['advice']}</span>
                </div>
                """, unsafe_allow_html=True)

                # ---- 5. 金句 & 导流 ----
                st.markdown(f"""
                <div style="text-align:center; margin-top:30px; color:#888; font-style:italic;">
                    “ {data['quote']} ”
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                if st.button("🗝 解锁真太阳时 · 深度排盘 →"):
                    switch_page('full_analysis')
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"连接中断: {e}")

# ================= 页面 2: 深度分析 (Full) =================
elif st.session_state.page == 'full_analysis':
    st.title("🗝 个人命盘全解")
    st.caption("AI 深度批断 · 真太阳时校正")
    
    # 输入卡片
    st.markdown('<div class="info-card" style="background:#f8f9fa; padding:20px; border-radius:12px; border:1px solid #eee;">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        b_date = st.date_input("出生日期", datetime.date(1984, 8, 25))
    with col2:
        b_time = st.time_input("出生时间", datetime.time(12, 00))
    
    b_city = st.text_input("出生城市 (用于经纬度校正)", "上海")
    st.caption("⚠️ 系统将根据城市自动计算经度差，修正为真太阳时。")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 开始排盘推演"):
        if not b_city or not api_key:
            st.error("请填写城市和 API Key")
            st.stop()

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在进行天文计算与命理推演...'):
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
        st.markdown("---")
        st.markdown(st.session_state.bazi_report)
