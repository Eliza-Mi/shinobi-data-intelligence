<div align="center">

```
███████╗██████╗ ██╗███████╗
██╔════╝██╔══██╗██║██╔════╝
███████╗██║  ██║██║███████╗
╚════██║██║  ██║██║╚════██║
███████║██████╔╝██║███████║
╚══════╝╚═════╝ ╚═╝╚══════╝
```

# 🏯 Shinobi Data Intelligence System
### *AWS Serverless Data Pipeline · Naruto Universe Analytics*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=for-the-badge&logo=awslambda&logoColor=white)](https://aws.amazon.com/lambda/)
[![Amazon S3](https://img.shields.io/badge/Amazon_S3-569A31?style=for-the-badge&logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![AWS Glue](https://img.shields.io/badge/AWS_Glue-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/glue/)
[![Athena](https://img.shields.io/badge/Amazon_Athena-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/athena/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Apache Parquet](https://img.shields.io/badge/Apache_Parquet-50ABF1?style=for-the-badge&logo=apachehadoop&logoColor=white)](https://parquet.apache.org/)

<br/>

> *"Um verdadeiro shinobi não age sem estratégia. Um verdadeiro engenheiro não age sem dados."*

<br/>

**[🔴 Live Demo](https://seu-app.streamlit.app)** · **[📊 Dashboard](https://seu-app.streamlit.app)** · **[📖 Documentação](#arquitetura)**

</div>

---

## 📋 Sobre o Projeto

O **SDIS (Shinobi Data Intelligence System)** é uma plataforma de Engenharia de Dados que transforma informações brutas do universo de Naruto em inteligência estratégica. O projeto simula um ecossistema real de análise de dados — desde a ingestão via API até a visualização em um Dashboard interativo com tema ninja.

### 🎯 Objetivo Técnico

Construir um pipeline **100% Serverless na AWS** utilizando exclusivamente a camada gratuita (Free Tier), demonstrando competências em:

- ✅ Ingestão de dados escalável via API pública
- ✅ Arquitetura de **Data Lake** em camadas (raw/processed)
- ✅ Processamento em formato colunar **Apache Parquet**
- ✅ Catalogação automática com **AWS Glue**
- ✅ Queries SQL serverless com **Amazon Athena**
- ✅ Visualização interativa com **Streamlit Cloud**

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    SDIS · Pipeline de Dados                     │
└─────────────────────────────────────────────────────────────────┘

  🌐 API Externa          ⚡ Processamento          🗄️ Data Lake (S3)
  ─────────────          ────────────────          ────────────────
  Dattebayo API    ───►  AWS Lambda           ───►  /raw/
  (REST/JSON)            Python 3.12                characters_raw.json
                         pandas + awswrangler
                                              ───►  /processed/
                                                    characters.parquet
                                                    (Snappy compressed)

  📚 Catalogação          🔍 Análise               📊 Visualização
  ──────────────          ──────────               ───────────────
  AWS Glue         ───►  Amazon Athena       ───►  Streamlit Cloud
  Crawler                SQL sobre S3               Dashboard Ninja
  Auto-schema            Pay-per-query              Radar Chart
                                                    Bio Cards
```

### Fluxo ETL detalhado

| Estágio | Serviço | Descrição |
|---------|---------|-----------|
| **Extract** | AWS Lambda | Coleta dados da API via HTTP paginado |
| **Load Raw** | Amazon S3 | Persiste JSON bruto — fonte de verdade imutável |
| **Transform** | AWS Lambda | Normalização Min-Max, imputação, cálculo de métricas |
| **Load Processed** | Amazon S3 | Salva Parquet com compressão Snappy |
| **Catalog** | AWS Glue | Crawler cria schema automaticamente |
| **Query** | Amazon Athena | SQL serverless sobre arquivos S3 |
| **Visualize** | Streamlit | Dashboard interativo com tema dark/ninja |

---

## 🛠️ Tecnologias Utilizadas

### Cloud Infrastructure
| Serviço | Uso | Free Tier |
|---------|-----|-----------|
| **AWS Lambda** | Execução do pipeline ETL | 1M requests/mês |
| **Amazon S3** | Data Lake (raw + processed) | 5GB storage |
| **AWS Glue** | Catalogação automática de schema | 1M objetos |
| **Amazon Athena** | Queries SQL serverless | 1TB/mês |

### Stack de Desenvolvimento
```python
# Core
Python         3.12    # Runtime principal
pandas         2.2+    # Manipulação de DataFrames
awswrangler    3.x     # SDK AWS para dados (S3, Glue, Athena)
pyarrow        latest  # Serialização Parquet

# Dashboard
streamlit      1.35+   # Interface web interativa
plotly         5.22+   # Radar Chart / Spider Chart
pyathena       3.9+    # Conector Athena → pandas

# Formato de dados
Apache Parquet         # Colunar + Snappy compression
```

---

## 📊 Decisões de Engenharia

### Por que Parquet?

```
JSON (raw)     →  ~2.5 MB  → Athena escaneia 100%
Parquet (proc) →  ~0.5 MB  → Athena escaneia só as colunas necessárias

Economia: ~80% menos dados escaneados = ~80% menos custo no Athena
Resultado: projeto 100% dentro do Free Tier da AWS ✅
```

### Fórmula de Potencial de Chakra

$$Potencial = \frac{(Ninjutsu + Taijutsu + Genjutsu) \times Inteligência}{10}$$

> Métrica customizada que recompensa ninjas com alto poder ofensivo amplificado pela inteligência estratégica. Divide por 10 para manter escala legível (0–1.5).

### Estratégia de Cache (Streamlit)

```python
@st.cache_resource  # Conexão Athena: singleton por sessão
def get_connection(): ...

@st.cache_data(ttl=3600)  # Queries: cache de 1 hora
def load_data(): ...
```

> Sem cache: cada hover/clique dispara uma nova query ao Athena (custo × N).
> Com cache: pagamos 1 query/hora independente de quantos usuários acessam.

### Normalização Min-Max (escala 0–5)

```python
# Usamos mediana (não média) como valor de imputação
# porque a distribuição de atributos em anime é assimétrica —
# ninjas "boss" inflam a média e distorcem a escala.
df[col] = df[col].fillna(df[col].median())
df[f"{col}_norm"] = (df[col] - min) / (max - min) * 5
```

---

## 🚀 Como Executar

### Pré-requisitos

- Conta AWS com Free Tier ativo
- Python 3.12+
- Conta no GitHub + Streamlit Cloud

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/shinobi-data-intelligence.git
cd shinobi-data-intelligence
pip install -r requirements.txt
```

### 2. Configure a AWS

```bash
# Crie o bucket S3
aws s3 mb s3://shinobi-data-lake-raw

# Crie as pastas
aws s3api put-object --bucket shinobi-data-lake-raw --key raw/characters/
aws s3api put-object --bucket shinobi-data-lake-raw --key processed/characters/
aws s3api put-object --bucket shinobi-data-lake-raw --key athena-results/
```

### 3. Deploy da Lambda

1. Crie a IAM Role `sdis-lambda-role` com as policies:
   - `AmazonS3FullAccess`
   - `AWSGlueServiceRole`
   - `CloudWatchLogsFullAccess`

2. Crie a função Lambda com:
   - **Runtime:** Python 3.12
   - **Layer:** `AWSSDKPandas-Python312`
   - **Timeout:** 3 minutos | **Memory:** 512 MB
   - **Variáveis de ambiente:**
     ```
     S3_BUCKET    = shinobi-data-lake-raw
     GLUE_DATABASE = shinobi_catalog
     ```

3. Cole o código de `lambda_function.py` e faça Deploy

### 4. Configure Glue + Athena

```sql
-- No Glue: crie o database 'shinobi_catalog'
-- Execute o Crawler apontando para:
-- s3://shinobi-data-lake-raw/processed/characters/

-- No Athena, configure o staging:
-- s3://shinobi-data-lake-raw/athena-results/

-- Valide com a query:
SELECT nome, vila, potencial_chakra
FROM shinobi_catalog.characters
ORDER BY potencial_chakra DESC
LIMIT 10;
```

### 5. Configure e rode o Dashboard

```bash
# Crie .streamlit/secrets.toml (NÃO suba para o GitHub)
cat > .streamlit/secrets.toml << EOF
AWS_ACCESS_KEY_ID     = "sua-key"
AWS_SECRET_ACCESS_KEY = "seu-secret"
AWS_REGION            = "us-east-1"
ATHENA_DATABASE       = "shinobi_catalog"
ATHENA_TABLE          = "characters"
S3_OUTPUT             = "s3://shinobi-data-lake-raw/athena-results/"
EOF

# Execute localmente
streamlit run app.py
```

---

## 🔐 Segurança

- Credenciais gerenciadas via **Streamlit Secrets** (nunca no código)
- IAM Role com **princípio do menor privilégio**
- Bucket S3 com **Block Public Access** ativo
- `.gitignore` configurado para excluir `secrets.toml`

---

## 📁 Estrutura do Projeto

```
shinobi-data-intelligence/
│
├── lambda_function.py    # Pipeline ETL (AWS Lambda)
├── app.py                # Dashboard Streamlit
├── requirements.txt      # Dependências Python
├── README.md             # Este arquivo
│
└── .streamlit/
    └── secrets.toml      # ⚠️ NÃO versionar — credenciais AWS
```

---

## 🧪 Resultados

Após executar o pipeline completo:

| Métrica | Valor |
|---------|-------|
| Ninjas processados | 60 |
| Vilas catalogadas | 34 |
| Maior Potencial de Chakra | Kakashi Hatake (1.294) |
| Volume raw (JSON) | ~2.5 KB |
| Volume processed (Parquet) | ~0.5 KB |
| Redução de custo Athena | ~80% |
| Custo total AWS | $0.00 (Free Tier) |

---

## 🗺️ Próximos Passos

- [ ] Adicionar particionamento por Vila no Parquet
- [ ] Implementar trigger automático da Lambda via EventBridge (agendamento diário)
- [ ] Adicionar mais páginas ao dashboard (Clãs, Vilas, Jutsus)
- [ ] Migrar para AWS CDK para Infrastructure as Code
- [ ] Adicionar testes unitários com pytest

---

## 👩‍💻 Autora

**Elizama Oliveira**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/elizamamoliveira-it)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/eliza-mi)

---

<div align="center">

*Construído com 🍜 e muito chakra*

**SDIS v1.0 · AWS Serverless · Apache Parquet · Streamlit**

</div>
