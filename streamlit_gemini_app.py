import streamlit as st
import os
import json
import datetime
import re
import google.generativeai as genai

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·职场能量日历 (2025 Edition)",
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
        background-color: #8E44AD; /* 紫气东来色 */
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
SYSTEM_PROMPT = """
Role: 你是一位精通中国传统八字命理（子平术）与现代色彩心理学、职场策略的资深咨询师。你的名字叫“气色主理人”。
Goal: 根据用户的【出生日期】和【今日日期】，简易排盘并分析今日运势，提供穿搭和行为建议。

Logic Rules:
1. 基于用户生日推算日柱天干（日主）。
2. 分析日主与今日流日干支的关系（如：官杀日、食伤日、财星日等）。
3. 五行色彩建议：木(青/绿), 火(红/紫), 土(黄/褐/咖), 金(白/金/银), 水(黑/深蓝)。

Output Format:
请务必仅返回纯 JSON 格式，不要包含 markdown 符号，结构如下：
{
    "user_info": "您的日柱是 [日柱] (如: 辛金)",
    "lucky_color": {
        "main": "主要建议颜色",
        "hex": "#颜色代码",
        "reason": "命理解析原因..."
    },
    "action_guide": {
        "time": "黄金时辰 (如: 未时 13-15点)",
        "todo": "建议做的事"
    },
    "quote": "一句职场转运金句"
}
"""

# ------- 3. 界面逻辑 -------
st.title("🔮 气色·职场能量日历")
st.caption("Powered by Gemini 2.5 Flash (High Speed)")

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
    dob = st.date_input("您的生日", datetime.date(1984, 8, 15))
with col2:
    today = st.date_input("查看日期", datetime.date.today())

# 运行按钮
if st.button("🚀 获取 2025 能量指南"):
    
    if not api_key:
        st.error("❌ 请先配置 API Key")
        st.stop()

    try:
        # ------- 4. 调用 Google SDK -------
        genai.configure(api_key=api_key)
        
        # ★★★ 关键修正：使用您列表里存在的最新模型 ★★★
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        with st.spinner('正在连接 2025 宇宙能量场...'):
            # 构造提示词
            full_prompt = f"{SYSTEM_PROMPT}\n\n用户生日：{dob}\n今日日期：{today}\n请生成JSON报告。"
            
            # 发送请求
            response = model.generate_content(full_prompt)
            result_text = response.text

            # ------- 5. 数据清洗 -------
            clean_json = re.sub(r"```json\s*|\s*```", "", result_text).strip()
            
            try:
                data = json.loads(clean_json)
                
                # 展示成功结果
                st.success("✨ 分析完成")
                
                # 颜色卡片
                color = data.get('lucky_color', {}).get('hex', '#333')
                st.markdown(f"""
                <div class="card" style="border-left: 10px solid {color};">
                    <h3>👕 今日幸运色：{data.get('lucky_color', {}).get('main')}</h3>
                    <p class="highlight">{data.get('user_info')}</p>
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
                
            except json.JSONDecodeError:
                st.warning("AI 返回了非标准 JSON，但内容如下：")
                st.write(result_text)

    except Exception as e:
        st.error(f"运行出错: {e}")
        st.info("如果报错 404，请尝试改用 'gemini-flash-latest'，这是您列表里也存在的通用名。")
