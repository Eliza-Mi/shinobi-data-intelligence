"""
app.py — Shinobi Data Intelligence System (SDIS) · Dashboard
=============================================================
Interface de visualização que consome dados catalogados pelo AWS Glue
e armazenados em S3 (formato Parquet), via Amazon Athena.

DECISÕES DE ENGENHARIA:
- PyAthena: Conector DBAPI2-compatível para Athena. Mais leve que boto3 puro
  e compatível com pandas.read_sql, simplificando o código de consulta.
- st.cache_data: Cacheia resultados de queries por 1 hora. Sem cache, cada
  interação do usuário (hover, clique) dispara uma nova query ao Athena,
  multiplicando custos de escaneamento. Com cache, pagamos apenas 1x/hora.
- Plotly (não Matplotlib): Gráficos interativos, responsivos e com tooltips
  nativos. Matplotlib geraria imagens estáticas de menor qualidade visual.
- Tema dark customizado via CSS injetado: Streamlit não expõe todo o sistema
  de design nativamente; injetar CSS via st.markdown nos dá controle total
  sobre tipografia, paleta e efeitos visuais sem frameworks externos.
"""

import os
import textwrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pyathena import connect
from pyathena.pandas.cursor import PandasCursor

# ─── Configuração da Página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="SDIS · Shinobi Intelligence",
    page_icon="🏯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Constantes de ambiente ──────────────────────────────────────────────────
# Em produção, esses valores vêm de st.secrets (arquivo .streamlit/secrets.toml)
# NUNCA hardcode de credenciais no código-fonte (risco de exposição em git).
AWS_REGION       = st.secrets.get("AWS_REGION",       os.getenv("AWS_REGION", "us-east-1"))
ATHENA_DATABASE  = st.secrets.get("ATHENA_DATABASE",  os.getenv("ATHENA_DATABASE", "shinobi_catalog"))
ATHENA_TABLE     = st.secrets.get("ATHENA_TABLE",     os.getenv("ATHENA_TABLE", "characters"))
S3_OUTPUT        = st.secrets.get("S3_OUTPUT",        os.getenv("S3_OUTPUT", "s3://shinobi-data-lake-raw/athena-results/"))
AWS_ACCESS_KEY   = st.secrets.get("AWS_ACCESS_KEY_ID",     os.getenv("AWS_ACCESS_KEY_ID", ""))
AWS_SECRET_KEY   = st.secrets.get("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", ""))

# Atributos exibidos no radar — mapeamento coluna → label legível
RADAR_ATTRIBUTES = {
    "ninjutsu_norm":     "Ninjutsu",
    "taijutsu_norm":     "Taijutsu",
    "genjutsu_norm":     "Genjutsu",
    "inteligencia_norm": "Inteligência",
    "forca_norm":        "Força",
    "velocidade_norm":   "Velocidade",
}

# Paleta de cores para cada ninja no radar (até 8 ninjas simultâneos)
NINJA_COLORS = [
    "#C084FC",  # Roxo vibrante  (Hinata)
    "#F97316",  # Laranja chakra (Naruto)
    "#60A5FA",  # Azul elétrico  (Sasuke)
    "#34D399",  # Verde esmeralda (Rock Lee)
    "#FB7185",  # Rosa sakura     (Sakura)
    "#FBBF24",  # Amarelo dourado (Gaara)
    "#A78BFA",  # Lavanda         (Kakashi)
    "#38BDF8",  # Ciano           (Itachi)
]

# ─── Injeção de CSS customizado ──────────────────────────────────────────────
# DECISÃO ESTÉTICA: Tema inspirado no selo de convocação (kanji 召) —
# fundo quase-preto com gradiente roxo, tipografia de alto contraste.
# Usamos a fonte "Cinzel" para títulos (evoca misticismo/hierarquia)
# e "JetBrains Mono" para dados técnicos (legibilidade de código).
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=JetBrains+Mono:wght@300;400&family=Inter:wght@300;400;500&display=swap');

