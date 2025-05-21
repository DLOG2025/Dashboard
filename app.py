import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk

# URLs dos arquivos (raw do GitHub ou outra hospedagem pública)
URL_ABAST = "COLOQUE_AQUI_A_URL_RAW/Abastecimentos_Consolidados.xlsx"
URL_FROTA = "COLOQUE_AQUI_A_URL_RAW/Frota_Master_Enriched.xlsx"
URL_OPM = "COLOQUE_AQUI_A_URL_RAW/OPM_Municipios_Enriched.xlsx"

@st.cache_data(ttl=3600)
def load_data():
    try:
        ab = pd.read_excel(URL_ABAST)
        fr = pd.read_excel(URL_FROTA)
        op = pd.read_excel(URL_OPM)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()
    # Padronizar placas
    for df in [ab, fr]:
        df['Placa'] = df['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)
    # Unir dados
    df = ab.merge(fr, on='Placa', how='left')
    df = df.merge(op[['OPM','Latitude','Longitude']], on='OPM', how='left')
    # Detectar coluna de data
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

    # Carregar dados automaticamente
    df = load_data()

    # Sidebar: filtros
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

    # Layout por abas
    tab1, tab2, tab3, tab4 = st.tabs(["✅ Visão Geral","⏳ Série Temporal","🗺️ Geoespacial","🚨 Anomalias"])

    with tab1:
        st.subheader("KPIs Principais")
        sum_cols = ['Gasolina (Lts)','Álcool (Lts)','Diesel (Lts)','Diesel S10 (Lts)']
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

    with tab2:
        st.subheader("Consumo Mensal")
        df_m = df.groupby(pd.Grouper(key='Data', freq='M'))[sum_cols].sum().reset_index()
        fig2 = px.line(df_m, x='Data', y=sum_cols, markers=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("*Passe o mouse sobre as linhas para detalhes*")

    with tab3:
        st.subheader("Mapa de Heatmap por OPM")
        midpoint = (float(df['Latitude'].mean()), float(df['Longitude'].mean()))
        deck = pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=6),
            layers=[pdk.Layer(
                'HeatmapLayer',
                data=df,
                get_position='[Longitude, Latitude]',
                radius=20000,
                opacity=0.6,
            )],
        )
        st.pydeck_chart(deck)

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
if __name__ == '__main__':
    main()
