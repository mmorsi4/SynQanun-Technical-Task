from document_parser import parse_directory
import psycopg2 as pg
from fastapi import FastAPI, HTTPException
import os
import time

DATABASE_URL = os.getenv("DATABASE_URL")
JUDGMENT_DIR = "./example-samples/judgments/"
FATWA_DIR = "./example-samples/fatwas/"
LAW_DIR = "./example-samples/laws/"
TABLE_MAP = {
    "judgment": {
        "main_table": "judgments",
        "main_text_fields": ["authority", "facts", "reasons"],
        "related_table": "judgment_principles",
        "related_text_fields": ["content"],
        "join_key": "judgment_id"
    },
    "fatwa": {
        "main_table": "fatwas",
        "main_text_fields": ["authority", "topic", "facts", "application", "opinion"],
        "related_table": "fatwa_principles",
        "related_text_fields": ["content"],
        "join_key": "fatwa_id"
    },
    "law": {
        "main_table": "law_articles",
        "main_text_fields": ["original_text", "final_text"],
        "related_tables": ["law_articles", "law_promulgation_articles"],
        "related_text_fields": {
            "law_articles": ["original_text", "final_text"],
            "law_promulgation_articles": ["original_text", "final_text"]
        },
        "join_key": "law_id"
    }
}

