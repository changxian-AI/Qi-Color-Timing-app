import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 (开启宽屏以适配炫酷背景) -------
st.set_page_config(
    page_title="气色·能量日历 Pro",
    page_icon="🔮",
    layout="centered"
)

# ------- 2. 炫酷 UI 注入 (赛博玄学风) -------
st.markdown("""
<style>
    /* 全局背景：深邃星空紫 */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: #fff;
    }
    
    /* 输入框美化 */
    .stDateInput > label, .stTextInput > label {
        color: #e0e0e0 !important;
    }
    
    /* 按钮特效：霓虹流光 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background: linear-gradient(90deg, #FF00CC, #333399);
        color: white;
        font-weight: bold;
        border: none;
        box-shadow: 0 0 15px rgba(255, 0, 204, 0.5);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 25px rgba(255, 0, 204, 0.8);
    }

    /* 通用毛玻璃卡片 */
    .glass-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* 评分球 */
    .score-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 12px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .score-val { font-size: 20px; font-weight: bold; color: #FFD700; }
    .score-label { font-size: 12px; color: #aaa; margin-top: 4px; }

    /* 幸运色卡片 */
    .color-box {
        height: 80px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        margin-bottom: 10px;
    }

    /* 宜忌对决 */
    .action-card {
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        height: 100%;
    }
    .lucky-bg { background: linear-gradient(135deg, rgba(39, 174, 96, 0.2), rgba(39, 174, 96, 0.4)); border: 1px solid #27ae60; }
    .taboo-bg { background: linear-gradient(135deg, rgba(192, 57, 43, 0.2), rgba(192, 57, 43, 0.4)); border: 1px solid #c0392b; }
    .act-title { font-size: 14px; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }
    .act-content { font-size: 18px; font-weight: bold; margin-top: 8px; }

    /* 黄金时辰条 */
    .time-bar {
        background: linear-gradient(90deg, #F2994A, #F2C94C);
        color: #333;
        padding: 10px 20px;
        border-radius: 50px;
        font-weight: bold;
        text-align: center;
        margin-top: 10px;
        box-shadow: 0 0 15px rgba(242, 201, 76, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ------- 3. 核心逻辑：Prompt 升级 -------
SYSTEM_PROMPT = """
Role: 你是一位神秘、毒舌且精准的“赛博命理师”。
Goal: 基于用户八字和流日，提供【四维评分】、【黄金时辰】、【幸运色】及【宜忌指南】。

Logic Rules:
1. **场景判断：** 工作日侧重搞钱/升职，周末侧重桃花/放松。
2. **生克建议：** 必须基于五行生克（如：官杀重用印化解）。
3. **黄金时辰：** 必须给出一个具体的时辰（如：未时 13:00-15:00），并说明适合做什么。
4. **四维评分 (1-5星)：** 
   - 💰 财运 (Money)
   - 💼 事业 (Career)
   - 🌸 桃花 (Love) - *必须独立评分*
   - 🔋 能量 (Health/Energy)

Output Format (Strict JSON):
{
    "user_info": "您的日柱：[日柱] ([五行])",
    "scores": {
        "money": 4,
        "career": 3,
        "love": 5,
        "energy": 3
    },
    "lucky_color": {
        "main": "建议颜色名称",
        "hex": "#颜色代码",
        "reason": "简短的命理理由"
    },
    "golden_hour": {
        "time": "未时 (13:00 - 15:00)",
        "action": "适合做的事情 (如: 约会/谈判)"
    },
    "guide": {
        "lucky": "宜：具体事项 (如: 喝冰美式)",
        "taboo": "忌：具体事项 (如: 穿绿帽子)"
    },
    "advice": "一句具体的转运建议",
    "quote": "一句神秘的玄学金句"
}
"""

# ------- 4. 辅助函数 -------
def get_bazi_info(date_obj):
    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
    lunar = solar.getLunar()
    return {
        "year_gz": lunar.getYearInGanZhi(),
        "month_gz": lunar.getMonthInGanZhi(),
        "day_gz": lunar.getDayInGanZhi(),
        "day_gan": lunar.getDayGan(),
        "day_zhi": lunar.getDayZhi()
    }

def get_day_type(date_obj):
    weekday = date_obj.weekday()
    if weekday >= 5:
        return "周末模式 (重点: 桃花/社牛/躺平)"
    else:
        return "工作日模式 (重点: 搞钱/防雷/效率)"

# ------- 5. 界面逻辑 -------
st.title("🔮 气色·能量日历 Pro")
st.caption("Cyber-Metaphysics Energy Guide")

# 侧边栏 (暗黑风格适配)
with st.sidebar:
    st.header("⚙️ 命理中枢")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ 灵力链接已建立")
    else:
        api_key = st.text_input("输入 API Key", type="password")

# 输入区
col1, col2 = st.columns(2)
with col1:
    dob = st.date_input("🎂 您的生辰", datetime.date(1984, 8, 25))
with col2:
    today = st.date_input("📅 预测日期", datetime.date.today())

# 运行按钮
if st.button("⚡️ 开启今日能量场"):
    
    if not api_key:
        st.error("❌ 灵力不足：请配置 API Key")
        st.stop()

    try:
        # Python 算命
        user_bazi = get_bazi_info(dob)
        today_bazi = get_bazi_info(today)
        day_context = get_day_type(today)

        # AI 算命
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        with st.spinner('🔮 正在连接高维宇宙数据库...'):
            full_prompt = f"""
            {SYSTEM_PROMPT}
            【用户数据】
            1. 用户日柱：{user_bazi['day_gz']} (天干: {user_bazi['day_gan']})
            2. 今日日期：{today_bazi['year_gz']}年 {today_bazi['month_gz']}月 {today_bazi['day_gz']}日
            3. 场景设定：{day_context}
            请严格生成JSON。
            """
            
            response = model.generate_content(full_prompt)
            clean_json = re.sub(r"```json\s*|\s*```", "", response.text).strip()
            data = json.loads(clean_json)

            # ------- 结果展示 (赛博风格) -------
            
            # 1. 四维评分系统 (使用自定义 CSS 渲染)
            st.markdown("### 📊 今日运势雷达")
            c1, c2, c3, c4 = st.columns(4)
            scores = data['scores']
            
            # 渲染评分小球
            def render_score(col, label, val, icon):
                with col:
                    st.markdown(f"""
                    <div class="score-container">
                        <div style="font-size:24px;">{icon}</div>
                        <div class="score-val">{"⚡" * val}</div>
                        <div class="score-label">{label}</div>
                    </div>
                    """, unsafe_allow_html=True)

            render_score(c1, "财运", scores['money'], "💰")
            render_score(c2, "事业", scores['career'], "💼")
            render_score(c3, "桃花", scores['love'], "🌸") # 新增桃花
            render_score(c4, "能量", scores['energy'], "🔋")

            # 2. 幸运色与 OOTD (毛玻璃卡片)
            st.markdown("<br>", unsafe_allow_html=True)
            lucky = data['lucky_color']
            st.markdown(f"""
            <div class="glass-card">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="font-size: 20px; margin-right: 10px;">👕</span>
                    <span style="font-weight: bold; font-size: 18px;">幸运穿搭 OOTD</span>
                </div>
                <div class="color-box" style="background-color: {lucky['hex']}; color: {'#000' if lucky['hex'] in ['#FFFFFF', '#FFF'] else '#FFF'}">
                    {lucky['main']}
                </div>
                <div style="font-size: 14px; opacity: 0.8; line-height: 1.6;">
                    {data['user_info']} 遇上今日流日。<br>
                    💡 {lucky['reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 3. 黄金时辰 (高亮条)
            gh = data.get('golden_hour', {'time': '未时', 'action': '摸鱼'})
            st.markdown(f"""
            <div class="time-bar">
                ⏳ 黄金时辰：{gh['time']} · 宜 {gh['action']}
            </div>
            <br>
            """, unsafe_allow_html=True)

            # 4. 宜忌对决 (左右护法)
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"""
                <div class="glass-card action-card lucky-bg">
                    <div class="act-title">LUCKY ACTION</div>
                    <div class="act-content">✅ {data['guide']['lucky']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_r:
                st.markdown(f"""
                <div class="glass-card action-card taboo-bg">
                    <div class="act-title">TABOO ACTION</div>
                    <div class="act-content">🚫 {data['guide']['taboo']}</div>
                </div>
                """, unsafe_allow_html=True)

            # 5. 锦囊与金句
            st.markdown(f"""
            <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                <p style="font-size: 16px; color: #F2C94C;">📜 <b>锦囊：</b>{data['advice']}</p>
                <p style="font-size: 14px; color: #aaa; font-style: italic;">“ {data['quote']} ”</p>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error("🌌 宇宙信号干扰，请重试...")
        st.error(f"Debug: {e}")
