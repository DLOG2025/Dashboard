import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from urllib.parse import urlparse

# Constrói URLs raw do GitHub
def build_raw_url(repo_url: str, filename: str) -> str:
    url = repo_url.rstrip('/').rstrip('.git')
    parts = urlparse(url).path.strip('/').split('/')
    if len(parts) != 2:
        raise ValueError("URL inválida. Deve ser https://github.com/usuario/repositorio")
    user, repo = parts
    return f"https://raw.githubusercontent.com/{user}/{repo}/main/{filename}"

@st.cache_data(ttl=3600)
def load_data(repo_url: str) -> pd.DataFrame:
    # Nomes dos arquivos no repositório
    files = {
        'abast': 'Abastecimentos_Consolidados.xlsx',
        'frota': 'Frota_Master_Enriched.xlsx',
        'opm':   'OPM_Municipios_Enriched.xlsx'
    }
    # Carrega planilhas
    try:
        url_abast = build_raw_url(repo_url, files['abast'])
        url_frota = build_raw_url(repo_url, files['frota'])
        url_opm   = build_raw_url(repo_url, files['opm'])
        ab = pd.read_excel(url_abast)
        fr = pd.read_excel(url_frota)
        op = pd.read_excel(url_opm)
    except Exception as e:
        st.error(f"Falha ao carregar arquivos: {e}")
        st.stop()

    # Padroniza placa e OPM no arquivo de abastecimento
    placa_col_ab = next((c for c in ab.columns if 'placa' in c.lower()), None)
    unit_col_ab = next((c for c in ab.columns if 'unidade' in c.lower()), None)
    if not placa_col_ab or not unit_col_ab:
        st.error("Arquivo de abastecimento deve ter colunas PLACA e UNIDADE")
        st.stop()
    ab = ab.rename(columns={placa_col_ab: 'Placa', unit_col_ab: 'OPM'})
    ab['Placa'] = ab['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)

    # Unifica nomes de métricas de volume e custo
    if 'TOTAL_LITROS' in ab.columns and 'VALOR_TOTAL' in ab.columns:
        ab = ab.rename(columns={'TOTAL_LITROS': 'TOTAL_L', 'VALOR_TOTAL': 'Custo'})
    else:
        st.error("Colunas TOTAL_LITROS e VALOR_TOTAL não encontradas em Abastecimentos_Consolidados")
        st.stop()

    # Padroniza placa no arquivo de frota
    placa_col_fr = next((c for c in fr.columns if 'placa' in c.lower()), None)
    if not placa_col_fr:
        st.error("Arquivo de frota deve ter coluna PLACA")
        st.stop()
    fr = fr.rename(columns={placa_col_fr: 'Placa'})
    fr['Placa'] = fr['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)

    # Padroniza OPM no arquivo de municípios
    unit_col_op = next((c for c in op.columns if 'unidade' in c.lower()), None)
    if not unit_col_op:
        st.error("Arquivo de OPM deve ter coluna UNIDADE")
        st.stop()
    op = op.rename(columns={unit_col_op: 'OPM'})
    # Detecta coluna de município
    muni_col = next((c for c in op.columns if 'munic' in c.lower()), None)
    if muni_col:
        op = op.rename(columns={muni_col: 'Municipio'})
    # Merge de dados
    df = ab.merge(fr, on='Placa', how='left')
    if 'Municipio' in op.columns:
        df = df.merge(op[['OPM', 'Municipio']], on='OPM', how='left')
    return df

# Função principal
def main():
    st.set_page_config(page_title="Dashboard PMAL - Combustível", page_icon="⛽️", layout="wide")
    st.title("📊 Dashboard 100% Online - Abastecimento PMAL")

    # URL do repo GitHub
    repo_url = st.sidebar.text_input("🔗 URL do repositório GitHub:", "https://github.com/DLOG2025/Dashboard")
    if not repo_url:
        st.sidebar.warning("Informe a URL do repositório GitHub.")
        return
    df = load_data(repo_url)

    # Filtros
    st.sidebar.header("Filtros")
    # Período: se existir coluna Data, usa; senão ignora
    if 'Data' in df.columns:
        min_date, max_date = df['Data'].min(), df['Data'].max()
        date_sel = st.sidebar.date_input("Período de Abastecimento", [min_date, max_date], min_value=min_date, max_value=max_date)
        df = df[(df['Data'] >= pd.to_datetime(date_sel[0])) & (df['Data'] <= pd.to_datetime(date_sel[1]))]
    # OPM
    opms = sorted(df['OPM'].dropna().unique())
    sel_opm = st.sidebar.multiselect("Selecione OPM(s)", opms, default=opms)
    df = df[df['OPM'].isin(sel_opm)]

    # Abas
    tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Série Temporal", "Distribuição", "Geoespacial/Outros"])

    # KPI
    with tab1:
        st.subheader("KPIs Principais")
        total_l = df['TOTAL_L'].sum()
        total_custo = df['Custo'].sum()
        media_placa = df.groupby('Placa')['TOTAL_L'].sum().mean()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Litros (L)", f"{total_l:,.0f}")
        c2.metric("Total Gasto (R$)", f"R$ {total_custo:,.2f}")
        c3.metric("Média por Viatura (L)", f"{media_placa:,.1f}")

    # Série Temporal
    with tab2:
        st.subheader("Consumo por Arquivo (Mês)")
        if 'ARQUIVO' in df.columns:
            s = df.groupby('ARQUIVO')['TOTAL_L'].sum().reset_index()
            fig2 = px.bar(s, x='ARQUIVO', y='TOTAL_L', labels={'TOTAL_L':'Litros'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Arquivo de abastecimentos não contém coluna 'ARQUIVO'.")

    # Distribuição de combustível
    with tab3:
        st.subheader("Distribuição por Tipo de Combustível")
        if 'COMBUSTIVEL_DOMINANTE' in df.columns:
            d = df.groupby('COMBUSTIVEL_DOMINANTE')['TOTAL_L'].sum().reset_index()
            fig3 = px.pie(d, names='COMBUSTIVEL_DOMINANTE', values='TOTAL_L', hole=0.4)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Coluna 'COMBUSTIVEL_DOMINANTE' não encontrada.")

    # Geoespacial ou tabela de municípios
    with tab4:
        st.subheader("Consumo por Município")
        if 'Municipio' in df.columns:
            m = df.groupby('Municipio')['TOTAL_L'].sum().reset_index().sort_values('TOTAL_L', ascending=False)
            fig4 = px.bar(m, x='Municipio', y='TOTAL_L', labels={'TOTAL_L':'Litros'})
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Arquivo de municípios não possui coluna de município para análise.")

    st.sidebar.button("🎉 Balões", on_click=st.balloons)
    st.markdown("---")
    st.markdown("_Dashboard PMAL - Combustível totalmente online._")

if __name__ == '__main__':
    main()
