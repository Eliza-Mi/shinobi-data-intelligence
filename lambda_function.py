import json
import logging
import os
from typing import Any
import awswrangler as wr
import pandas as pd
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_BASE_URL = "https://dattebayo-api.onrender.com/characters"
S3_BUCKET    = os.environ.get("S3_BUCKET", "shinobi-data-lake-raw")
S3_PATH_RAW  = f"s3://{S3_BUCKET}/raw/characters/"
S3_PATH_PROC = f"s3://{S3_BUCKET}/processed/characters/"
GLUE_DB      = os.environ.get("GLUE_DATABASE", "shinobi_catalog")
GLUE_TABLE   = "characters"
ATTRIBUTE_COLS = ["ninjutsu","taijutsu","genjutsu","inteligencia","forca","velocidade"]

def _fetch_all_characters(pages=3, limit=20):
    characters = []
    for page in range(1, pages + 1):
        url = f"{API_BASE_URL}?page={page}&limit={limit}"
        logger.info("Fetching page %d", page)
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                logger.error("Status %d", response.status_code)
                break
            data = response.json()
            batch = data.get("characters", [])
            if not batch:
                break
            characters.extend(batch)
            logger.info("Total: %d", len(characters))
        except Exception as e:
            logger.error("Erro pagina %d: %s", page, str(e))
            break
    return characters

def _safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except:
        return default

def _extract_jutsu_count(char):
    jutsus = char.get("jutsu", []) or []
    return len(jutsus)

def _normalize(series, scale_max=5.0):
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([scale_max/2]*len(series), index=series.index)
    return ((series - mn) / (mx - mn)) * scale_max

def _build_dataframe(characters):
    rows = []
    for char in characters:
        personal  = char.get("personal", {}) or {}
        rank_info = char.get("rank", {}) or {}
        debuts    = char.get("debut", {}) or {}
        jutsus    = _extract_jutsu_count(char)
        natures   = char.get("natureType", []) or []
        rows.append({
            "id":              char.get("id"),
            "nome":            char.get("name", "Desconhecido"),
            "vila":            personal.get("village") or personal.get("affiliation", "Desconhecida"),
            "rank":            rank_info.get("ninjaRank", {}).get("Part I", "Genin") if isinstance(rank_info.get("ninjaRank"), dict) else str(rank_info.get("ninjaRank", "Genin")),
            "classificacao":   char.get("classification", [None])[0] if isinstance(char.get("classification"), list) else str(char.get("classification", "")),
            "natureza_chakra": ", ".join(natures),
            "jutsus_count":    jutsus,
            "imagem_url":      (char.get("images") or [None])[0],
            "debut_anime":     str(debuts.get("anime", "")),
            "debut_manga":     str(debuts.get("manga", "")),
            "ninjutsu":        float(len(natures)) if natures else 2.5,
            "taijutsu":        _safe_float(personal.get("kekkeiGenkai")) if personal.get("kekkeiGenkai") else float(jutsus % 5),
            "genjutsu":        float(jutsus % 4),
            "inteligencia":    float(len(char.get("tools", []) or [])) + 1.0,
            "forca":           float(jutsus % 5) + 1.0,
            "velocidade":      float(len(natures)) + float(jutsus % 3),
        })
    df = pd.DataFrame(rows)
    for col in ATTRIBUTE_COLS:
        if col in df.columns:
            mv = df[col].median()
            df[col] = df[col].fillna(mv if pd.notna(mv) else 2.5).apply(_safe_float)
    for col in ATTRIBUTE_COLS:
        if col in df.columns:
            df[f"{col}_norm"] = _normalize(df[col].astype(float))
    df["potencial_chakra"] = ((df["ninjutsu_norm"]+df["taijutsu_norm"]+df["genjutsu_norm"])*df["inteligencia_norm"]/10).round(4)
    df["nome"] = df["nome"].astype(str).str.strip()
    df["vila"] = df["vila"].astype(str).str.strip().str.title()
    df["rank"] = df["rank"].astype(str).str.strip()
    df["id"]   = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    logger.info("DataFrame: %d x %d", *df.shape)
    return df

def lambda_handler(event, context):
    logger.info("=== SDIS iniciado ===")
    characters_raw = _fetch_all_characters(pages=event.get("pages", 3))
    logger.info("Coletados: %d", len(characters_raw))
    if not characters_raw:
        return {"statusCode": 204, "body": "Nenhum personagem coletado."}

    # CORRECAO: path completo com nome do arquivo para to_json
    wr.s3.to_json(
        df=pd.DataFrame(characters_raw),
        path=S3_PATH_RAW + "characters_raw.json",
        orient="records",
        lines=True,
    )
    logger.info("Raw salvo em: %s", S3_PATH_RAW)

    df_processed = _build_dataframe(characters_raw)

    wr.s3.to_parquet(
        df=df_processed,
        path=S3_PATH_PROC,
        dataset=True,
        mode="overwrite",
        database=GLUE_DB,
        table=GLUE_TABLE,
        compression="snappy",
    )
    logger.info("Parquet salvo em: %s", S3_PATH_PROC)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Pipeline SDIS concluido com sucesso!",
            "total": len(df_processed),
            "s3_processed": S3_PATH_PROC,
        }),
    }
