import streamlit as st
import os
import json
import datetime
from google import genai
from google.genai import types

# ------- 页面配置 -------
st.set_page_config(
    page_title="八字能量色彩分析 | Powered by Gemini",
    page_icon="🎨",
    layout="wide"
)

# ------- 自定义 CSS -------
st.markdown("""
<style>
    .main { padding: 30px; }
    .card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        border: 1px solid #eee;
    }
    .big-button > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        font-weight: 600;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ------- 页面标题 -------
st.markdown("## 🎨 八字能量色彩分析（Gemini JSON Viewer）")
st.markdown("通过输入出生日期和提示模版，由 Gemini 自动返回结构化 JSON 预测结果。")

# ---------- 左侧输入栏 ----------
with st.sidebar:
    st.markdown("### 🧩 预测设置")

    dob = st.date_input("出生日期", datetime.date(1990, 1, 1))
    today = st.date_input("今天日期", datetime.date.today())

    model_choice = st.text_input("Gemini 模型（例如：gemini-2.5-flash）", "gemini-2.5-flash")

    api_key_input = st.text_input(
        "Gemini API Key（可不填，系统将使用环境变量）",
        type="password"
    )

    st.markdown("---")
    st.markdown("如结果未返回 JSON，请在 Prompt 中明确要求：**仅返回 JSON**。")

# 右侧主体区域
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 📝 输入提示（Prompt 模板）")
prompt_template = st.text_area(
    label="在这里输入你的 Prompt 模板，可使用 {dob} 与 {today} 占位符。",
    height=200
)
st.markdown("</div>", unsafe_allow_html=True)

# 运行按钮
st.markdown('<div class="card">', unsafe_allow_html=True)
run = st.container()
with run:
    st.markdown("### 🚀 开始分析")
    run_button = st.button("运行并调用 Gemini", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ---------- 执行 Gemini 调用 ----------
if run_button:
    final_prompt = prompt_template.replace("{dob}", str(dob)).replace("{today}", str(today))

    api_key = api_key_input if api_key_input else os.environ.get("GEMINI_API_KEY")

    if not api_key:
        st.error("❌ 你需要在环境变量或侧栏中填写 GEMINI API KEY。")
        st.stop()

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_choice,
            contents=final_prompt
        )

        # 尝试解析 JSON
        try:
            json_data = json.loads(response.text)
            st.success("✨ 成功解析 JSON！")
            st.json(json_data)
        except:
            st.warning("模型未返回 JSON，显示原始内容：")
            st.code(response.text)

    except Exception as e:
        st.error(f"调用 Gemini 出错：{e}")
