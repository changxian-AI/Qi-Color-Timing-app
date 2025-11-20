import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·职场能量日历",
    page_icon="🔮",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'
if 'bazi_report' not in st.session_state:
    st.session_state.bazi_report = None

# ------- 2. 清爽现代 UI (复刻截图风格，适配复杂功能) -------
st.markdown("""
<style>
    /* 全局设置：清爽职场风 */
    .stApp {
        background-color: #FFFFFF;
        color: #333333;
    }
    
    /* 按钮：紫色渐变 (保持您喜欢的风格) */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #8E2DE2, #4A00E0);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover {
        opacity: 0.9;
    }
    
    /* 次要按钮 (幽灵按钮) */
    .secondary-btn button {
        background: white;
        border: 1px solid #4A00E0;
        color: #4A00E0;
    }

    /* 通用卡片容器 */
    .info-card {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }

    /* 命主图腾 (现代简约版) */
    .totem-container {
        text-align: center;
        padding: 20px;
        background: white;
        border: 1px solid #eee;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .totem-char { font-size: 40px; font-weight: bold; color: #333; }
    .totem-desc { color: #666; font-size: 14px; margin-top: 5px; }

    /* 幸运色卡片 (带左侧色条) */
    .lucky-card {
        background-color: #FFF;
        border: 1px solid #E0E0E0;
        border-left: 8px solid #333; /* 动态颜色 */
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* 功能性小盒子 (扁平化) */
    .box-blue { background-color: #E3F2FD; color: #1565C0; padding: 15px; border-radius: 8px; font-weight: bold; font-size: 15px; height: 100%; }
    .box-green { background-color: #E8F5E9; color: #2E7D32; padding: 15px; border-radius: 8px; font-weight: bold; font-size: 15px; height: 100%; }
    .box-red   { background-color: #FFEBEE; color: #C62828; padding: 15px; border-radius: 8px; font-weight: bold; font-size: 15px; height: 100%; }
    .box-gold  { background-color: #FFF8E1; color: #F57F17; padding: 15px; border-radius: 8px; border: 1px solid #FFECB3; margin-top: 15px; }

    /* 评分样式 */
    .score-item { text-align: center; }
    .score-label { font-size: 12px; color: #888; margin-bottom: 4px; }
    .score-val { font-size: 16px; color: #FBC02D; letter-spacing: 2px; }

    /* 标题优化 */
    h1 { font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 700; color: #2c3e50; }
    
</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑部分 (保留所有功能) -------

# 日报 Prompt (包含评分、图腾、详细建议)
DAILY_PROMPT = """
Role: 现代职场命理策略顾问。
Goal: 基于用户八字和流日，输出JSON。
Logic:
1. 场景：工作日(效率/搞钱) vs 周末(生活/桃花)。
2. 风格：专业、干练、现代。
3. 内容：必须包含命主特征、四维评分、幸运色、黄金时辰、宜忌、锦囊。

Output Format (Strict JSON):
{
    "day_master": {"gan": "甲", "element": "木", "trait": "正直的领袖，宁折不弯"}, 
    "scores": {"money": 4, "career": 3, "love": 5, "energy": 3},
    "lucky_color": {"main": "白色", "hex": "#FFFFFF", "reason": "金克木为财，今日财星旺..."},
    "golden_hour": {"time": "申时 15-17点", "action": "汇报工作"},
    "guide": {"lucky": "请客吃饭", "taboo": "与老板争执"},
    "advice": "具体的职场行动建议...",
    "quote": "一句金句"
}
"""

# 深度分析 Prompt (保留真太阳时逻辑)
FULL_ANALYSIS_PROMPT = """
Role: 资深命理分析师。
Task: 
1. 根据[出生城市]和[出生时间]自动校正真太阳时。
2. 进行八字排盘。
3. 深度分析：格局强弱、喜用神、性格优缺、事业财运、婚姻情感。
Output: 清晰的 Markdown 格式报告，标题要现代专业。
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
    st.title("气色 · 职场能量日历")
    st.caption("Powered by Gemini 2.5 + LunarPython")
    
    # 输入区 (原生样式，最干净)
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("查看日期", datetime.date.today())
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀 获取今日指南"):
        if not api_key:
            st.error("请先在侧边栏配置 API Key")
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
                
                # ---- 结果展示区 (清爽风格) ----
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 1. 命主信息 (简洁卡片)
                dm = data['day_master']
                st.markdown(f"""
                <div class="totem-container">
                    <div class="totem-char">{dm['gan']} <span style="font-size:20px; font-weight:normal; color:#888;">{dm['element']}</span></div>
                    <div class="totem-desc">“ {dm['trait']} ”</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. 能量评分 (四列布局)
                st.markdown("##### 📊 今日指数")
                c1, c2, c3, c4 = st.columns(4)
                scores = data['scores']
                def render_score(col, label, val):
                    col.markdown(f"""<div class="score-item"><div class="score-label">{label}</div><div class="score-val">{'★'*val}</div></div>""", unsafe_allow_html=True)
                
                render_score(c1, "财运", scores['money'])
                render_score(c2, "事业", scores['career'])
                render_score(c3, "人缘", scores['love'])
                render_score(c4, "状态", scores['energy'])
                
                st.markdown("---")
                
                # 3. 幸运色 (带色条的卡片)
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
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 4. 行动指南 (色块布局)
                st.markdown("##### ⚡️ 行动指南")
                col_l, col_r = st.columns(2)
                with col_l:
                    # 黄金时辰 (蓝色)
                    gh = data['golden_hour']
                    st.markdown(f"""
                    <div class="box-blue">
                        ⏰ {gh['time']}<br>
                        <span style="font-weight:normal; font-size:14px; opacity:0.8;">宜：{gh['action']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    # 宜 (绿色)
                    st.markdown(f"""<div class="box-green" style="margin-top:15px;">✅ 宜：{data['guide']['lucky']}</div>""", unsafe_allow_html=True)
                    
                with col_r:
                    # 锦囊 (金色)
                    st.markdown(f"""
                    <div class="box-gold">
                        💡 <b>锦囊：</b>{data['advice']}
                    </div>
                    """, unsafe_allow_html=True)
                    # 忌 (红色)
                    st.markdown(f"""<div class="box-red" style="margin-top:15px;">🚫 忌：{data['guide']['taboo']}</div>""", unsafe_allow_html=True)

                # 5. 金句
                st.markdown(f"""
                <div style="text-align:center; margin-top:30px; color:#888; font-style:italic;">
                    “ {data['quote']} ”
                </div>
                """, unsafe_allow_html=True)
                
                # 6. 导流入口 (现代风格按钮)
                st.markdown("---")
                st.markdown("#### 想要更精准的个人分析？")
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
    
    # 使用清爽的卡片容器
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("##### 完善出生信息")
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

    # 报告展示
    if st.session_state.bazi_report:
        st.markdown("---")
        st.markdown(st.session_state.bazi_report)
