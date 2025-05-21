import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from urllib.parse import urlparse

# Função para construir URLs raw do GitHub
def build_raw_url(repo_url: str, filename: str) -> str:
    # Remove .git e possíveis barras finais
    url = repo_url.rstrip('/').rstrip('.git')
    # Extrai proprietário e repositório
    parts = urlparse(url).path.strip('/').split('/')
    if len(parts) != 2:
        raise ValueError("URL inválida. Deve ser https://github.com/usuario/repositorio")
    user, repo = parts
    # Constrói raw URL para a branch main
    return f"https://raw.githubusercontent.com/{user}/{repo}/main/{filename}"

# Carregamento de dados
@st.cache_data(ttl=3600)
def load_data(repo_url: str):
    # Define nomes dos arquivos esperados
    files = {
        'abast': 'Abastecimentos_Consolidados.xlsx',
        'frota': 'Frota_Master_Enriched.xlsx',
        'opm': 'OPM_Municipios_Enriched.xlsx'
    }
    # Constrói URLs raw
    try:
        url_abast = build_raw_url(repo_url, files['abast'])
        url_frota = build_raw_url(repo_url, files['frota'])
        url_opm   = build_raw_url(repo_url, files['opm'])
        ab = pd.read_excel(url_abast)
        fr = pd.read_excel(url_frota)
        op = pd.read_excel(url_opm)
    except Exception as e:
        st.error(f"Falha ao carregar os arquivos do GitHub: {e}")
        st.stop()
    # Padronizar placas
    for df in [ab, fr]:
        df['Placa'] = df['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)
    # Merge de tabelas
    df = ab.merge(fr, on='Placa', how='left')
    df = df.merge(op[['OPM','Latitude','Longitude']], on='OPM', how='left')
    # Detecta coluna de data
    for c in df.columns:
        if 'data' in c.lower():
            df['Data'] = pd.to_datetime(df[c], errors='coerce')
            break
    df = df.dropna(subset=['Data'])
    return df

# Função principal
def main():
    # Configuração da página
    st.set_page_config(
        page_title="Dashboard PMAL - Combustível",
        page_icon="⛽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Input: URL do repositório GitHub
    repo_url = st.sidebar.text_input(
        "🔗 URL do repositório GitHub (https://github.com/usuario/repositorio)",
        value="https://github.com/DLOG2025/Dashboard"
    )
    if not repo_url:
        st.sidebar.warning("Insira a URL do seu repositório GitHub.")
        return

    # Carrega dados diretamente do GitHub
    df = load_data(repo_url)

    # Filtros
    st.sidebar.header("📅 Filtros")
    min_date, max_date = df['Data'].min(), df['Data'].max()
    data_selec = st.sidebar.date_input(
        "Período de Abastecimento", [min_date, max_date],
        min_value=min_date, max_value=max_date
    )
    df = df[(df['Data'] >= pd.to_datetime(data_selec[0])) & (df['Data'] <= pd.to_datetime(data_selec[1]))]
    opms = sorted(df['OPM'].dropna().unique())
    sel_opm = st.sidebar.multiselect("Selecione OPM(s)", opms, default=opms)
    df = df[df['OPM'].isin(sel_opm)]

    # Layout em abas
    tab1, tab2, tab3, tab4 = st.tabs([
        "✅ Visão Geral", "⏳ Série Temporal", "🗺️ Geoespacial", "🚨 Anomalias"
    ])

    # Aba 1: KPIs
    with tab1:
        st.subheader("KPIs Principais")
        sum_cols = ['Gasolina (Lts)', 'Álcool (Lts)', 'Diesel (Lts)', 'Diesel S10 (Lts)']
        total_l = df[sum_cols].sum().sum()
        total_custo = df['Custo'].sum() if 'Custo' in df.columns else np.nan
        media_viatura = df.groupby('Placa')[sum_cols].sum().mean().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Litros (L)", f"{total_l:,.0f}")
        c2.metric("Total Gasto (R$)", f"R$ {total_custo:,.2f}")
        c3.metric("Média por Viatura (L)", f"{media_viatura:,.1f}")
        st.divider()
        st.subheader("Distribuição de Combustíveis")
        df_kpi = df[sum_cols].sum().reset_index().rename(columns={'index':'Combustível', 0:'Litros'})
        fig = px.pie(df_kpi, names='Combustível', values='Litros', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    # Aba 2: Série Temporal
    with tab2:
        st.subheader("Consumo Mensal")
        df_m = df.groupby(pd.Grouper(key='Data', freq='M'))[sum_cols].sum().reset_index()
        fig2 = px.line(df_m, x='Data', y=sum_cols, markers=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("*Passe o mouse sobre as linhas para detalhes*")

    # Aba 3: Geoespacial
    with tab3:
        st.subheader("Mapa de Heatmap por OPM")
        midpoint = (df['Latitude'].mean(), df['Longitude'].mean())
        deck = pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=midpoint[0], longitude=midpoint[1], zoom=6
            ),
            layers=[
                pdk.Layer(
                    'HeatmapLayer', data=df,
                    get_position='[Longitude, Latitude]',
                    radius=20000, opacity=0.6,
                )
            ],
        )
        st.pydeck_chart(deck)

    # Aba 4: Anomalias
    with tab4:
        st.subheader("Anomalias de Consumo")
        df['Total_L'] = df[sum_cols].sum(axis=1)
        z = (df['Total_L'] - df['Total_L'].mean()) / df['Total_L'].std()
        anomal = df[z.abs() > 2]
        st.metric("Total Registros", len(df), delta=f"{len(anomal)} anomalias detectadas")
        st.dataframe(anomal.sort_values('Total_L', ascending=False), use_container_width=True)

    # Efeitos Visuais
    if st.sidebar.button("🎉 Celebrar Resultados"):
        st.balloons()

    st.markdown("---")
    st.markdown("_Dashboard totalmente online, sem necessidade de upload manual._")

# Executar
def run():
    main()

if __name__ == '__main__':
    run()
