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
    .custom-btn {
        display: inline-block;
        width: 320px;
        height: 160px;
        margin: 40px;
        background: #0A2342;
        color: #fff !important;
        font-size: 2rem;
        font-weight: bold;
        border: none;
        border-radius: 22px;
        text-align: center;
        vertical-align: middle;
        text-decoration: none;
        box-shadow: 0 6px 24px 0 rgba(0,0,0,0.20);
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .custom-btn:hover {
        background: #10336B;
        transform: scale(1.04);
        box-shadow: 0 10px 40px 0 rgba(0,0,0,0.28);
        color: #f9dc5c !important;
        cursor: pointer;
    }
    .center-btns {
        text-align: center;
        margin-top: 5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1 style='color:#fff;'>DLOG PMAL</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#fff;font-weight:300;'>Diretoria de Logística</h3>", unsafe_allow_html=True)
st.write("")

# Botões grandes centralizados
st.markdown('<div class="center-btns">', unsafe_allow_html=True)
st.markdown(f"""
    <a href="/efetivo" class="custom-btn" target="_self">🪖<br>Dashboard<br>de Efetivo</a>
    <a href="/viaturas" class="custom-btn" target="_self">🚓<br>Dashboard<br>de Viaturas</a>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.write("")
st.caption("Desenvolvido pela Secretaria - DLOG/PMAL | 2025")
