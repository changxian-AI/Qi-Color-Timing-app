"""
Streamlit app: Gemini JSON viewer

Features:
- Input: user's birthday and today's date (date pickers)
- Textarea: paste your prepared prompt template. Use placeholders {dob} and {today} in the template.
- Calls Google Gemini via Python SDK (tries google.genai or google.generativeai). The app expects an env var GEMINI_API_KEY.
- Parses the model response as JSON (if the model returns JSON). Displays the raw JSON and a styled view:
  - shows color blocks when it finds hex colors in JSON under keys named 'color', 'colors' or similar
  - displays 'suggestions' or 'advice' arrays in a friendly card list

Run:
1) pip install streamlit google-genai (or google-generativeai) requests
2) export GEMINI_API_KEY="YOUR_KEY_HERE"  (or set in your environment on Windows accordingly)
3) streamlit run streamlit_gemini_app.py

Note: this script attempts to use the official SDK. If not available, it will raise a helpful error telling you what to install.

"""

import os
import json
import re
import streamlit as st
from datetime import date

st.set_page_config(page_title="Gemini JSON Viewer", layout="wide")

st.title("Gemini JSON Viewer — Streamlit")
st.caption("输入生日和日期，粘贴你的 Prompt（使用 {dob} 和 {today} 占位），调用 Google Gemini 并美观地展示返回的 JSON。")

# --- Sidebar inputs ---
st.sidebar.header("输入")
user_dob = st.sidebar.date_input("出生日期 (DOB)", value=date(1990,1,1))
user_today = st.sidebar.date_input("今天日期", value=date.today())
model_name = st.sidebar.text_input("Gemini 模型 (例如: gemini-2.5-flash)", value="gemini-2.5-flash")

st.sidebar.markdown("设置 GEMINI_API_KEY 环境变量或在下面输入（不推荐，把 key 放环境变量更安全）")
api_key_input = st.sidebar.text_input("GEMINI API KEY (optional)", type="password")

# --- Prompt template ---
st.subheader("Prompt 模板")
st.markdown("在这里粘贴你已经准备好的 Prompt 模板。使用占位符 {dob} 和 {today} 来自动替换。\n例如：\n`请以 JSON 格式返回：{\"suggestions\": [...], \"colors\": [\"#FF0000\"]}`")
prompt_template = st.text_area("Prompt 模板", height=200)

col1, col2 = st.columns([2,1])
with col2:
    run_button = st.button("运行并调用 Gemini")

# Helper: safe placeholder replacement
def fill_prompt(template: str, dob_value: date, today_value: date) -> str:
    return template.format(dob=dob_value.isoformat(), today=today_value.isoformat())

# Helper: extract color-like strings
HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")

def extract_colors_from_obj(obj):
    colors = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            colors += extract_colors_from_obj(v)
            if isinstance(v, str):
                colors += HEX_COLOR_RE.findall(v)
    elif isinstance(obj, list):
        for item in obj:
            colors += extract_colors_from_obj(item)
    elif isinstance(obj, str):
        colors += HEX_COLOR_RE.findall(obj)
    return list(dict.fromkeys(colors))

# Helper: find suggestions/advice
def extract_suggestions(obj):
    candidates = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if kl in ("suggestions", "advice", "tips", "recommendations") and isinstance(v, list):
                candidates += v
            else:
                candidates += extract_suggestions(v)
    elif isinstance(obj, list):
        for item in obj:
            candidates += extract_suggestions(item)
    return candidates

