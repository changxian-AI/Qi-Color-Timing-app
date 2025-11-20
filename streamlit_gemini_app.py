import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·能量穿搭指南",
    page_icon="👗",
    layout="centered"
)

# 初始化 Session State
if 'page' not in st.session_state:
    st.session_state.page = 'daily'
if 'forecast_type' not in st.session_state:
    st.session_state.forecast_type = None # 'month' or 'year'
if 'forecast_result' not in st.session_state:
    st.session_state.forecast_result = None

# ------- 2. 时尚风格 UI (Fashion UI) -------
st.markdown("""
<style>
    /* 全局白底，字体深灰 */
    .stApp {
        background-color: #FFFFFF;
        color: #333;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 主按钮：渐变紫 */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 30px; /* 圆润时尚感 */
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3);
        transition: transform 0.2s;
    }
    div.stButton > button:hover { transform: scale(1.02); }

    /* 支付/解锁按钮 (金色系) */
    .premium-btn button {
        background: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%);
        color: #333;
        box-shadow: 0 4px 15px rgba(242, 201, 76, 0.3);
    }

    /* --- 核心组件：OOTD Hero Card (杂志封面风) --- */
    .ootd-card {
        background: #fff;
        border-radius: 16px;
        padding: 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        overflow: hidden;
        border: 1px solid #eee;
    }
    .ootd-header {
        background: #F8F9FA;
        padding: 15px 20px;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .ootd-body {
        padding: 25px;
        display: flex;
        align-items: center;
    }
    .color-swatch {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-right: 20px;
        flex-shrink: 0;
        border: 3px solid #fff;
    }
    .ootd-details {
        flex-grow: 1;
    }
    .ootd-title { font-size: 22px; font-weight: 800; color: #333; margin-bottom: 8px; }
    .ootd-desc { color: #555; font-size: 15px; line-height: 1.6; }
    .ootd-tags { margin-top: 10px; }
    .tag { 
        background: #eee; color: #555; padding: 4px 10px; 
        border-radius: 4px; font-size: 12px; margin-right: 5px; display: inline-block;
    }

    /* 能量对撞条 (简约版) */
    .energy-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #F4F6F7;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 20px;
        font-size: 13px;
        color: #666;
    }
    
    /* 宫格布局 */
    .grid-item {
        background: #FAFAFA;
        padding: 15px;
        border-radius: 12px;
        height: 100%;
        border: 1px solid #eee;
    }
    
    /* 标题 */
    h3 { font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #333; }

</style>
""", unsafe_allow_html=True)

# ------- 3. 逻辑部分 -------

# OOTD 强化版 Prompt
DAILY_PROMPT = """
Role: 顶级时尚穿搭顾问 & 命理师。
Goal: 基于【日柱生克】+【天气】+【场景】，输出 OOTD 建议。

Logic:
1. **能量计算：** 分析日主与今日干支的关系（如：财旺需比劫，印旺需食伤）。
2. **天气结合：** 
   - 晴天：推荐透气、亮色。
   - 雨/雪：推荐防水材质、靴子、深色防脏。
   - 阴/风：推荐风衣、叠穿。
3. **穿搭建议 (OOTD)：** 必须包含【主色】、【单品名】、【材质】、【配饰】。

Output Format (Strict JSON):
{
    "energy_analysis": "今日金水旺，您是木命，水多木漂，需土制水（黄色/卡其色）或火暖局...",
    "lucky_color": {"main": "卡其色", "hex": "#F0E68C"},
    "ootd": {
        "title": "卡其色风衣 · 稳重气场",
        "items": ["卡其色防水风衣", "深棕色羊毛衫", "切尔西靴"],
        "style_desc": "今日雨水偏多，五行水旺。建议外穿防水材质的风衣（土克水），内搭保暖羊毛。既实用又符合命理开运逻辑。",
        "tags": ["防水", "英伦风", "土系能量"]
    },
    "scores": {"money": 4, "love": 3, "energy": 3},
    "golden_hour": "13:00-15:00 (未时)",
    "guide": {"lucky": "整理工位", "taboo": "穿白色鞋子(易脏/泄气)"}
}
"""

# 运势预测 Prompt
FORECAST_PROMPT = """
Role: 资深命理分析师。
Goal: 生成【本月】或【本年】的运势预测。
Input: 用户八字、预测周期（月/年）。
Output: 清晰的 Markdown，包含：
1. 核心关键词（如：动荡、桃花、破财）。
2. 事业/财运/感情/健康 四维深度解析。
3. 重点月份/日期提醒。
"""

def get_bazi_simple(date_obj):
    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
    lunar = solar.getLunar()
    return {"full": f"{lunar.getDayInGanZhi()}", "gan": lunar.getDayGan()}

def switch_page(page_name, f_type=None):
    st.session_state.page = page_name
    if f_type:
        st.session_state.forecast_type = f_type
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
        st.session_state.forecast_result = None
        switch_page('daily')

