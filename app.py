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
import webbrowser

load_dotenv()

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

LOG_DIR = "conversation_logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

st.markdown("<h1 style='color: #3771a2; border-bottom: 2px solid #3771a2;'>Python Code Error Checker</h1>", unsafe_allow_html=True)

# Custom CSS for the background and message colors
st.markdown(
    """
    <style>
    .stApp {
        background-color: white;
    }
    .user-message {
        background-color: #ffd141;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        margin-left: auto;
        color: black;
        width: fit-content;
        max-width: 80%;
    }
    .bot-message {
        background-color: #3771a2;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        color: white;
        width: fit-content;
        max-width: 80%;
    }
    .bot-message img {
        position: absolute;
        bottom: 10px;
        left: -60px; 
        width: 50px;
    }
    .stCodeBlock {
        max-height: 300px;
        overflow-y: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

def generate_summary(conversation):
    conversation_text = "\n".join([f"User: {entry['user']}\nBot: {entry['bot']}" for entry in conversation])
    prompt = f"Aşağıdaki konuşmayı özetle:\n\n{conversation_text}\n\nÖzet:"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content

def create_history_html():
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Geçmiş Konuşmalar</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
            h1 { color: #16b5ed; }
            .conversation { border: 1px solid #ddd; margin-bottom: 20px; padding: 10px; }
            .summary { background-color: #f0f0f0; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>Geçmiş Konuşmalar</h1>
    """

    log_files = [f for f in os.listdir(LOG_DIR) if f.startswith("conversation_log_") and f.endswith(".json")]
    
    for log_file in sorted(log_files, reverse=True):
        with open(os.path.join(LOG_DIR, log_file), "r", encoding="utf-8") as f:
            conversation = json.load(f)
        
        html_content += f"<div class='conversation'><h2>{log_file}</h2>"
        for entry in conversation:
            html_content += f"<p><strong>User:</strong> {entry['user']}</p>"
            html_content += f"<p><strong>Bot:</strong> {entry['bot']}</p>"
        
        summary = generate_summary(conversation)
        html_content += f"<div class='summary'><h3>Konuşma Özeti</h3><p>{summary}</p></div></div>"

    html_content += "</body></html>"

    history_filepath = os.path.join(LOG_DIR, "conversation_history.html")
    with open(history_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return history_filepath

# Initialize session state variables
if 'user_responses' not in st.session_state:
    st.session_state['user_responses'] = ["Merhaba"]
if 'bot_responses' not in st.session_state:
    st.session_state['bot_responses'] = ["Merhaba! Ben Python kod hata denetleyicisiyim. Lütfen analiz etmemi istediğiniz Python kodunu girin."]

input_container = st.container()
response_container = st.container()

# Capture user input and display bot responses
user_input = st.text_area("Python kodunuzu veya mesajınızı buraya girin:", "", key="input")

with response_container:
    if user_input:
        if any(keyword in user_input.lower() for keyword in ['print', 'def', 'class', 'import', 'for', 'while', 'if', '=']):
            response = code_error_agent(user_input)
        else:
            response = "Bu bir Python kodu gibi görünmüyor. Lütfen geçerli bir Python kodu girin."
        
        st.session_state.user_responses.append(user_input)
        st.session_state.bot_responses.append(response)
        
    if st.session_state['bot_responses']:
        for i in range(len(st.session_state['bot_responses'])):
            st.markdown(f'<div class="user-message">{st.session_state["user_responses"][i]}</div>', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 9])
            with col1:
                st.image("images/logo.png", width=50, use_column_width=True, clamp=True, output_format='auto')
            with col2:
                st.markdown(f'<div class="bot-message">{st.session_state["bot_responses"][i]}</div>', unsafe_allow_html=True)

with input_container:
    display_input = user_input

if st.button("Konuşmayı Bitir"):
    log_filepath = save_conversation_log(st.session_state.user_responses, st.session_state.bot_responses)
    st.success(f"Konuşma kaydedildi: {log_filepath}")
    st.session_state.user_responses = ["Merhaba"]
    st.session_state.bot_responses = ["Merhaba! Ben Python kod hata denetleyicisiyim. Lütfen analiz etmemi istediğiniz Python kodunu girin."]

if st.button("Geçmiş Konuşmaları Görüntüle"):
    history_filepath = create_history_html()
    webbrowser.open_new_tab(f'file://{os.path.abspath(history_filepath)}')