:root {
    --bg-primary:    #0A0A0F;
    --bg-secondary:  #12121A;
    --bg-card:       #1A1A2E;
    --accent-purple: #C084FC;
    --accent-orange: #F97316;
    --accent-dim:    #6D28D9;
    --text-primary:  #F1F0FB;
    --text-muted:    #94A3B8;
    --border-glow:   rgba(192, 132, 252, 0.3);
}

/* Reset de fundo do Streamlit */
.stApp { background: var(--bg-primary); }
section[data-testid="stSidebar"] {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-glow);
}

/* Tipografia global */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text-primary); }

/* Título principal */
.sdis-title {
    font-family: 'Cinzel', serif;
    font-size: clamp(1.6rem, 4vw, 2.8rem);
    font-weight: 900;
    background: linear-gradient(135deg, #C084FC 0%, #F97316 60%, #FBBF24 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 0.04em;
    margin-bottom: 0.1em;
    line-height: 1.1;
}
.sdis-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

/* Cards de bio */
.bio-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glow);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(109, 40, 217, 0.15);
    transition: border-color 0.2s;
}
.bio-card:hover { border-color: var(--accent-purple); }
.bio-card h3 {
    font-family: 'Cinzel', serif;
    font-size: 1.05rem;
    color: var(--accent-purple);
    margin: 0 0 0.6rem 0;
    letter-spacing: 0.05em;
}
.bio-badge {
    display: inline-block;
    background: rgba(192,132,252,0.15);
    border: 1px solid rgba(192,132,252,0.4);
    color: var(--accent-purple);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
    margin-bottom: 4px;
}
.bio-badge.orange {
    background: rgba(249,115,22,0.15);
    border-color: rgba(249,115,22,0.4);
    color: var(--accent-orange);
}
.bio-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.bio-value {
    font-size: 0.9rem;
    color: var(--text-primary);
    margin-bottom: 0.7rem;
}
.potencial-score {
    font-family: 'Cinzel', serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--accent-orange);
    line-height: 1;
}
.potencial-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* Sidebar customizada */
.sidebar-title {
    font-family: 'Cinzel', serif;
    font-size: 0.85rem;
    color: var(--accent-purple);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

/* Métricas */
[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border-glow);
    border-radius: 8px;
    padding: 0.8rem 1rem;
}
[data-testid="metric-container"] label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Cinzel', serif;
    color: var(--accent-purple) !important;
}

/* Divider estilizado */
hr { border-color: var(--border-glow); margin: 1.5rem 0; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--accent-dim); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ─── Conexão com Athena ──────────────────────────────────────────────────────

@st.cache_resource
def _get_athena_connection():
    """
    Cria e cacheia a conexão com o Amazon Athena.

    cache_resource vs cache_data:
    - cache_resource: para objetos de conexão/sessão (singleton por sessão do app).
    - cache_data:     para DataFrames e resultados de query (TTL configurável).
    Misturar os dois garante que não abrimos múltiplas conexões nem
    recriamos DataFrames desnecessariamente.
    """
    kwargs = dict(
        region_name=AWS_REGION,
        s3_staging_dir=S3_OUTPUT,
        schema_name=ATHENA_DATABASE,
        cursor_class=PandasCursor,
    )
    # Injeta credenciais apenas se fornecidas (em produção usa IAM Role da instância)
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        kwargs["aws_access_key_id"]     = AWS_ACCESS_KEY
        kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
    return connect(**kwargs)


# ─── Queries ao Athena (com cache de 1 hora) ────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="🔮 Consultando o Registro Akatsuki...")
def load_ninja_roster() -> pd.DataFrame:
    """
    Carrega lista de ninjas disponíveis no Data Lake.

    OTIMIZAÇÃO: Seleciona apenas as colunas necessárias para o menu lateral.
    Parquet + projeção de colunas = Athena lê <5% do arquivo. Com JSON bruto,
    leria 100% mesmo que precisássemos só de 'nome'.
    """
    query = f"""
        SELECT DISTINCT
            id,
            nome,
            vila,
            rank,
            potencial_chakra,
            natureza_chakra,
            jutsus_count
        FROM "{ATHENA_DATABASE}"."{ATHENA_TABLE}"
        WHERE nome IS NOT NULL
          AND nome != 'Desconhecido'
        ORDER BY potencial_chakra DESC
        LIMIT 200
    """
    conn = _get_athena_connection()
    return pd.read_sql(query, conn)


