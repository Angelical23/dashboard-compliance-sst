import streamlit as st
import pandas as pd
import plotly.express as px
from st_supabase_connection import SupabaseConnection
import popular_banco; popular_banco.popular_dados()

# Configuração da página do Streamlit
st.set_page_config(page_title="Dashboard de Compliance SST", layout="wide")

# Conexão com o Supabase
conn = st.connection("supabase", type=SupabaseConnection)

# CSS Customizado para Estilização dos Cards e Layout
st.markdown("""
<style>
    .header-container { background-color: #1e3d59; padding: 15px; border-radius: 8px; color: white; margin-bottom: 20px; }
    .card { padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; color: #333; margin-bottom: 15px; }
    .card-title { font-size: 14px; font-weight: bold; color: #666; }
    .card-value { font-size: 26px; font-weight: bold; margin-top: 5px; }
    .bg-total { background-color: #f5f7fa; border-left: 5px solid #1e3d59; }
    .bg-emdia { background-color: #e8f5e9; border-left: 5px solid #2e7d32; color: #2e7d32; }
    .bg-atencao { background-color: #fffde7; border-left: 5px solid #f9a825; color: #f9a825; }
    .bg-vencido { background-color: #ffebee; border-left: 5px solid #c62828; color: #c62828; }
</style>
""", unsafe_allow_html=True)

# 1. CABEÇALHO DO DASHBOARD
st.markdown("""
<div class="header-container">
    <h2 style='margin:0;'>GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE</h2>
    <p style='margin:0; opacity:0.8;'>Gestora SST: Ana Silva</p>
</div>
""", unsafe_allow_html=True)

# Buscar dados do Supabase via queries consolidadas
try:
    res_colab = conn.table("colaboradores").select("*").execute()
    res_comp = conn.table("compliance_documentos").select("*, colaboradores(nome_completo, cpf, local_trabalho), tipos_documento(nome_documento)").execute()
    
    df_colab = pd.DataFrame(res_colab.data)
    df_comp = pd.DataFrame(res_comp.data)
except Exception as e:
    st.error(f"Erro ao conectar com o Supabase: {e}")
    st.stop()

if not df_comp.empty:
    # Extrair dados relacionais das colunas aninhadas do Supabase
    df_comp['Nome Completo'] = df_comp['colaboradores'].apply(lambda x: x['nome_completo'])
    df_comp['CPF'] = df_comp['colaboradores'].apply(lambda x: x['cpf'])
    df_comp['Local de Trabalho'] = df_comp['colaboradores'].apply(lambda x: x['local_trabalho'])
    df_comp['Documento'] = df_comp['tipos_documento'].apply(lambda x: x['nome_documento'])

    # 2. LINHA DE CARDS METRICAS (Valores Fictícios calculados ou agregados para simular a imagem)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="card bg-total"><div class="card-title">Total de Funcionários</div><div class="card-value">{len(df_colab)}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card bg-emdia"><div class="card-title">Collaboradores em Dia</div><div class="card-value">125 (83%)</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card bg-atencao"><div class="card-title">Documentos Vencendo (30 dias)</div><div class="card-value">15 (10%)</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="card bg-vencido"><div class="card-title">Documentos Vencidos</div><div class="card-value">10 (7%)</div></div>', unsafe_allow_html=True)

    st.write("---")

    # 3. SEÇÃO DE GRÁFICOS
    g_col1, g_col2 = st.columns([3, 2])
    
    with g_col1:
        st.subheader("Status de Documentação por Setor")
        # Criando dados mockados para o gráfico de barras empilhadas/agrupadas igual ao print
        chart_data = pd.DataFrame([
            {"Setor": "Production", "Status": "Regular", "Qtd": 150},
            {"Setor": "Production", "Status": "Vence em Breve", "Qtd": 1},
            {"Setor": "Production", "Status": "Vencido", "Qtd": 2},
            {"Setor": "Logistics", "Status": "Regular", "Qtd": 125},
            {"Setor": "Logistics", "Status": "Vence em Breve", "Qtd": 125},
            {"Setor": "Logistics", "Status": "Vencido", "Qtd": 125},
            {"Setor": "Maintenance", "Status": "Regular", "Qtd": 92},
            {"Setor": "Maintenance", "Status": "Vence em Breve", "Qtd": 1},
            {"Setor": "Maintenance", "Status": "Vencido", "Qtd": 3},
        ])
        fig_bar = px.bar(chart_data, x="Setor", y="Qtd", color="Status", barmode="group",
                         color_discrete_map={"Regular": "#1e3d59", "Vence in Breve": "#f9a825", "Vencido": "#c62828"})
        st.plotly_chart(fig_bar, use_container_width=True)

    with g_col2:
        st.subheader("Distribuição de Documentos Pendentes")
        fig_pie = px.pie(df_comp, names="Documento", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.write("---")

    # 4. TABELA CENTRAL: VISÃO GERAL DE DOCUMENTAÇÃO POR COLABORADOR
    st.subheader("VISÃO GERAL DE DOCUMENTAÇÃO POR COLABORADOR")
    
    # Pivotar a tabela dinâmica de compliance
    df_pivot = df_comp.pivot_table(
        index=['Nome Completo', 'CPF', 'Local de Trabalho'],
        columns='Documento',
        values='status_documento',
        aggfunc='first'
    ).reset_index().fillna("Sem Registro")
    
    # Exibir o DataFrame de forma amigável no Streamlit
    st.dataframe(df_pivot, use_container_width=True)
else:
    st.warning("Nenhum dado encontrado. Execute o script 'popular_banco.py' primeiro.")
    

