import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai
# 引入专业的历法库
from lunar_python import Solar

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·职场能量日历 (Pro)",
    page_icon="🔮",
    layout="centered"
)

# ------- 自定义样式 -------
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        background-color: #8E44AD;
        color: white;
    }
    .card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .highlight {
        color: #8E44AD;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ------- 2. 核心逻辑：命理师的大脑 -------
# 注意：这里的逻辑规则微调了，告诉AI“不要自己算，用我给你的数据”
SYSTEM_PROMPT = """
Role: 你是一位精通中国传统八字命理（子平术）与现代色彩心理学、职场策略的资深咨询师。你的名字叫“气色主理人”。
Goal: 根据系统提供的【用户日柱】和【今日流日】，分析今日运势，提供穿搭和行为建议。

Logic Rules:
1. **绝对信任系统传入的日柱信息，不要自己重新推算日期。**
2. 分析日主（用户日柱的天干）与今日流日干支的关系：
   - 官杀重（克身）：建议印星色（化煞）。
   - 食伤重（泄身）：建议财星色（生财）或印星色（制伤）。
   - 财星重（耗身）：建议比劫色（帮身）。
   - 印星重（生身）：建议财星色（坏印）或食伤色（泄秀）。
   - 比劫重（同身）：建议食伤色（通关）或官杀色（制劫）。
3. 五行色彩映射：
   - 木: 青/绿
   - 火: 红/紫/粉
   - 土: 黄/褐/咖/米
   - 金: 白/金/银/灰
   - 水: 黑/深蓝/墨绿

Output Format:
请务必仅返回纯 JSON 格式，不要包含 markdown 符号，结构如下：
{
    "lucky_color": {
        "main": "建议颜色",
        "hex": "#颜色代码",
        "reason": "命理解析原因 (例如: 今日丙火克辛金，官杀太重，建议穿黄色(土)来通关...)"
    },
    "action_guide": {
        "time": "黄金时辰 (如: 未时 13-15点)",
        "todo": "建议做的事"
    },
    "quote": "一句职场转运金句"
}
"""

# ------- 3. 辅助函数：Python 算命 (硬逻辑) -------
def get_bazi_info(date_obj):
    # 将公历转为 Solar 对象
    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
    #以此获取农历(Lunar)对象，因为八字是基于农历/节气的
    lunar = solar.getLunar()
    
    return {
        "year_gz": lunar.getYearInGanZhi(),
        "month_gz": lunar.getMonthInGanZhi(),
        "day_gz": lunar.getDayInGanZhi(),  # 这里就是准确的日柱，比如 "辛卯"
        "day_gan": lunar.getDayGan(),      # 日干，比如 "辛"
        "day_zhi": lunar.getDayZhi(),      # 日支，比如 "卯"
        "wuxing": lunar.getDayNaYin()      # 纳音，可选
    }

# ------- 4. 界面逻辑 -------
st.title("🔮 气色·职场能量日历")
st.caption("Powered by Gemini 2.5 + LunarPython (精准排盘)")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ API Key 已加载")
    else:
        api_key = st.text_input("请输入 Gemini API Key", type="password")

# 主界面输入
col1, col2 = st.columns(2)
with col1:
    # 默认值设为您的生日 1984-08-25
    dob = st.date_input("您的生日", datetime.date(1984, 8, 25))
with col2:
    today = st.date_input("查看日期", datetime.date.today())

# 运行按钮
if st.button("🚀 获取能量指南"):
    
    if not api_key:
        st.error("❌ 请先配置 API Key")
        st.stop()

    # --- 关键步骤：先用 Python 算出准确的八字 ---
    try:
        user_bazi = get_bazi_info(dob)
        today_bazi = get_bazi_info(today)
        
        # 构造显示用的字符串
        user_info_str = f"{user_bazi['day_gz']} ({user_bazi['day_gan']}木/火/土/金/水...)" # 这里偷懒了没写五行映射，交给AI判断
        today_info_str = f"{today_bazi['year_gz']}年 {today_bazi['month_gz']}月 {today_bazi['day_gz']}日"

        # --- 调用 AI ---
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        with st.spinner(f'正在分析：您是【{user_bazi["day_gz"]}】人，遇上【{today_bazi["day_gz"]}】日...'):
            
            # 构造极其明确的 Prompt
            full_prompt = f"""
            {SYSTEM_PROMPT}

            【关键数据 - 请严格基于此分析】
            1. 用户日柱（Day Pillar）：{user_bazi['day_gz']} (天干：{user_bazi['day_gan']})
            2. 今日日期（Date）：{today_bazi['year_gz']}年 {today_bazi['month_gz']}月 {today_bazi['day_gz']}日
            
            请生成JSON报告。
            """
            
            response = model.generate_content(full_prompt)
            result_text = response.text
            clean_json = re.sub(r"```json\s*|\s*```", "", result_text).strip()
            
            data = json.loads(clean_json)
            
            # ------- 结果展示 -------
            st.success("✨ 排盘准确，分析完成")
            
            # 颜色卡片
            color = data.get('lucky_color', {}).get('hex', '#333')
            st.markdown(f"""
            <div class="card" style="border-left: 10px solid {color};">
                <h3>👕 今日幸运色：{data.get('lucky_color', {}).get('main')}</h3>
                <p><b>您的日柱：</b> {user_bazi['day_gz']} | <b>今日气场：</b> {today_bazi['day_gz']}日</p>
                <p>{data.get('lucky_color', {}).get('reason')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 建议卡片
            st.markdown("### ⚡️ 行动指南")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"⏰ **{data.get('action_guide', {}).get('time')}**")
            with c2:
                st.success(f"🛡 **{data.get('action_guide', {}).get('todo')}**")
            
            # 金句
            st.markdown("---")
            st.markdown(f"#### *“{data.get('quote')}”*")

    except Exception as e:
        st.error(f"运行出错: {e}")
        st.warning("请检查 requirements.txt 是否包含了 `lunar_python`")
