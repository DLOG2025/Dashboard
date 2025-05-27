import streamlit as st

# Configuração da página
st.set_page_config(page_title="DLOG PMAL - Home", page_icon="🛡️", layout="wide")

# CSS para imagem de fundo (ajuste o link se mudar a imagem!)
st.markdown(
    """
    <style>
    .stApp {
        background-image: url('https://raw.githubusercontent.com/DLOG2025/Dashboard/refs/heads/main/pagina_home.png');
        background-size: cover;
        background-position: center;
        min-height: 100vh;
    }
    /* Deixa os elementos de fundo transparentes */
    .block-container {
        background: rgba(0, 0, 0, 0.15);
        border-radius: 12px;
        padding: 2rem;
        margin-top: 3rem;
    }
    h1, h2, h3, h4, h5, h6, .stTextInput label, .stButton>button, .stRadio label {
        color: #fff !important;
        text-shadow: 2px 2px 6px #222;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Título e subtítulo
st.markdown("<h1 style='color:#fff;'>DLOG PMAL</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#fff;font-weight:300;'>Diretoria de Logística</h3>", unsafe_allow_html=True)
st.write("")

# Botões para navegar entre páginas
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/efetivo.py", label="🪖 Dashboard de Efetivo", icon="🪖")
with col2:
    st.page_link("pages/viaturas.py", label="🚓 Dashboard de Viaturas", icon="🚓")

st.write("")
st.caption("Desenvolvido por DLOG/PMAL | 2025")

