import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·每日运程深度版",
    page_icon="📜",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'

# ------- 2. 杂志风 UI (高可读性) -------
st.markdown("""
<style>
    /* 全局排版优化 */
    .stApp {
        background-color: #FAFAFA; /* 极淡灰，护眼 */
        color: #333;
        font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }

    /* 标题增强 */
    h1, h2, h3 { color: #2C3E50; font-weight: 700; }
    
    /* 按钮：渐变蓝紫 */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 14px 24px;
        border-radius: 8px;
        font-size: 17px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(118, 75, 162, 0.25);
        transition: all 0.2s;
    }
    div.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(118, 75, 162, 0.35); }

    /* --- 核心组件：今日定调 Hero Card --- */
    .hero-card {
        background: #FFF;
        border-radius: 12px;
        padding: 25px;
        border-left: 6px solid #764ba2;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .day-score { font-size: 36px; font-weight: 900; color: #764ba2; line-height: 1; }
    .day-summary { font-size: 20px; font-weight: bold; color: #333; margin-bottom: 5px; }
    .day-bazi { color: #888; font-size: 14px; letter-spacing: 1px; }

    /* --- 内容区块：深度解读 --- */
    .section-title {
        font-size: 18px;
        font-weight: bold;
        color: #333;
        margin: 25px 0 15px 0;
        display: flex;
        align-items: center;
    }
    .section-icon { margin-right: 8px; font-size: 20px; }
    
    .content-card {
        background: #FFF;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #EEE;
        margin-bottom: 15px;
        line-height: 1.6; /* 增加行高，提升可读性 */
        font-size: 15px;
        color: #444;
    }
    .keyword-tag {
        background: #F3F4F6;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        color: #555;
        margin-right: 5px;
    }

    /* OOTD 卡片 */
    .ootd-box {
        background: linear-gradient(to right, #fff, #f9f9f9);
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        display: flex;
        align-items: center;
    }
    .color-circle {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-right: 15px;
        flex-shrink: 0;
        border: 2px solid #fff;
    }

    /* 宜忌胶囊 */
    .capsule-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .capsule { flex: 1; padding: 12px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 15px; }
    .capsule-green { background: #E8F5E9; color: #2E7D32; }
    .capsule-red { background: #FFEBEE; color: #C62828; }

</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑与 Prompt (增强版) -------

# Prompt: 要求输出深度解读，而不仅仅是标签
DAILY_PROMPT = """
Role: 资深命理咨询师。
Goal: 生成一份**有深度、有温度、有逻辑**的今日运势分析。
Input: 用户八字、流日、天气。

Logic Requirements:
1. **今日定调**：给今天一个核心定义（如：财星破印·谨慎投资）。并给出一个综合评分（0-100）。
2. **五行穿搭**：结合天气和五行，给出具体的穿搭建议和理由。
3. **三大运势深度解**：
   - **事业**：分析机会点与风险点。
   - **财运**：正财还是偏财？有无破财风险？
   - **感情/人际**：桃花如何？是否容易口舌？
   - *要求：每个维度写 2-3 句具体分析，不要只给分数。*
4. **具体建议**：黄金时辰 + 宜忌 + 锦囊。

Output Format (Strict JSON):
{
    "user": {"gan": "辛", "element": "金"},
    "today": {"ganzhi": "甲午", "relation": "正财坐杀"},
    "summary": {
        "score": 85,
        "title": "财官双美 · 机遇与压力并存",
        "desc": "今日金木交战，财星滋杀。虽然机会很多，但压力也随之而来，适合迎难而上。"
    },
    "ootd": {
        "main_color": "白色",
        "hex": "#FFFFFF",
        "item": "白衬衫配深蓝西裤",
        "reason": "今日木火太旺，耗泄日主。穿白色（金）帮身，深蓝（水）调候，平衡燥气。"
    },
    "analysis": {
        "career": {"score": 4, "keywords": ["晋升", "压力"], "content": "官杀星当令，职场上容易受到领导关注，有机会承担重要任务。但工作量会激增，需注意情绪管理。"},
        "wealth": {"score": 5, "keywords": ["正财", "理财"], "content": "正财运极佳，适合谈薪资、做稳健型投资决策。但不宜进行高风险投机，容易财来财去。"},
        "love": {"score": 3, "keywords": ["争执", "包容"], "content": "由于压力较大，容易把工作情绪带回家。伴侣间可能因琐事拌嘴，建议多做倾听者。"}
    },
    "guide": {
        "golden_hour": "巳时 (09:00-11:00)",
        "lucky": "汇报工作、整理账目",
        "taboo": "冲动辞职、借钱给他人",
        "advice": "忙碌是好事，但不要让焦虑吞噬了你的判断力。保持呼吸节奏。"
    }
}
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
        st.success("✅ 密钥已加载")
    else:
        api_key = st.text_input("输入 API Key", type="password")
    st.markdown("---")
    if st.button("🏠 返回首页"):
        switch_page('daily')

# 页面逻辑
if st.session_state.page == 'daily':
    st.title("📜 气色 · 每日运程")
    st.caption("深度命理推演 v6.0")
    
    # 输入区 (紧凑排列)
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("预测日期", datetime.date.today())
    with col3:
        weather = st.selectbox("天气", ["☀️晴", "☁️阴", "🌧️雨", "❄️雪"])
        
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀 解读今日运势"):
        if not api_key:
            st.error("请配置 API Key")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('大师正在详批...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                今日天气：{weather}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                st.markdown("<br>", unsafe_allow_html=True)

                # ---- 1. 今日定调 (Hero Section) ----
                summ = data['summary']
                st.markdown(f"""
                <div class="hero-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div class="day-summary">{summ['title']}</div>
                            <div class="day-bazi">
                                我：{data['user']['gan']} ({data['user']['element']}) &nbsp;|&nbsp; 
                                日：{data['today']['ganzhi']} ({data['today']['relation']})
                            </div>
                        </div>
                        <div class="day-score">{summ['score']}</div>
                    </div>
                    <div style="margin-top:15px; color:#555; line-height:1.5; border-top:1px solid #eee; padding-top:10px;">
                        {summ['desc']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ---- 2. OOTD (带天气) ----
                st.markdown('<div class="section-title"><span class="section-icon">👗</span> 气色穿搭指南</div>', unsafe_allow_html=True)
                ootd = data['ootd']
                st.markdown(f"""
                <div class="ootd-box">
                    <div class="color-circle" style="background-color:{ootd['hex']};"></div>
                    <div>
                        <div style="font-weight:bold; font-size:18px; margin-bottom:5px;">{ootd['main_color']} · {ootd['item']}</div>
                        <div style="color:#666; font-size:14px; line-height:1.5;">{ootd['reason']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ---- 3. 三大运势深度解 (核心干货) ----
                # 事业
                car = data['analysis']['career']
                st.markdown('<div class="section-title"><span class="section-icon">💼</span> 事业运势</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="content-card">
                    <div style="margin-bottom:8px;">
                        {''.join([f'<span class="keyword-tag">{k}</span>' for k in car['keywords']])}
                        <span style="float:right; color:#FBC02D;">{'★' * car['score']}</span>
                    </div>
                    {car['content']}
                </div>
                """, unsafe_allow_html=True)

                # 财运
                wlth = data['analysis']['wealth']
                st.markdown('<div class="section-title"><span class="section-icon">💰</span> 财富运势</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="content-card">
                    <div style="margin-bottom:8px;">
                        {''.join([f'<span class="keyword-tag">{k}</span>' for k in wlth['keywords']])}
                        <span style="float:right; color:#FBC02D;">{'★' * wlth['score']}</span>
                    </div>
                    {wlth['content']}
                </div>
                """, unsafe_allow_html=True)

                # 感情
                love = data['analysis']['love']
                st.markdown('<div class="section-title"><span class="section-icon">🌸</span> 感情人际</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="content-card">
                    <div style="margin-bottom:8px;">
                        {''.join([f'<span class="keyword-tag">{k}</span>' for k in love['keywords']])}
                        <span style="float:right; color:#FBC02D;">{'★' * love['score']}</span>
                    </div>
                    {love['content']}
                </div>
                """, unsafe_allow_html=True)

                # ---- 4. 每日必做 ----
                st.markdown('<div class="section-title"><span class="section-icon">⚡</span> 行动清单</div>', unsafe_allow_html=True)
                gd = data['guide']
                
                # 黄金时辰
                st.info(f"**⏰ 黄金时辰：{gd['golden_hour']}**")

                # 宜忌
                st.markdown(f"""
                <div class="capsule-container">
                    <div class="capsule capsule-green">✅ 宜：{gd['lucky']}</div>
                    <div class="capsule capsule-red">🚫 忌：{gd['taboo']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 锦囊
                st.markdown(f"""
                <div style="background:#FFF8E1; padding:15px; border-radius:8px; border:1px solid #FFECB3; color:#5D4037; text-align:center; margin-top:10px;">
                    <b>💡 锦囊：</b>{gd['advice']}
                </div>
                """, unsafe_allow_html=True)
                
                # ---- 5. 变现钩子 ----
                st.markdown("---")
                st.markdown("#### 📅 规划未来")
                col_m, col_y = st.columns(2)
                with col_m:
                    st.button("🔓 解锁本月运势 (Pro)")
                with col_y:
                    st.button("📜 解锁2025流年 (Pro)")

        except Exception as e:
            st.error(f"连接中断: {e}")