@st.cache_data(ttl=3600, show_spinner="⚡ Carregando atributos de chakra...")
def load_ninja_attributes(ninja_names: tuple[str, ...]) -> pd.DataFrame:
    """
    Busca atributos completos dos ninjas selecionados para o radar.

    Parâmetro como tuple (não list) porque st.cache_data requer argumentos
    hashable — listas não são hashable em Python, tuples sim.
    """
    if not ninja_names:
        return pd.DataFrame()

    # Parametrização segura: construímos os placeholders manualmente.
    # PyAthena não suporta bind parameters estilo DBAPI2 com PandasCursor,
    # mas sanitizamos a entrada com replace para evitar SQL injection básico.
    sanitized = [n.replace("'", "''") for n in ninja_names]
    names_sql = ", ".join(f"'{n}'" for n in sanitized)

    query = f"""
        SELECT
            nome,
            vila,
            rank,
            classificacao,
            natureza_chakra,
            jutsus_count,
            potencial_chakra,
            ninjutsu_norm,
            taijutsu_norm,
            genjutsu_norm,
            inteligencia_norm,
            forca_norm,
            velocidade_norm,
            debut_anime,
            debut_manga
        FROM "{ATHENA_DATABASE}"."{ATHENA_TABLE}"
        WHERE nome IN ({names_sql})
    """
    conn = _get_athena_connection()
    return pd.read_sql(query, conn)


# ─── Componentes de visualização ────────────────────────────────────────────

def build_radar_chart(df: pd.DataFrame) -> go.Figure:
    """
    Constrói gráfico de radar (Spider Chart) comparando atributos de múltiplos ninjas.

    DECISÃO: Plotly sobre Matplotlib por:
    1. Interatividade nativa (hover, zoom, toggle de séries)
    2. Renderização WebGL para datasets grandes
    3. API declarativa mais legível
    4. Suporte nativo a theming transparente (integra com CSS do Streamlit)
    """
    attrs   = list(RADAR_ATTRIBUTES.keys())
    labels  = list(RADAR_ATTRIBUTES.values())
    # Fecha o polígono repetindo o primeiro ponto
    labels_closed = labels + [labels[0]]

    fig = go.Figure()

    for i, (_, row) in enumerate(df.iterrows()):
        values        = [float(row.get(a, 0) or 0) for a in attrs]
        values_closed = values + [values[0]]
        color         = NINJA_COLORS[i % len(NINJA_COLORS)]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            name=row["nome"],
            line=dict(color=color, width=2.5),
            fillcolor=color.replace(")", ", 0.12)").replace("rgb", "rgba")
                      if color.startswith("rgb") else f"{color}1F",
            hovertemplate=(
                f"<b>{row['nome']}</b><br>"
                "%{theta}: <b>%{r:.2f}</b>/5.0<extra></extra>"
            ),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(26, 26, 46, 0.8)",
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickfont=dict(size=9, color="#94A3B8", family="JetBrains Mono"),
                gridcolor="rgba(192, 132, 252, 0.15)",
                linecolor="rgba(192, 132, 252, 0.2)",
                tickvals=[1, 2, 3, 4, 5],
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color="#F1F0FB", family="Cinzel"),
                gridcolor="rgba(192, 132, 252, 0.2)",
                linecolor="rgba(192, 132, 252, 0.3)",
            ),
        ),
        showlegend=True,
        legend=dict(
            font=dict(size=11, color="#F1F0FB", family="Inter"),
            bgcolor="rgba(18, 18, 26, 0.9)",
            bordercolor="rgba(192,132,252,0.3)",
            borderwidth=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=60, t=40, b=40),
        height=480,
    )
    return fig