# ================= 页面 1: 首页 (OOTD) =================
if st.session_state.page == 'daily':
    st.title("气色 · 能量穿搭指南")
    st.caption("Based on Bazi & Weather")
    
    # 输入区
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
    with col2:
        today = st.date_input("出行日期", datetime.date.today())
    with col3:
        weather = st.selectbox("天气", ["☀️ 晴朗", "☁️ 多云", "🌧️ 下雨", "❄️ 下雪", "💨 大风"])
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("👗 生成今日穿搭"):
        if not api_key:
            st.error("请配置 API Key")
            st.stop()
            
        user_bazi = get_bazi_simple(dob)
        today_bazi = get_bazi_simple(today)
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在匹配五行与天气数据...'):
                prompt = f"""
                {DAILY_PROMPT}
                用户日柱：{user_bazi['full']}
                今日流日：{today_bazi['full']}
                今日天气：{weather}
                """
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                st.markdown("<br>", unsafe_allow_html=True)

                # ---- 1. 能量分析条 ----
                st.markdown(f"""
                <div class="energy-bar">
                    <span>👤 <b>我 ({user_bazi['gan']})</b></span>
                    <span style="font-size:10px;">VS</span>
                    <span>📅 <b>今日 ({today_bazi['full']})</b></span>
                    <span style="color:#333; font-weight:bold;">{data['energy_analysis'][:20]}...</span>
                </div>
                """, unsafe_allow_html=True)

                # ---- 2. OOTD Hero Card (核心亮点) ----
                ootd = data['ootd']
                color = data['lucky_color']
                tags_html = "".join([f'<span class="tag">#{t}</span>' for t in ootd['tags']])
                
                st.markdown(f"""
                <div class="ootd-card">
                    <div class="ootd-header">
                        <span style="font-weight:bold; color:#666;">⚡ 今日能量战袍</span>
                        <span style="font-size:14px;">{weather}</span>
                    </div>
                    <div class="ootd-body">
                        <div class="color-swatch" style="background-color: {color['hex']};"></div>
                        <div class="ootd-details">
                            <div class="ootd-title">{ootd['title']}</div>
                            <div class="ootd-desc">{ootd['style_desc']}</div>
                            <div style="margin-top:10px; font-size:14px;">
                                <b>推荐单品：</b> {", ".join(ootd['items'])}
                            </div>
                            <div class="ootd-tags">
                                {tags_html}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ---- 3. 辅助信息 (宫格布局) ----
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"""
                    <div class="grid-item" style="background:#E3F2FD; color:#1565C0; text-align:center;">
                        <div style="font-size:12px; opacity:0.8;">黄金时辰</div>
                        <div style="font-weight:bold; margin-top:5px;">{data['golden_hour'].split(' ')[0]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="grid-item" style="background:#E8F5E9; color:#2E7D32; text-align:center;">
                        <div style="font-size:12px; opacity:0.8;">宜</div>
                        <div style="font-weight:bold; margin-top:5px;">{data['guide']['lucky']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class="grid-item" style="background:#FFEBEE; color:#C62828; text-align:center;">
                        <div style="font-size:12px; opacity:0.8;">忌</div>
                        <div style="font-weight:bold; margin-top:5px;">{data['guide']['taboo']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # ---- 4. 付费/高级功能钩子 (Funnel) ----
                st.markdown("---")
                st.markdown("### 🔓 解锁更多运势")
                
                col_m, col_y = st.columns(2)
                
                # 模拟付费按钮
                with col_m:
                    st.markdown('<div class="premium-btn">', unsafe_allow_html=True)
                    if st.button("📅 查看本月运势 (Premium)"):
                         switch_page('forecast', 'month')
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                with col_y:
                    st.markdown('<div class="premium-btn">', unsafe_allow_html=True)
                    if st.button("📜 查看2025流年 (Premium)"):
                         switch_page('forecast', 'year')
                    st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"连接中断: {e}")

# ================= 页面 2: 运势预测 (Premium Mockup) =================
elif st.session_state.page == 'forecast':
    f_type = st.session_state.forecast_type
    title = "本月流月运势" if f_type == 'month' else "2025 流年运势"
    
    st.title(f"🔒 {title}")
    st.caption("深度命理推演 · 付费专享内容")
    
    # 输入再次确认
    st.markdown('<div class="grid-item">', unsafe_allow_html=True)
    dob = st.date_input("确认您的生日", datetime.date(1984, 8, 25))
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 这里可以加一个模拟的“支付墙”或者直接生成
    if st.button(f"🚀 开始推演 {title}"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('正在排布命盘与大运流年...'):
                prompt = f"""
                {FORECAST_PROMPT}
                预测类型：{title}
                用户生日：{dob}
                """
                response = model.generate_content(prompt)
                st.session_state.forecast_result = response.text
                st.rerun()
        except Exception as e:
            st.error(f"推演失败: {e}")

    if st.session_state.forecast_result:
        st.markdown("---")
        st.markdown('<div class="grid-item" style="background:#fff;">', unsafe_allow_html=True)
        st.markdown(st.session_state.forecast_result)
        st.markdown('</div>', unsafe_allow_html=True)