# Attempt to call Gemini
if run_button:
    if not prompt_template.strip():
        st.warning("请先在上方粘贴 Prompt 模板（包含 {dob} 和 {today} 占位符）")
    else:
        final_prompt = fill_prompt(prompt_template, user_dob, user_today)
        st.subheader("已发送的 Prompt")
        st.code(final_prompt, language="text")

        # Determine API key
        api_key = "PASTE_YOUR_GEMINI_API_KEY_HERE"  # ← 已替换为你的真实 KEY
        if not api_key:
            st.error("找不到 GEMINI API Key。请在侧边栏输入或设置环境变量 GEMINI_API_KEY。")
        else:
            with st.spinner("调用 Gemini 中…"):
                success = False
                response_text = None
                # Try using modern google-genai SDKs
                try:
                    # Try the newer google.genai client
                    from google import genai
                    client = genai.Client(api_key=api_key) if hasattr(genai, 'Client') else genai.Client()
                    # Some SDK variants use client.models.generate_content
                    if hasattr(client, 'models') and hasattr(client.models, 'generate_content'):
                        gen_resp = client.models.generate_content(model=model_name, contents=final_prompt)
                        # gen_resp may have .text or .response
                        response_text = getattr(gen_resp, 'text', None) or getattr(gen_resp, 'output', None) or json.dumps(gen_resp)
                        success = True
                    else:
                        raise RuntimeError("genai client missing expected method")
                except Exception:
                    try:
                        # Try google.generativeai (older package name)
                        import google.generativeai as genai2
                        # configure
                        if hasattr(genai2, 'configure'):
                            genai2.configure(api_key=api_key)
                        # some variants have generate_text
                        if hasattr(genai2, 'generate_text'):
                            gen_resp = genai2.generate_text(model=model_name, prompt=final_prompt)
                            response_text = getattr(gen_resp, 'text', None) or json.dumps(gen_resp)
                            success = True
                        else:
                            # some variants use client-like API
                            if hasattr(genai2, 'Client'):
                                client2 = genai2.Client()
                                gen_resp = client2.generate_text(model=model_name, prompt=final_prompt)
                                response_text = getattr(gen_resp, 'text', None) or json.dumps(gen_resp)
                                success = True
                            else:
                                raise RuntimeError("google.generativeai missing expected methods")
                    except Exception as e:
                        st.error(f"调用 SDK 时出现问题：{e}\n请确认已安装 google-genai 或 google-generativeai 并且 API key 有效。")

                if success and response_text:
                    st.success("收到模型响应（尝试解析为 JSON）")
                    # Try to parse JSON
                    parsed = None
                    try:
                        # If response_text is some object, ensure it's a string
                        if not isinstance(response_text, str):
                            response_text = json.dumps(response_text)
                        parsed = json.loads(response_text)
                    except Exception:
                        # The model sometimes returns text that *contains* JSON; try to extract the first JSON substring
                        json_search = re.search(r"(\{(?:.|\n)*\})", response_text)
                        if json_search:
                            try:
                                parsed = json.loads(json_search.group(1))
                            except Exception:
                                parsed = None

                    # Display raw response
                    st.subheader("原始响应 (text)")
                    st.code(response_text, language="json")

                    if parsed is None:
                        st.warning("未能将响应解析为 JSON。你也可以在 Prompt 中要求 'Respond in strict JSON' 来确保返回 JSON 格式。")
                    else:
                        st.subheader("解析后的 JSON")
                        st.json(parsed)

                        # color blocks
                        colors = extract_colors_from_obj(parsed)
                        if colors:
                            st.subheader("颜色块")
                            cols = st.columns(len(colors))
                            for c, hexc in zip(cols, colors):
                                with c:
                                    st.markdown(f"<div style='width:100%;padding:20px;border-radius:8px;text-align:center;background:{hexc};'>\n<b>{hexc}</b>\n</div>", unsafe_allow_html=True)

                        # suggestions
                        suggestions = extract_suggestions(parsed)
                        if suggestions:
                            st.subheader("建议 / 建议列表")
                            for i, s in enumerate(suggestions, start=1):
                                st.markdown(f"**{i}.** {s}")

                        # If JSON contains freeform text fields that look like advice, show them
                        if not suggestions:
                            # search common keys
                            for key in ("summary", "advice", "recommendation", "suggestion"):
                                if key in parsed and isinstance(parsed[key], (str, list)):
                                    st.subheader(f"{key} 内容")
                                    if isinstance(parsed[key], list):
                                        for idx, item in enumerate(parsed[key], start=1):
                                            st.markdown(f"- {item}")
                                    else:
                                        st.markdown(parsed[key])

                else:
                    st.error("调用失败或未收到可识别的文本响应。请检查 API Key、模型名称以及 SDK 安装。")

# End of app

# Footer notes
st.sidebar.markdown("---")
st.sidebar.markdown("**提示**: 如果模型没有返回 JSON，请在你的 Prompt 中明确要求 `Respond only in strict JSON` 或者提供一个 JSON Schema 示例。")
