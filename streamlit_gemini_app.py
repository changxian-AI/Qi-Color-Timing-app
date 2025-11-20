import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·能量日历 v1.5",
    page_icon="⚡️",
    layout="centered"
)

# ------- 自定义样式 (更潮一点) -------
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: 700;
        background: linear-gradient(90deg, #8E44AD 0%, #3498DB 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #eee;
    }
    .score-box {
        text-align: center;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 10px;
    }
    .score-num { font-size: 24px; font-weight: bold; display: block; }
    .score-label { font-size: 12px; color: #666; }
    .taboo { color: #e74c3c; font-weight: bold; }
    .lucky { color: #27ae60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ------- 2. 核心逻辑：命理师的大脑 (升级版) -------
SYSTEM_PROMPT = """
Role: 你是一位精通八字命理、擅长把握人性的“毒舌”运势顾问。
Goal: 基于用户日柱和流日，根据【当前是工作日还是周末】，提供极具洞察力的运势评分、穿搭建议和宜忌指南。

Logic Rules:
1. **场景判断：**
   - 若系统提示【工作日】：聚焦职场、效率、搞钱、防小人、向上管理。
   - 若系统提示【周末】：聚焦桃花、约会、家庭、休息、社死瞬间、吃喝玩乐。
2. **生克关系与建议：**
   - 官杀重：压力大，建议用“印”化解（穿生身之色，多睡觉/读书）。
   - 食伤重：想发泄，建议用“财”引流（搞钱/购物）或“印”克制（闭嘴）。
   - 财星重：欲望强，建议“比劫”帮身（找朋友/AA制）。
3. **评分系统：** 请给出 财运、事业(或桃花)、健康 三个维度的 1-5 星评分。

Output Format (Strict JSON):
{
    "user_info": "您的日柱: [日柱]",
    "scores": {
        "money": 4,  (1-5的整数)
        "career_love": 3, (工作日给事业分，周末给桃花分)
        "health": 5
    },
    "lucky_color": {
        "main": "建议颜色",
        "hex": "#颜色代码",
        "reason": "一针见血的理由"
    },
    "guide": {
        "lucky_act": "宜：做某事 (简短)",
        "taboo_act": "忌：做某事 (一定要具体，带点幽默或警告)",
        "advice": "给今日的具体建议 (工作日谈职场策略，周末谈情感/生活)"
    },
    "quote": "一句扎心的毒鸡汤"
}
"""

# ------- 3. 辅助函数 -------
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
    # Python中 0-4 是周一到周五，5-6 是周六周日
    weekday = date_obj.weekday()
    if weekday >= 5:
        return "周末 (Focus: 恋爱、休息、消费)", "桃花/心情"
    else:
        return "工作日 (Focus: 职场、效率、竞争)", "事业/学业"

# ------- 4. 界面逻辑 -------
st.title("⚡️ 气色·能量日历")
st.caption("Daily Energy Forecast (v1.5)")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ API Key 已加载")
    else:
        api_key = st.text_input("Gemini API Key", type="password")

# 输入区
col1, col2 = st.columns(2)
with col1:
    dob = st.date_input("🎂 您的生日", datetime.date(1984, 8, 25))
with col2:
    today = st.date_input("📅 查看日期", datetime.date.today())

# 运行按钮
if st.button("🚀 解锁今日能量"):
    
    if not api_key:
        st.error("❌ 请输入 API Key")
        st.stop()

    try:
        # 1. 算八字
        user_bazi = get_bazi_info(dob)
        today_bazi = get_bazi_info(today)
        
        # 2. 判断是周末还是工作日
        day_context, score_label_2 = get_day_type(today)

        # 3. 调用 AI
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') # 既然这个能用就用这个
        
        with st.spinner('正在下载宇宙信号...'):
            full_prompt = f"""
            {SYSTEM_PROMPT}
            
            【当前上下文 Context】
            1. 用户日柱：{user_bazi['day_gz']} (天干: {user_bazi['day_gan']})
            2. 今日日期：{today_bazi['year_gz']}年 {today_bazi['month_gz']}月 {today_bazi['day_gz']}日
            3. **特殊场景设定：{day_context}**
            
            请严格基于上述场景生成JSON。
            """
            
            response = model.generate_content(full_prompt)
            # 清洗 JSON
            clean_json = re.sub(r"```json\s*|\s*```", "", response.text).strip()
            data = json.loads(clean_json)

            # ------- 4. 结果展示 -------
            st.balloons() # 给点氛围感

            # 顶部：评分栏
            st.markdown("### 📊 今日能量值")
            s1, s2, s3 = st.columns(3)
            with s1:
                st.markdown(f"""<div class="score-box"><span class="score-num">{"⭐️" * data['scores']['money']}</span><span class="score-label">财运指数</span></div>""", unsafe_allow_html=True)
            with s2:
                st.markdown(f"""<div class="score-box"><span class="score-num">{"⭐️" * data['scores']['career_love']}</span><span class="score-label">{score_label_2}指数</span></div>""", unsafe_allow_html=True)
            with s3:
                st.markdown(f"""<div class="score-box"><span class="score-num">{"⭐️" * data['scores']['health']}</span><span class="score-label">身心指数</span></div>""", unsafe_allow_html=True)

            # 中部：幸运色卡片
            color = data.get('lucky_color', {}).get('hex', '#333')
            st.markdown(f"""
            <div class="card" style="border-left: 10px solid {color}; margin-top: 20px;">
                <h3>👕 今日OOTD：{data['lucky_color']['main']}</h3>
                <p style="color: #666; font-size: 14px;">{data['user_info']} vs {today_bazi['day_gz']}日</p>
                <p><i>{data['lucky_color']['reason']}</i></p>
            </div>
            """, unsafe_allow_html=True)

            # 下部：宜忌清单 (这是重点钩子)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div class="card" style="border-top: 5px solid #27ae60; text-align: center;">
                    <div class="lucky">✅ 宜</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 10px;">{data['guide']['lucky_act']}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="card" style="border-top: 5px solid #e74c3c; text-align: center;">
                    <div class="taboo">🚫 忌</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 10px;">{data['guide']['taboo_act']}</div>
                </div>
                """, unsafe_allow_html=True)

            # 底部：详细建议 & 金句
            st.info(f"💡 **{score_label_2.split('/')[0]}锦囊：** {data['guide']['advice']}")
            st.markdown(f"<div style='text-align: center; color: #999; margin-top: 20px;'>“ {data['quote']} ”</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error("AI 开小差了，请重试。")
        st.error(f"Error: {e}")
