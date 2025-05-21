import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(
    page_title="Dashboard PMAL - Combustível",
    layout="wide"
)

@st.cache_data(ttl=3600)
def load_data():
    # Carrega o Excel completo e detecta colunas essenciais dinamicamente
    df = pd.read_excel("Abastecimentos_Consolidados.xlsx")

    # Detecta colunas
    placa_col = next((c for c in df.columns if 'placa' in c.lower()), None)
    unidade_col = next((c for c in df.columns if 'unidade' in c.lower() or 'opm' in c.lower()), None)
    litros_col = next((c for c in df.columns if 'lts' in c.lower() or 'litro' in c.lower()), None)
    custo_col  = next((c for c in df.columns if 'valor' in c.lower() or 'custo' in c.lower()), None)
    date_col   = next((c for c in df.columns if 'data' in c.lower()), None)

    # Erros claros se faltar coluna
    if not all([placa_col, unidade_col, litros_col, custo_col, date_col]):
        missing = [name for name,col in [('placa',placa_col),('unidade',unidade_col),('litros',litros_col),('custo',custo_col),('data',date_col)] if col is None]
        st.error(f"Colunas essenciais não encontradas: {', '.join(missing)}")
        st.stop()

    # Renomeia para padrão
    df = df.rename(columns={
        placa_col: 'Placa',
        unidade_col: 'OPM',
        litros_col: 'Litros',
        custo_col: 'Custo',
        date_col: 'Data'
    })

    # Conversões
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df = df.dropna(subset=['Data'])
    df['Litros'] = pd.to_numeric(df['Litros'], errors='coerce').fillna(0)
    df['Custo']  = pd.to_numeric(df['Custo'],  errors='coerce').fillna(0)
    df['Placa']  = df['Placa'].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)

    return df

# Função principal
def main():
    st.title("📊 Dashboard PMAL – Consumo de Combustível Simplificado")

    # Carrega dados
    df = load_data()

    # Sidebar: filtro de período
    st.sidebar.header("Filtros")
    min_date, max_date = df['Data'].min(), df['Data'].max()
    date_range = st.sidebar.date_input(
        "Período", [min_date, max_date],
        min_value=min_date, max_value=max_date
    )
    df = df[(df['Data'] >= pd.to_datetime(date_range[0])) & (df['Data'] <= pd.to_datetime(date_range[1]))]

    # KPIs básicos
    st.header("✅ KPIs")
    total_l = df['Litros'].sum()
    total_c = df['Custo'].sum()
    unique_v = df['Placa'].nunique()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Litros (L)", f"{total_l:,.0f}")
    c2.metric("Total Gasto (R$)", f"R$ {total_c:,.2f}")
    c3.metric("Viaturas Únicas", unique_v)

    # Consumo Mensal
    st.header("📈 Consumo Mensal")
    monthly = (
        df.set_index('Data')['Litros']
          .resample('M').sum()
          .reset_index()
    )
    fig = px.line(monthly, x='Data', y='Litros', markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # Amostra de Dados
    st.header("📋 Amostra de Dados")
    st.dataframe(df.head(10), use_container_width=True)

    # Balões ao fim
    if st.sidebar.button("🎉 Celebrar"):
        st.balloons()

    st.markdown("---")
    st.markdown("_Dashboard enxuto e funcional sem configuração adicional._")

if __name__ == '__main__':
    main()
