"""
전시회 명단 엑셀 파일에서 데이터를 읽어 SQL INSERT 문을 생성하는 모듈

필수 열:
  • 분반        → category_name (= "분반41" 형태로 자동 변환)
  • 작품명      → post_title  &  exhibition.title

선택 열:
  • 조원         → exhibition.participants
  • 담당교수     → exhibition.professor
  • 파일명       → 쉼표로 구분하여 file 테이블에 삽입
  • 썸네일 / 포스터 / 영상 열이 있으면 각각 파일 1개로 처리
    (모두 /uploads/videos/<YEAR_SEGMENT>/ 경로에 저장)

사용 예시:
    from sqlgen.main import generate_sql
    generate_sql(df,
                 cat_max=1, post_max=1, exh_max=1, file_max=1)
"""

from __future__ import annotations
import datetime as dt
import mimetypes
import os
from pathlib import Path
import pandas as pd


# 메인 기능: SQL 생성
def generate_sql(
    df: pd.DataFrame,
    *,
    cat_max: int,
    post_max: int,
    exh_max: int,
    file_max: int,
    out_path: str = "bulk_insert.sql",
    year_segment: str = "20251",
) -> None:
    """엑셀 데이터를 기반으로 SQL INSERT 문을 생성합니다.
    
    Args:
        df: 엑셀에서 읽어온 DataFrame
        cat_max: category 테이블의 현재 최대 ID (MAX(id) 값)
        post_max: post 테이블의 현재 최대 ID (MAX(id) 값)
        exh_max: exhibition 테이블의 현재 최대 ID (MAX(id) 값)
        file_max: file 테이블의 현재 최대 ID (MAX(id) 값)
        out_path: 생성할 SQL 파일 경로
        year_segment: 파일 업로드 경로의 하위 폴더명 (예: '20251')
    
    각 테이블의 새 ID는 현재 최대값 + 1부터 순차적으로 부여됩니다.
    """

    # 1. 열 매핑 및 데이터 전처리
    df = df.fillna("")

    col_alias = {
        "분반": "category_name",
        "category_name": "category_name",
        "작품명": "post_title",
        "post_title": "post_title",
        "조원": "participants",
        "participants": "participants",
        "담당교수": "professor",
        "professor": "professor",
        "파일": "file_names",
        "file_names": "file_names",
        "조": "team",
        "team": "team",
        "썸네일": "thumbnail",
        "thumbnail": "thumbnail",
        "포스터": "poster",
        "poster": "poster",
        "영상": "video",
        "video": "video",
    }
    for src, dst in col_alias.items():
        if src in df.columns and dst not in df.columns:
            df[dst] = df[src]

    required = ["category_name", "post_title"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"❌ 엑셀에 필요한 열이 없습니다: {', '.join(missing)}")

    defaults = {"participants": "", "professor": "", "file_names": ""}
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    df["category_name"] = df["category_name"].astype(str)

    # 각 행에 고유 ID 부여 (post_id)
    df["post_id"] = range(1, len(df) + 1)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ─── 1. SQL helper ─────────────────────────────────────────────
    def esc(v):
        if pd.isna(v):
            return "NULL"
        if v == "":
            return "''"
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(int(v) if isinstance(v, float) and v.is_integer() else v)
        return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"

    def build_insert(table: str, rows: list[dict]) -> str:
        if not rows:
            return ""
        cols = rows[0].keys()
        col_sql = ", ".join(f"`{c}`" for c in cols)
        val_sql = ",\n".join(
            "  (" + ", ".join(esc(r[c]) for c in cols) + ")"
            for r in rows
        )
        return f"INSERT INTO `{table}` ({col_sql}) VALUES\n{val_sql};\n"

    # 2. 기본 변수 초기화
    cat_map: dict[str, int] = {}
    post_map: dict[str, int] = {}

    cat_rows, post_rows, exh_rows, file_rows = [], [], [], []

    next_cat, next_post, next_exh, next_file = (
        cat_max,
        post_max,
        exh_max,
        file_max,
    )

    # 2-A) category
    for name in df["category_name"].unique():
        next_cat += 1
        cat_map[name] = next_cat
        cat_rows.append({"id": next_cat, "name": name})

    # 2-B) post
    for _, r in df.iterrows():
        row_id = r["post_id"]
        next_post += 1
        post_map[row_id] = next_post
        post_rows.append(
            {
                "id": next_post,
                "CategoryId": cat_map[str(r["category_name"])],
                "board_type": "exhibition",
                "createdAt": now,
                "updatedAt": now,
            }
        )

    # 2-C) exhibition (row 당 1개)
    for _, r in df.iterrows():
        next_exh += 1
        exh_rows.append(
            {
                "id": next_exh,
                "PostId": post_map[r["post_id"]],
                "title": r["post_title"],
                "team": r.get("team", ""),
                "professor": r["professor"],
                "text": "",
                "representative": "",
                "participants": r["participants"],
                "group": "작품",
                "youtubeId": 0,
                "likes": 0,
                "createdAt": now,
                "updatedAt": now,
            }
        )

    # 2-D) file  (모든 타입 → uploads/videos/<year_segment>/)
    UPLOAD_ROOT = "/uploads"
    FOLDER = "videos"

    FILE_SINGLE_COLS = {  # 열이름 → type
        "thumbnail": "thumbnail",
        "poster": "poster",
        "video": "video",
    }
    FILE_MULTI_COL = "file_names"

    def guess_mime(fname: str) -> str:
        """파일명으로부터 MIME 타입을 추측
        
        Args:
            fname: 파일명
            
        Returns:
            추측된 MIME 타입 문자열, 알 수 없는 경우 'application/octet-stream'
        """
        mt, _ = mimetypes.guess_type(fname)
        return mt or "application/octet-stream"

    for _, r in df.iterrows():
        post_id = post_map[r["post_id"]]

        # ① thumbnail / poster / video
        for col, ftype in FILE_SINGLE_COLS.items():
            fname = str(r.get(col, "")).strip()
            if fname:
                next_file += 1
                full_name = f"{UPLOAD_ROOT}/{FOLDER}/{year_segment}/{fname}"
                file_rows.append(
                    {
                        "id": next_file,
                        "PostId": post_id,
                        "name": fname,
                        "type": ftype,
                        "path": full_name,
                        "mimetype": guess_mime(fname),
                        "size": 0,
                        "createdAt": now,
                        "updatedAt": now,
                    }
                )

        # ② file_names (쉼표 분리)
        multi = str(r.get(FILE_MULTI_COL, "")).strip()
        if multi:
            for fname in filter(None, map(str.strip, multi.split("/"))):
                ext = os.path.splitext(fname)[1].lower()
                ftype = (
                    "video"
                    if ext in (".mp4", ".mov", ".webm")
                    else "thumbnail"
                    if ext in (".jpg", ".jpeg", ".png", ".gif")
                    else "file"
                )
                next_file += 1
                full_name = f"{UPLOAD_ROOT}/{FOLDER}/{year_segment}/{fname}"
                file_rows.append(
                    {   
                        "id": next_file,
                        "PostId": post_id,
                        "name": fname,
                        "type": ftype,
                        "path": full_name,
                        "mimetype": guess_mime(fname),
                        "size": 0,
                        "createdAt": now,
                        "updatedAt": now,
                    }
                )

    # 4. SQL 파일 작성
    sql = (
        f"-- AUTO-GENERATED {now}\n"
        "SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS = 0;\n"
        + build_insert("category", cat_rows)
        + build_insert("post", post_rows)
        + build_insert("exhibition", exh_rows)
        + build_insert("file", file_rows)
        + "SET FOREIGN_KEY_CHECKS = 1;\n"
    )
    Path(out_path).write_text(sql, encoding="utf-8")
