import os
import io
import sys
import ast
import json
import streamlit as st
from streamlit_chat import message
from openai import OpenAI
from dotenv import load_dotenv
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

load_dotenv()
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

LOG_DIR = "conversation_logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

st.set_page_config(page_title="Python Code Error Checker", page_icon="🐍")
st.markdown("<h1 style='text-align: center;'>Python Code Error Checker</h1>", unsafe_allow_html=True)

def safe_exec(code):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    
    env = {
        'input': lambda _: '123',  
        'print': lambda *args, **kwargs: None,  
    }
    
    try:
        with redirect_stdout(redirected_output):
            with redirect_stderr(redirected_error):
                exec(code, env)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    return redirected_error.getvalue()

def analyze_code(code):
    try:

        ast.parse(code)

        error_output = safe_exec(code)
        if error_output:
            return f"Mantıksal hata: {error_output.strip()}"
        return "Kod sözdizimi ve mantık açısından doğru görünüyor."
    except SyntaxError as e:
        return f"Sözdizimi hatası: {str(e)}"
    except Exception as e:
        return f"Beklenmeyen hata: {str(e)}"

def get_openai_suggestion(code, error):
    prompt = f"""Aşağıdaki Python kodu bir hata içeriyor:

{code}

Hata mesajı:
{error}

Lütfen bu hatayı açıklayın, nedenini belirtin ve nasıl düzeltileceğini gösterin."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[
            {"role": "system", "content": "Sen deneyimli bir Python programcısısın. Kod hatalarını tespit edip düzeltmede uzmansın."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

def code_error_agent(code):
    error = analyze_code(code)
    
    if "hata" in error.lower():
        suggestion = get_openai_suggestion(code, error)
        return f"Hata: {error}\n\nÇözüm önerisi:\n{suggestion}"
    else:
        return error

def save_conversation_log(user_responses, bot_responses):
    conversation = []
    for user, bot in zip(user_responses, bot_responses):
        conversation.append({"user": user, "bot": bot})
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversation_log_{timestamp}.json"
    filepath = os.path.join(LOG_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    return filepath


if 'user_responses' not in st.session_state:
    st.session_state['user_responses'] = []
if 'bot_responses' not in st.session_state:
    st.session_state['bot_responses'] = []


st.markdown("""
<style>
.stCodeBlock {
    max-height: 300px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)


user_input = st.text_area("Python kodunuzu buraya girin:", height=150)

if st.button("Kodu Analiz Et"):
    if user_input:
        result = code_error_agent(user_input)
        st.session_state.user_responses.append(user_input)
        st.session_state.bot_responses.append(result)


for i in range(len(st.session_state['bot_responses'])):
    message(st.session_state['user_responses'][i], is_user=True)
    message(st.session_state['bot_responses'][i])


if st.button("Konuşmayı Kaydet"):
    log_filepath = save_conversation_log(st.session_state.user_responses, st.session_state.bot_responses)
    st.success(f"Konuşma kaydedildi: {log_filepath}")