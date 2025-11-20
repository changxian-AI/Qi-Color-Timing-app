import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gemini 诊断模式", page_icon="🛠")
st.title("🛠 Gemini 账号诊断模式")

# 1. 输入 Key
api_key = st.text_input("请输入您的 API Key", type="password")

if st.button("开始诊断"):
    if not api_key:
        st.error("请先输入 Key")
        st.stop()
        
    # 2. 配置
    genai.configure(api_key=api_key)
    
    try:
        # 3. 检查 SDK 版本
        st.info(f"当前 SDK 版本: {genai.__version__}")
        
        # 4.以此 Key 向 Google 索要可用模型列表
        st.write("正在查询 Google 服务器...")
        
        available_models = []
        for m in genai.list_models():
            # 只列出支持“生成内容”的模型
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                st.success(f"✅ 发现可用模型: **{m.name}**")
        
        if not available_models:
            st.error("❌ 您的 Key 连接成功，但没有发现任何可用模型。可能是账号权限问题。")
        else:
            st.markdown("---")
            st.warning("请记下上面显示的某个模型名称（通常是 `models/gemini-1.5-flash`），这就是我们下一步要填入代码的准确名字。")
            
    except Exception as e:
        st.error(f"诊断失败，报错信息: {e}")
