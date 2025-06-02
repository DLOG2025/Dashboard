import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Efetivo", page_icon="🪖", layout="wide")

# --- Botão HOME estilizado menor ---
st.markdown("""
    <style>
    .home-btn {
        display: inline-block;
        width: 140px;
        height: 54px;
        margin: 10px 0 32px 0;
        background: #0A2342;
        color: #fff !important;
        font-size: 1.2rem;
        font-weight: bold;
        border: none;
        border-radius: 14px;
        text-align: center;
        line-height: 54px;
        text-decoration: none !important;
        box-shadow: 0 4px 16px 0 rgba(0,0,0,0.10);
        letter-spacing: 2px;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .home-btn:hover {
        background: #10336B;
        color: #f9dc5c !important;
        transform: scale(1.04);
        text-decoration: none !important;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown('<a href="/" class="home-btn" target="_self">HOME</a>', unsafe_allow_html=True)

# ---- Configuração dos arquivos ----
URL_EFETIVO = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/EFETIVO_GERAL_DA_DLOG%20.xlsx"
URL_FUNCOES = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/FUNCOES_DE_PRACAS_COM_BGO.xlsx"

@st.cache_data
def load_data():
    df_efetivo = pd.read_excel(URL_EFETIVO, dtype=str).fillna("")
    df_funcoes = pd.read_excel(URL_FUNCOES, dtype=str).fillna("")
    return df_efetivo, df_funcoes

df_efetivo, df_funcoes = load_data()

# --- Normaliza nomes de colunas ---
df_efetivo.columns = df_efetivo.columns.str.upper().str.strip()
df_funcoes.columns = df_funcoes.columns.str.upper().str.strip()

# --- ORDEM HIERÁRQUICA (Cel ao Sd) ---
ordem_grad = ["CEL", "TEN CEL", "MAJ", "CAP", "1º TEN", "2º TEN",
              "SUBTENENTE", "1º SARGENTO", "2º SARGENTO", "3º SARGENTO", "CB", "SD"]

# --- Setores oficiais da DLOG ---
setores_dlog = [
    "DLOG 1", "DLOG 2", "DLOG 3", "DLOG 4", "DLOG 5", "DLOG 6",
    "CMM", "CMO", "CMB", "DIRETORIA", "SUBDIRETORIA", "SECRETARIA"
]

# --- Remove duplicidades por nome completo ---
df_efetivo_unique = df_efetivo.drop_duplicates(subset=["NOME"])

# --- KPIs básicos ---
st.subheader("✨ Indicadores Gerais")
total_efetivo = len(df_efetivo_unique)
total_setores = df_efetivo_unique["SETOR"].str.upper().isin([s.upper() for s in setores_dlog]).sum()
col1, col2 = st.columns(2)
col1.metric("Efetivo Atual (únicos)", total_efetivo)
col2.metric("Militares em setores DLOG", total_setores)

st.divider()

# --- Efetivo por Posto/Graduação (Ordem Hierárquica, sem duplicidade) ---
st.subheader("📊 Efetivo por Posto/Graduação")
ordem_grad = ["CEL", "TEN CEL", "MAJ", "CAP", "1º TEN", "2º TEN",
              "SUBTENENTE", "1º SARGENTO", "2º SARGENTO", "3º SARGENTO", "CB", "SD"]

if "P/G" in df_efetivo.columns:
    efetivo_grad = df_efetivo["P/G"].value_counts().reindex(ordem_grad, fill_value=0).reset_index()
    efetivo_grad.columns = ["Posto/Graduação", "Quantidade"]
    fig_grad = px.bar(
        efetivo_grad, 
        x="Posto/Graduação", 
        y="Quantidade", 
        color="Posto/Graduação", 
        category_orders={"Posto/Graduação": ordem_grad},
        title="Distribuição por Graduação"
    )
    st.plotly_chart(fig_grad, use_container_width=True)
else:
    st.warning("Coluna 'P/G' não encontrada nos dados do efetivo.")

st.divider()

# --- Efetivo por Setor (apenas setores oficiais DLOG) ---
st.subheader("👥 Efetivo por Setor")
df_efetivo_dlog = df_efetivo_unique[df_efetivo_unique["SETOR"].str.upper().isin([s.upper() for s in setores_dlog])]
efetivo_setor = df_efetivo_dlog.groupby("SETOR")["NOME"].count().reset_index(name="Quantidade")
st.dataframe(efetivo_setor, use_container_width=True)

# (Opcional: Mostra militares em outros setores)
df_efetivo_otros = df_efetivo_unique[~df_efetivo_unique["SETOR"].str.upper().isin([s.upper() for s in setores_dlog])]
if not df_efetivo_otros.empty:
    st.markdown("#### 👥 Efetivo lotado na DLOG, mas atuando em outros setores/locais:")
    st.dataframe(df_efetivo_otros[["NOME", "P/G", "SETOR", "LOTAÇÃO"]], use_container_width=True)

st.divider()

# --- Busca Detalhada do Efetivo ---
st.subheader("🔎 Busca Detalhada do Efetivo")
busca_nome = st.text_input("Buscar por nome, posto/graduação, setor ou lotação:").upper()

# Adiciona a graduação/posto da função ocupada (merge pelo nome de guerra, se possível)
df_result = df_efetivo_unique.copy()
if "N GUERRA" in df_efetivo_unique.columns and "NOME DE GUERRA" in df_funcoes.columns and "GRADUAÇÃO DA FUNÇÃO" in df_funcoes.columns:
    df_result = df_result.merge(df_funcoes[["NOME DE GUERRA", "GRADUAÇÃO DA FUNÇÃO"]],
                                left_on="N GUERRA", right_on="NOME DE GUERRA", how="left")

# Filtro de busca
if busca_nome:
    df_filtrado = df_result[
        df_result.apply(lambda row: any(busca_nome in str(row[c]).upper() for c in ["NOME", "P/G", "SETOR", "LOTAÇÃO"] if c in row), axis=1)
    ]
else:
    df_filtrado = df_result.copy()

colunas_mostrar = [col for col in ["NOME", "P/G", "SETOR", "LOTAÇÃO", "GRADUAÇÃO DA FUNÇÃO"] if col in df_filtrado.columns]
st.dataframe(df_filtrado[colunas_mostrar], use_container_width=True)

# --- Rodapé centralizado ---
st.markdown("""
    <div style="position: fixed; left: 0; bottom: 0; width: 100vw; background: rgba(255,255,255,0.0);
    text-align: center; padding: 18px 0 10px 0; font-size: 1.1rem; color: #0A2342 !important;
    font-weight: bold; letter-spacing: 1px; z-index: 999;">
    Desenvolvido pela Secretaria - DLOG/PMAL | 2025
    </div>
""", unsafe_allow_html=True)
