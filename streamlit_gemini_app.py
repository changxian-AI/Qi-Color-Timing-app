import streamlit as st
import os
import json
import datetime
import google.generativeai as genai
import re

# ------- 1. 页面配置 -------
st.set_page_config(
    page_title="气色·职场能量日历",
    page_icon="🔮",
    layout="centered" # 手机端友好模式
)

# ------- 2. 核心逻辑：命理师的大脑 (System Instruction) -------
# 这就是我们要“写死”在代码里的核心算法，不需要用户看见
SYSTEM_PROMPT = """
Role: 你是一位精通中国传统八字命理（子平术）与现代色彩心理学、职场策略的资深咨询师。你的名字叫“气色主理人”。
Goal: 根据用户的【出生日期】和【今日日期】，排盘（简易版）并分析今日运势，提供穿搭和行为建议。

Logic Rules:
1. 基于用户生日推算日柱天干（日主）。
2. 分析日主与今日流日干支的关系（如：官杀日、食伤日、财星日等）。
3. 五行色彩建议：木(青/绿), 火(红/紫), 土(黄/褐), 金(白/金), 水(黑/蓝)。
4. 给出具体的职场建议（Golden Hours）。

Output Format:
请务必仅返回纯 JSON 格式，不要包含 markdown 符号（如 ```json ... ```），格式如下：
{
    "user_element": "辛金 (您的日主)",
    "day_energy": "今日是 乙巳年... (流日)",
    "lucky_color": {
        "main": "藏青色",
        "reason": "今日火旺，需水降温..."
    },
    "action_guide": {
        "lucky_time": "13:00-15:00",
        "advice": "适合找老板汇报..."
    },
    "quote": "一句简短的职场命理金句"
}
"""

# ------- 3. 界面设计 -------
st.title("🔮 气色·职场能量日历")
st.caption("硅谷高管都在用的玄学管理工具")

# 输入区
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("您的生日", datetime.date(1984, 8, 15))
    with col2:
        today = st.date_input("查看日期", datetime.date.today())
    
    # 这里的 Key 建议从环境变量取，如果没有就让用户填
    api_key = st.text_input("输入 Gemini API Key", type="password", help="在 aistudio.google.com 获取")

# 运行按钮
if st.button("✨ 生成今日指南", type="primary", use_container_width=True):
    
    if not api_key:
        st.error("请先输入 API Key！")
        st.stop()

    # ------- 4. 调用 AI -------
    try:
        genai.configure(api_key=api_key)
        # 注意：这里修正了模型名称，使用目前稳定免费的 1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner('正在连接宇宙能量场... (AI排盘中)'):
            # 拼接提示词
            final_user_prompt = f"{SYSTEM_PROMPT}\n\n用户生日：{dob}\n今日日期：{today}\n请生成JSON报告。"
            
            response = model.generate_content(final_user_prompt)
            text_res = response.text

            # ------- 5. 结果清洗 (防止 JSON 解析失败) -------
            # 有时候 AI 会返回 ```json ... ```，我们要把反引号去掉
            clean_json = re.sub(r"```json\s*|\s*```", "", text_res).strip()
            
            try:
                data = json.loads(clean_json)
                
                # ------- 6. 漂亮的 UI 展示 -------
                st.success("能量获取成功！")
                
                # 幸运色展示卡片
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid {data.get('lucky_color', {}).get('hex', '#333')};">
                    <h3>今日幸运色：{data['lucky_color']['main']}</h3>
                    <p><b>日主：</b>{data['user_element']} | <b>能量场：</b>{data['day_energy']}</p>
                    <p><i>💡 {data['lucky_color']['reason']}</i></p>
                </div>
                """, unsafe_allow_html=True)
                
                # 黄金时间 & 建议
                st.markdown("### ⚡️ 黄金行动指南")
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**⏰ 黄金时间**\n\n{data['action_guide']['lucky_time']}")
                with c2:
                    st.warning(f"**🛡 建议策略**\n\n{data['action_guide']['advice']}")
                
                # 金句
                st.markdown("---")
                st.markdown(f"**“{data['quote']}”**")
                
                # 调试模式（显示原始数据）
                with st.expander("查看原始 JSON 数据"):
                    st.json(data)

            except json.JSONDecodeError:
                st.error("AI 返回了非标准 JSON，请重试。")
                st.code(text_res) # 打印出来看看错哪了

    except Exception as e:
        st.error(f"发生错误: {e}")
        st.markdown("可能原因：\n1. API Key 不对\n2. 网络不通\n3. 模型名称写错了")