def render_bio_card(row: pd.Series, color: str) -> None:
    """Renderiza card HTML com bio e métricas de um ninja."""
    potencial = float(row.get("potencial_chakra", 0) or 0)
    vila      = str(row.get("vila", "—") or "—")
    rank      = str(row.get("rank", "—") or "—")
    classif   = str(row.get("classificacao", "") or "")
    natureza  = str(row.get("natureza_chakra", "") or "")
    jutsus    = int(row.get("jutsus_count", 0) or 0)
    debut_a   = str(row.get("debut_anime", "—") or "—")

    badges_html = ""
    if classif and classif != "None":
        badges_html += f'<span class="bio-badge">{classif}</span>'
    if natureza and natureza != "None":
        for n in natureza.split(",")[:3]:
            n = n.strip()
            if n:
                badges_html += f'<span class="bio-badge orange">{n}</span>'

    nome_color_style = f"color: {color};"

    st.markdown(f"""
    <div class="bio-card">
        <h3 style="{nome_color_style}">{row['nome']}</h3>
        <div>{badges_html}</div>
        <div style="margin-top:0.8rem; display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
            <div>
                <div class="bio-label">Vila</div>
                <div class="bio-value">{vila}</div>
                <div class="bio-label">Rank</div>
                <div class="bio-value">{rank}</div>
            </div>
            <div>
                <div class="bio-label">Jutsus</div>
                <div class="bio-value">{jutsus}</div>
                <div class="bio-label">Debut Anime</div>
                <div class="bio-value" style="font-size:0.78rem;">{textwrap.shorten(debut_a, 28)}</div>
            </div>
        </div>
        <hr style="margin:0.8rem 0; border-color:rgba(192,132,252,0.2);">
        <div class="potencial-label">Potencial de Chakra</div>
        <div class="potencial-score">{potencial:.3f}</div>
        <div style="font-size:0.7rem;color:#64748B;font-family:'JetBrains Mono',monospace;margin-top:2px;">
            ((Nin+Tai+Gen) × Int) / 10
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Layout principal ────────────────────────────────────────────────────────

def main() -> None:
    # ── Cabeçalho ────────────────────────────────────────────────────────────
    st.markdown('<div class="sdis-title">🏯 Shinobi Data Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sdis-subtitle">AWS · Athena · S3 Parquet · Naruto Universe Analytics</div>', unsafe_allow_html=True)

    # ── Carregamento do roster ────────────────────────────────────────────────
    try:
        df_roster = load_ninja_roster()
    except Exception as exc:
        st.error(f"**Falha na conexão com Athena:** `{exc}`")
        st.info("Verifique as credenciais em `.streamlit/secrets.toml` e o S3 staging dir.")
        st.stop()

    if df_roster.empty:
        st.warning("Nenhum ninja encontrado no Data Lake. Execute a Lambda de ingestão primeiro.")
        st.stop()

    # ── Sidebar — seleção de ninjas ──────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sidebar-title">⛩ Seleção de Ninjas</div>', unsafe_allow_html=True)

        # Filtro por Vila
        vilas_disponiveis = sorted(df_roster["vila"].dropna().unique())
        vila_filter = st.multiselect(
            "Filtrar por Vila",
            options=vilas_disponiveis,
            default=[],
            placeholder="Todas as vilas",
        )

        df_filtered = df_roster if not vila_filter else df_roster[df_roster["vila"].isin(vila_filter)]

        # Multiselect de ninjas (ordenados por Potencial_Chakra desc)
        ninja_options = df_filtered["nome"].tolist()
        # Pré-seleção dos Top 3 para demonstração imediata
        default_selection = ninja_options[:3] if len(ninja_options) >= 3 else ninja_options

        selected_names = st.multiselect(
            "Comparar Ninjas",
            options=ninja_options,
            default=default_selection,
            max_selections=8,
            help="Selecione até 8 ninjas para comparar no Radar Chart.",
        )

        st.markdown("---")
        st.markdown('<div class="sidebar-title">📊 Resumo do Data Lake</div>', unsafe_allow_html=True)
        st.metric("Total de Ninjas", len(df_roster))
        st.metric("Vilas Catalogadas", df_roster["vila"].nunique())

        top_ninja = df_roster.iloc[0]
        st.metric(
            "Maior Potencial",
            f"{top_ninja['potencial_chakra']:.3f}",
            delta=top_ninja["nome"],
        )

    # ── Área principal ────────────────────────────────────────────────────────
    if not selected_names:
        st.info("👈 Selecione ao menos um ninja no menu lateral para começar a análise.")
        return

    df_ninjas = load_ninja_attributes(tuple(selected_names))

    if df_ninjas.empty:
        st.warning("Dados de atributos não encontrados para os ninjas selecionados.")
        return

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    cols_metrics = st.columns(len(df_ninjas) if len(df_ninjas) <= 4 else 4)
    for i, (_, row) in enumerate(df_ninjas.iterrows()):
        if i < 4:
            with cols_metrics[i]:
                st.metric(
                    label=row["nome"],
                    value=f"{float(row.get('potencial_chakra', 0) or 0):.3f}",
                    delta=f"{row.get('vila', '—')} · {row.get('rank', '—')}",
                )

    st.markdown("---")

    # ── Radar Chart + Bio Cards ───────────────────────────────────────────────
    col_radar, col_bio = st.columns([3, 2], gap="large")

    with col_radar:
        st.markdown("#### ⚔️ Análise Comparativa de Atributos")
        fig = build_radar_chart(df_ninjas)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Tabela de atributos numéricos abaixo do gráfico
        with st.expander("📋 Dados Brutos dos Atributos"):
            display_cols = ["nome"] + list(RADAR_ATTRIBUTES.keys()) + ["potencial_chakra"]
            existing_cols = [c for c in display_cols if c in df_ninjas.columns]
            df_display = df_ninjas[existing_cols].copy()
            # Renomeia colunas para exibição legível
            rename_map = {k: v for k, v in RADAR_ATTRIBUTES.items()}
            rename_map["nome"] = "Ninja"
            rename_map["potencial_chakra"] = "Potencial"
            df_display = df_display.rename(columns=rename_map)
            st.dataframe(
                df_display.style.format({
                    col: "{:.2f}" for col in df_display.columns if col not in ["Ninja"]
                }).background_gradient(
                    subset=[c for c in df_display.columns if c not in ["Ninja"]],
                    cmap="Purples",
                ),
                use_container_width=True,
                hide_index=True,
            )

    with col_bio:
        st.markdown("#### 📜 Fichas dos Shinobis")
        for i, (_, row) in enumerate(df_ninjas.iterrows()):
            render_bio_card(row, NINJA_COLORS[i % len(NINJA_COLORS)])

    # ── Ranking Geral ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🏆 Ranking Global de Potencial de Chakra")
    ranking_cols = ["nome", "vila", "rank", "potencial_chakra", "natureza_chakra", "jutsus_count"]
    existing_ranking = [c for c in ranking_cols if c in df_roster.columns]
    st.dataframe(
        df_roster[existing_ranking]
            .head(30)
            .rename(columns={
                "nome": "Ninja", "vila": "Vila", "rank": "Rank",
                "potencial_chakra": "Potencial", "natureza_chakra": "Chakra",
                "jutsus_count": "Jutsus",
            })
            .style.format({"Potencial": "{:.4f}"})
            .background_gradient(subset=["Potencial"], cmap="Purples"),
        use_container_width=True,
        hide_index=True,
    )

    # ── Rodapé ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;margin-top:3rem;padding:1rem;
         border-top:1px solid rgba(192,132,252,0.2);
         font-family:'JetBrains Mono',monospace;font-size:0.65rem;
         color:#475569;letter-spacing:0.12em;">
        SDIS v1.0 · AWS Serverless · Athena + S3 Parquet + Glue ·
        Data: NarutoDB API · Built for Portfolio
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
