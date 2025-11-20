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

# ------- 2. 经典清爽 UI (复刻截图风格) -------
st.markdown("""
<style>
    /* 按钮样式：紫色渐变，圆角 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        background: linear-gradient(90deg, #8E2DE2, #4A00E0); /* 紫色渐变 */
        color: white;
        border: none;
    }
    
    /* 幸运色大卡片：浅灰背景 */
    .main-card {
        background-color: #f8f9fa;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        margin-bottom: 25px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 时间盒子：浅蓝背景 */
    .time-box {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        display: flex;
        align-items: center;
        height: 100%;
    }
    
    /* 建议盒子：浅绿背景 */
    .advice-box {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        height: 100%;
        font-size: 15px;
    }
    
    /* 标题强调 */
    .card-title {
        font-size: 22px;
        font-weight: bold;
        color: #333;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
    }
    
    /* 小标签 */
    .sub-label {
        color: #666;
        font-size: 14px;
        margin-bottom: 15px;
        font-weight: 500;
    }
    
    /* 金句 */
    .quote-text {
        text-align: center;
        color: #555;
        font-size: 18px;
        font-style: italic;
        font-weight: bold;
        margin-top: 30px;
        font-family: "Georgia", serif;
    }
</style>
""", unsafe_allow_html=True)

# ------- 3. 核心逻辑：Prompt (职场/现代风格) -------
SYSTEM_PROMPT = """
Role: 你是一位精通八字命理的现代职场策略顾问。
Goal: 基于用户日柱和流日，提供精准的幸运色、黄金时辰及行动指南。

Logic Rules:
1. **分析逻辑：** 基于日主与流日的生克关系（如：财旺累身，需比劫帮身）。
2. **语言风格：** 专业、理性、现代、干练。不要神神叨叨。
3. **内容要求：**
   - 幸运色：必须给出明确颜色。
   - 理由：解释五行生克原理（如：今日火旺，建议用水降温）。
   - 黄金时辰：具体的时间段（如：申时 15-17点）。
   - 建议：具体的职场或生活建议。

Output Format (Strict JSON):
{
    "user_bazi_str": "辛卯", 
    "today_bazi_str": "甲午日",
    "lucky_color": "白色",
    "lucky_reason": "今日流日天干甲木是用户日主辛金的正财，财星较旺，容易耗损自身能量。建议穿着白色（五行属金）来帮身助运，增强日主力量以驾驭财星，求得平衡。",
    "golden_time": "申时 15-17点",
    "action_advice": "积极拓展人脉，与志同道合的同事或朋友进行深度交流，共同探讨项目或寻求合作，集思广益，互相支持。",
    "quote": "合作是力量的源泉，团结才能成就更大的财富。"
}
"""

# ------- 4. 辅助函数 -------
def get_bazi_simple(date_obj):
    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
    lunar = solar.getLunar()
    return {"full": f"{lunar.getDayInGanZhi()}", "gan": lunar.getDayGan()}

# ------- 5. 页面构建 -------
st.title("🔮 气色·职场能量日历")
st.caption("Powered by Gemini 2.5 + LunarPython (精准排盘)")

# 侧边栏设置
with st.sidebar:
    st.header("⚙️ 设置")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ API Key 已加载")
    else:
        api_key = st.text_input("请输入 Gemini API Key", type="password")

# 输入区 (使用 Streamlit 原生列布局，清爽干净)
col1, col2 = st.columns(2)
with col1:
    dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
with col2:
    today = st.date_input("查看日期", datetime.date.today())

st.markdown("<br>", unsafe_allow_html=True)

# 运行按钮
if st.button("🚀 获取能量指南"):
    
    if not api_key:
        st.error("❌ 请先配置 API Key")
        st.stop()

    try:
        # 1. Python 算命 (精准排盘)
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        # 2. AI 分析
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        with st.spinner('正在分析五行磁场...'):
            prompt = f"""
            {SYSTEM_PROMPT}
            用户日柱：{user_bazi['full']}
            今日流日：{today_bazi['full']}
            """
            
            # 强制 JSON 输出，保证稳定
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            
            # ------- 结果展示 (复刻截图 UI) -------
            
            # 成功提示条
            st.success("✨ 排盘准确，分析完成")
            
            # 1. 幸运色大卡片
            st.markdown(f"""
            <div class="main-card">
                <div class="card-title">
                    👕 今日幸运色：{data['lucky_color']}
                </div>
                <div class="sub-label">
                    您的日柱：{data['user_bazi_str']} | 今日气场：{data['today_bazi_str']}
                </div>
                <div style="line-height: 1.6; color: #333;">
                    {data['lucky_reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. 行动指南标题
            st.markdown("### ⚡ 行动指南")
            
            # 3. 左右分栏建议
            c1, c2 = st.columns([1, 2]) # 左1右2比例，视觉更协调
            
            with c1:
                st.markdown(f"""
                <div class="time-box">
                    ⏰ {data['golden_time']}
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                st.markdown(f"""
                <div class="advice-box">
                    🛡 {data['action_advice']}
                </div>
                """, unsafe_allow_html=True)
            
            # 4. 底部金句
            st.markdown("---")
            st.markdown(f"""
            <div class="quote-text">
                “{data['quote']}”
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"运行出错: {e}")
