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

# 初始化 Session State (用于切换页面)
if 'page' not in st.session_state:
    st.session_state.page = 'daily' # 默认显示日报
if 'bazi_report' not in st.session_state:
    st.session_state.bazi_report = None

# ------- 2. 赛博玄学 UI -------
st.markdown("""
<style>
    /* 全局背景：深空紫黑 */
    .stApp {
        background: linear-gradient(180deg, #0B0B15 0%, #1A1A2E 100%);
        color: #E0E0E0;
    }
    
    /* 按钮特效 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    
    /* 主要按钮 (紫色流光) */
    .primary-btn button {
        background: linear-gradient(90deg, #7928CA, #FF0080);
        color: white;
        box-shadow: 0 0 20px rgba(121, 40, 202, 0.4);
    }
    
    /* 次要按钮 (科技蓝) */
    .secondary-btn button {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
    }

    /* 日主图腾 (Hero Section) */
    .hero-card {
        text-align: center;
        padding: 30px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    .hero-icon { font-size: 60px; margin-bottom: 10px; display: block; }
    .hero-title { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
    .hero-subtitle { font-size: 14px; color: #aaa; }

    /* 锦囊 (重点突出) */
    .advice-box {
        background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%);
        color: #333;
        padding: 25px;
        border-radius: 15px;
        margin-top: 20px;
        position: relative;
        box-shadow: 0 10px 30px rgba(253, 185, 49, 0.3);
        border: 2px solid #FFF;
    }
    .advice-title { font-size: 16px; font-weight: bold; text-transform: uppercase; opacity: 0.8; margin-bottom: 8px; }
    .advice-content { font-size: 20px; font-weight: 900; line-height: 1.4; }
    
    /* 玻璃卡片 */
    .glass-card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ------- 3. Prompt 仓库 -------

# 日报 Prompt (轻量级)
DAILY_PROMPT = """
Role: 赛博命理师。
Goal: 输出JSON，包含四维评分、幸运色、黄金时辰、宜忌、锦囊。
Output Format (JSON):
{
    "day_master": {"gan": "甲", "element": "木", "trait": "参天大树，正直仁慈，宁折不弯"}, 
    "scores": {"money": 4, "career": 3, "love": 5, "energy": 3},
    "lucky_color": {"main": "色名", "hex": "#HEX", "reason": "理由"},
    "golden_hour": {"time": "时辰", "action": "宜做之事"},
    "guide": {"lucky": "宜...", "taboo": "忌..."},
    "advice": "一条极其精准、直击痛点的行动建议",
    "quote": "玄学金句"
}
"""

# 全盘分析 Prompt (重量级)
FULL_ANALYSIS_PROMPT = """
Role: 宗师级命理顾问。
Goal: 基于用户提供的出生时间（含城市），**自行推算真太阳时**，进行专业的八字排盘和深度分析。

Task:
1. **真太阳时修正：** 根据[出生城市]和[出生时间]，估算经度时差，修正为真太阳时排盘。
2. **排盘：** 输出年、月、日、时四柱。
3. **核心分析：**
   - **强弱格局：** 判断身强身弱，定格局。
   - **喜用神：** 明确指出最喜五行和最忌五行。
   - **性格画像：** 深度剖析优缺点。
   - **事业财运：** 适合行业、财富等级预测。
   - **婚姻感情：** 配偶特征、感情走势。

Output Format (Markdown):
请用优美的 Markdown 格式输出一份详尽的命理报告。
结构：
## 🌌 您的真太阳时命盘
**出生信息：** ... (修正后的时间)
**八字排盘：** 年[XX] 月[XX] 日[XX] 时[XX]

### 1. ⚔️ 命局总格
(分析强弱、格局、喜用神)

### 2. 🦁 性格深层解码
(详细分析)

### 3. 💰 事业与财富天机
(详细分析)

### 4. 💘 情感与婚姻
(详细分析)

### 🔮 宗师寄语
(给当下的人生建议)
"""

# ------- 4. 辅助逻辑 -------
def get_bazi_simple(date_obj):
    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
    lunar = solar.getLunar()
    return {
        "gan": lunar.getDayGan(),
        "zhi": lunar.getDayZhi(),
        "full": f"{lunar.getDayInGanZhi()}"
    }

def switch_page(page_name):
    st.session_state.page = page_name
    st.rerun()

# ------- 5. 主程序 -------

# 侧边栏
with st.sidebar:
    st.title("🧿 命运罗盘")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
    else:
        api_key = st.text_input("API Key", type="password")
    
    if st.button("🔄 重置/返回首页"):
        st.session_state.bazi_report = None
        switch_page('daily')

# ================= 页面 1: 今日能量 (Daily) =================
if st.session_state.page == 'daily':
    st.markdown("# 📅 今日能量场")
    
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("查看日期", datetime.date.today())

    # 这里的按钮用 primary 样式
    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    if st.button("⚡️ 开启今日运势"):
        if not api_key:
            st.error("请先配置 API Key")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在连接高维数据...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # ---- 1. 命主图腾 (Hero Section) ----
                dm = data['day_master']
                # 根据五行定颜色
                elem_colors = {"木": "#2ecc71", "火": "#e74c3c", "土": "#f1c40f", "金": "#ecf0f1", "水": "#3498db"}
                color = elem_colors.get(dm['element'], "#fff")
                
                st.markdown(f"""
                <div class="hero-card" style="border-top: 5px solid {color}; box-shadow: 0 0 30px {color}40;">
                    <span class="hero-icon" style="color: {color};">{dm['gan']}</span>
                    <div class="hero-title">您的本命：{dm['gan']}{dm['element']}</div>
                    <div class="hero-subtitle">日干代表最核心的自己</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 交互式性格解析
                with st.expander(f"🔮 点击查看【{dm['gan']}{dm['element']}】性格底色"):
                    st.info(f"**{dm['trait']}**")
                    st.markdown("日干决定了你最底层的思维方式和潜意识行为模式。了解日干，就是觉醒的第一步。")

                # ---- 2. 运势评分 ----
                st.markdown("### 📊 今日雷达")
                scores = data['scores']
                c1, c2, c3, c4 = st.columns(4)
                def show_score(col, label, val):
                    col.markdown(f"<div style='text-align:center; background:rgba(0,0,0,0.3); padding:10px; border-radius:8px;'><b>{label}</b><br><span style='color:#FFD700; font-size:18px;'>{'⚡'*val}</span></div>", unsafe_allow_html=True)
                
                show_score(c1, "财运", scores['money'])
                show_score(c2, "事业", scores['career'])
                show_score(c3, "桃花", scores['love'])
                show_score(c4, "能量", scores['energy'])
                
                # ---- 3. 锦囊 (重磅突出) ----
                st.markdown(f"""
                <div class="advice-box">
                    <div class="advice-title">✨ 宇宙锦囊 (Daily Wisdom)</div>
                    <div class="advice-content">{data['advice']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # ---- 4. 黄金时辰 & 宜忌 ----
                st.markdown("<br>", unsafe_allow_html=True)
                col_l, col_r = st.columns(2)
                with col_l:
                     st.success(f"**✅ 宜：** {data['guide']['lucky']}")
                with col_r:
                     st.error(f"**🚫 忌：** {data['guide']['taboo']}")
                
                st.info(f"⏳ **黄金时辰：** {data['golden_hour']['time']} —— {data['golden_hour']['action']}")
                
                # ---- 5. 导流入口 (Funnel Next Step) ----
                st.markdown("---")
                st.markdown("#### 想要更精准的命运解析？")
                st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                if st.button("🗝 解锁完整命盘 (含真太阳时校正) →"):
                    switch_page('full_analysis')
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)


# ================= 页面 2: 深度批命 (Full Analysis) =================
elif st.session_state.page == 'full_analysis':
    st.markdown("# 🗝 命运全息解码")
    st.caption("运用真太阳时排盘 · 宗师级AI深度批断")
    
    with st.container(border=True):
        st.subheader("完善出生信息")
        col1, col2 = st.columns(2)
        with col1:
            b_date = st.date_input("出生日期", datetime.date(1984, 8, 25))
        with col2:
            b_time = st.time_input("出生时间", datetime.time(12, 00))
        
        b_city = st.text_input("出生城市 (用于经纬度校正)", "例如：中国上海 / 加拿大多伦多")
        
        st.warning("⚠️ 注意：系统将根据您输入的城市，自动计算经度并修正为【真太阳时】进行精准排盘。")
        
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button("🚀 开始深度排盘"):
            if not b_city:
                st.error("请输入出生城市，否则无法校正真太阳时。")
                st.stop()
            
            if not api_key:
                st.error("请配置 API Key")
                st.stop()

            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                with st.spinner('正在进行天文计算与命理推演 (耗时约15秒)...'):
                    full_prompt = f"""
                    {FULL_ANALYSIS_PROMPT}
                    
                    【用户输入】
                    出生日期：{b_date}
                    出生时间：{b_time}
                    出生城市：{b_city}
                    """
                    
                    response = model.generate_content(full_prompt)
                    st.session_state.bazi_report = response.text
                    st.rerun() # 刷新页面显示报告

            except Exception as e:
                st.error(f"分析出错: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # 显示报告
    if st.session_state.bazi_report:
        st.markdown("---")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.bazi_report)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("📥 保存报告 (模拟)"):
            st.toast("报告已保存到云端 (Demo)")