def init_db():
    conn = get_db_connection()
    conn.autocommit = True  # needed for create table
    cur = conn.cursor()

    # create tables and indices
    with open("database_schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    cur.execute(sql)

    # populate tables
    # judgements
    judgments = parse_directory(JUDGMENT_DIR, "judgment")

    for doc in judgments:
        cur.execute("""
            SELECT id FROM judgments WHERE file_name = %s
        """, (doc["file_name"],))
        row = cur.fetchone()

        if row:
            judgment_id = row[0]
        else:
            cur.execute("""
                INSERT INTO judgments (
                    file_name, court_name, chamber_type,
                    appeal_number, judicial_year, hearing_date,
                    volume_number, part_number, page_number,
                    rule_number, reference_number,
                    authority, facts, reasons
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                doc.get("file_name"),
                doc.get("court_name"),
                doc.get("chamber_type"),
                doc.get("appeal_number"),
                doc.get("judicial_year"),
                doc.get("hearing_date"),
                doc.get("volume_number"),
                doc.get("part_number"),
                doc.get("page_number"),
                doc.get("rule_number"),
                doc.get("reference_number"),
                doc.get("authority"),
                doc.get("facts"),
                doc.get("reasons"),
            ))
            judgment_id = cur.fetchone()[0]

        # principles
        for num, text in doc.get("principles", {}).items():
            cur.execute("""
                INSERT INTO judgment_principles
                (judgment_id, principle_number, content)
                VALUES (%s,%s,%s)
                ON CONFLICT (judgment_id, principle_number) DO NOTHING
            """, (judgment_id, num, text))

    # fatwas
    fatwas = parse_directory(FATWA_DIR, "fatwa")

    for doc in fatwas:
        cur.execute("""
            SELECT id FROM fatwas WHERE fatwa_number = %s AND fatwa_date = %s
        """, (doc["fatwa_number"], doc["fatwa_date"]),) # if same fatwa_number and fatwa_date, skip
        row = cur.fetchone()

        if row:
            fatwa_id = row[0]
        else:
            cur.execute("""
                INSERT INTO fatwas (
                    file_name, fatwa_number, fatwa_date,
                    hearing_date, file_number,
                    authority, topic, facts,
                    application, opinion
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                doc.get("file_name"),
                doc.get("fatwa_number"),
                doc.get("fatwa_date"),
                doc.get("hearing_date"),
                doc.get("file_number"),
                doc.get("authority"),
                doc.get("topic"),
                doc.get("facts"),
                doc.get("application"),
                doc.get("opinion"),
            ))
            fatwa_id = cur.fetchone()[0]

        # principles
        for num, text in doc.get("principles", {}).items():
            cur.execute("""
                INSERT INTO fatwa_principles
                (fatwa_id, principle_number, content)
                VALUES (%s,%s,%s)
                ON CONFLICT (fatwa_id, principle_number) DO NOTHING
            """, (fatwa_id, num, text))

    # laws
    laws = parse_directory(LAW_DIR, "law")

    for doc in laws:
        cur.execute("""
            SELECT id FROM laws WHERE file_name = %s
        """, (doc["file_name"],))
        row = cur.fetchone()

        if row:
            law_id = row[0]
        else:
            cur.execute("""
                INSERT INTO laws (
                    file_name, law_number,
                    issue_date, publish_date,
                    subject, gazette
                ) VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                doc.get("file_name"),
                doc.get("law_number"),
                doc.get("issue_date"),
                doc.get("publish_date"),
                doc.get("subject"),
                doc.get("gazette"),
            ))
            law_id = cur.fetchone()[0]

        # articles
        for num, article in doc.get("articles", {}).items():
            cur.execute("""
                INSERT INTO law_articles (
                    law_id, article_number, is_repeated,
                    original_text, final_text, final_text_date
                ) VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (law_id, article_number, is_repeated) DO NOTHING
            """, (
                law_id,
                int(str(num).replace("_repeated", "")),
                article.get("repeated", False),
                article.get("original_text"),
                article.get("final_text"),
                article.get("final_text_date"),
            ))

        # promulgation articles
        for num, article in doc.get("promulgation_articles", {}).items():
            cur.execute("""
                INSERT INTO law_promulgation_articles (
                    law_id, article_number,
                    original_text, final_text, final_text_date
                ) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (law_id, article_number) DO NOTHING
            """, (
                law_id,
                int(str(num)),
                article.get("original_text"),
                article.get("final_text"),
                article.get("final_text_date"),
            ))

    conn.commit()
    cur.close()
    conn.close()

def get_db_connection():
    for attempt in range(100):
        try:
            conn = pg.connect(DATABASE_URL)
            print("Connected to Postgres!")
            break
        except pg.OperationalError:
            print(f"Postgres not ready yet, retrying...")
            time.sleep(3)
    else:
        raise Exception("Could not connect to Postgres after several retries.")
    conn = pg.connect(DATABASE_URL)
    return conn

app = FastAPI()
init_db()

@app.get("/documents")
def get_documents(
    type: str,
    q: str = "",
    page: int = 1,
    pageSize: int = 10
):
    type = type.lower()
    if type not in TABLE_MAP:
        raise HTTPException(
            status_code=400,
            detail="INVALID TYPE. Choose 'judgment', 'fatwa', or 'law'"
        )

    table_info = TABLE_MAP[type]
    main_table = table_info["main_table"]
    main_fields = table_info["main_text_fields"]
    join_key = table_info["join_key"]

    offset = (page - 1) * pageSize

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # if law -> two related tables
        if type == "law":
            related_tables = table_info["related_tables"]
            related_fields_map = table_info["related_text_fields"]
        else:
            related_tables = [table_info["related_table"]]
            related_fields_map = {table_info["related_table"]: table_info["related_text_fields"]}

        # query
        if q:
            conditions = []
            params = []

            # main table conditions
            main_conditions = " OR ".join([f"m.{field} ILIKE %s" for field in main_fields])
            conditions.append(main_conditions)
            params.extend([f"%{q}%"] * len(main_fields))

            # related tables conditions
            join_clauses = ""
            for idx, rtable in enumerate(related_tables):
                alias = f"r{idx}"
                join_clauses += f" LEFT JOIN {rtable} {alias} ON m.id = {alias}.{join_key} "
                rfields = related_fields_map[rtable]
                rconds = " OR ".join([f"{alias}.{f} ILIKE %s" for f in rfields])
                conditions.append(rconds)
                params.extend([f"%{q}%"] * len(rfields))

            query = f"""
                SELECT DISTINCT m.id
                FROM {main_table} m
                {join_clauses}
                WHERE {" OR ".join(conditions)}
                LIMIT %s OFFSET %s
            """
            params.extend([pageSize, offset])
        else:
            query = f"SELECT id FROM {main_table} LIMIT %s OFFSET %s"
            params = (pageSize, offset)

        cur.execute(query, params)
        main_ids = [row[0] for row in cur.fetchall()]

        if not main_ids:
            return {"page": page, "pageSize": pageSize, "returned": 0, "data": []}

        # ---- FETCH MAIN ROWS ----
        cur.execute(
            f"SELECT * FROM {main_table} WHERE id = ANY(%s)",
            (main_ids,)
        )
        main_columns = [desc[0] for desc in cur.description]
        main_rows = [dict(zip(main_columns, row)) for row in cur.fetchall()]

        results = []

        # ---- NEST RELATED DATA ----
        if type in ["judgment", "fatwa"]:
            rtable = table_info["related_table"]
            rfields = table_info["related_text_fields"]
            cur.execute(
                f"SELECT * FROM {rtable} WHERE {join_key} = ANY(%s) ORDER BY principle_number",
                (main_ids,)
            )
            related_columns = [desc[0] for desc in cur.description]
            related_rows = [dict(zip(related_columns, row)) for row in cur.fetchall()]

            related_map = {}
            for r in related_rows:
                pid = r[join_key]
                if pid not in related_map:
                    related_map[pid] = {}
                related_map[pid][r["principle_number"]] = r["content"]

            for m in main_rows:
                m["principles"] = related_map.get(m["id"], {})
                results.append(m)

        elif type == "law":
            # articles
            cur.execute(
                f"SELECT * FROM law_articles WHERE law_id = ANY(%s) ORDER BY article_number",
                (main_ids,)
            )
            article_rows = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]

            # promulgation articles
            cur.execute(
                f"SELECT * FROM law_promulgation_articles WHERE law_id = ANY(%s) ORDER BY article_number",
                (main_ids,)
            )
            prom_rows = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]

            articles_map = {}
            prom_map = {}
            for a in article_rows:
                lid = a["law_id"]
                if lid not in articles_map:
                    articles_map[lid] = {}
                key = f"{a['article_number']}_repeated" if a.get("is_repeated") else a["article_number"]
                articles_map[lid][key] = {k: v for k, v in a.items() if k not in ["id", "law_id", "article_number"]}

            for p in prom_rows:
                lid = p["law_id"]
                if lid not in prom_map:
                    prom_map[lid] = {}
                prom_map[lid][p["article_number"]] = {k: v for k, v in p.items() if k not in ["id", "law_id", "article_number"]}

            for m in main_rows:
                m["articles"] = articles_map.get(m["id"], {})
                m["promulgation_articles"] = prom_map.get(m["id"], {})
                results.append(m)

        cur.close()
        conn.close()

        return {
            "page": page,
            "pageSize": pageSize,
            "returned": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))