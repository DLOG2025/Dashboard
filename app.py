import streamlit as st

st.set_page_config(page_title="DLOG PMAL - Home", page_icon="🛡️", layout="wide")

# CSS personalizado
st.markdown(
    """
    <style>
    .stApp {
        background-image: url('https://raw.githubusercontent.com/DLOG2025/Dashboard/refs/heads/main/pagina_home.png');
        background-size: cover;
        background-position: center;
        min-height: 100vh;
    }
    h1, h2, h3, h4, h5, h6, p, .stMarkdown, .stTextInput label, .stCaption, .st-bq, .st-cc, .st-cv, .st-cn, .st-co {
        color: #0A2342 !important;
        text-shadow: 0px 1px 4px #ffffff30;
    }
    .custom-btn {
        display: inline-block;
        width: 320px;
        height: 160px;
        margin: 40px;
        background: #0A2342;
        color: #fff !important;
        font-size: 2.2rem;
        font-weight: bold;
        border: none;
        border-radius: 22px;
        text-align: center;
        vertical-align: middle;
        text-decoration: none !important;
        box-shadow: 0 6px 24px 0 rgba(0,0,0,0.20);
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: transform 0.15s, box-shadow 0.15s;
        line-height: 160px;
    }
    .custom-btn:hover {
        background: #10336B;
        transform: scale(1.04);
        box-shadow: 0 10px 40px 0 rgba(0,0,0,0.28);
        color: #f9dc5c !important;
        cursor: pointer;
        text-decoration: none !important;
    }
    .center-btns {
        text-align: center;
        margin-top: 5rem;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100vw;
        background: rgba(255,255,255,0.0);
        text-align: center;
        padding: 18px 0 10px 0;
        font-size: 1.1rem;
        color: #0A2342 !important;
        font-weight: bold;
        letter-spacing: 1px;
        z-index: 999;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1>DLOG PMAL</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='font-weight:300;'>Dashboard Integrado – Diretoria de Logística</h3>", unsafe_allow_html=True)
st.write("")

# Botões grandes centralizados, sem sublinhado, sem emoji, texto maiúsculo
st.markdown('<div class="center-btns">', unsafe_allow_html=True)
st.markdown(f"""
    <a href="/efetivo" class="custom-btn" target="_self">EFETIVO</a>
    <a href="/viaturas" class="custom-btn" target="_self">VIATURAS</a>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Rodapé centralizado
st.markdown("""
    <div class="footer">
    Desenvolvido pela Secretaria - DLOG/PMAL | 2025
    </div>
""", unsafe_allow_html=True)
