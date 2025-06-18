import argparse
import pandas as pd
from eeegp_sqlgen.main import generate_sql


def main():
    parser = argparse.ArgumentParser(description="엑셀 파일에서 SQL INSERT 문을 생성합니다.")
    parser.add_argument("excel", help="명단 엑셀 파일(.xlsx)")
    parser.add_argument("--cat-max", type=int, default=0, help="category 테이블의 현재 최대 ID")
    parser.add_argument("--post-max", type=int, default=0, help="post 테이블의 현재 최대 ID")
    parser.add_argument("--exh-max", type=int, default=0, help="exhibition 테이블의 현재 최대 ID")
    parser.add_argument("--file-max", type=int, default=0, help="file 테이블의 현재 최대 ID")
    parser.add_argument("-o", "--out", default="bulk_insert.sql", help="출력 SQL 파일 경로")
    parser.add_argument("--year", default="20251", help="파일 경로의 연도 세그먼트")
    args = parser.parse_args()

    df = pd.read_excel(args.excel)
    generate_sql(
        df,
        cat_max=args.cat_max,
        post_max=args.post_max,
        exh_max=args.exh_max,
        file_max=args.file_max,
        out_path=args.out,
        year_segment=args.year,
    )
    print(f"✅ SQL 생성 완료: {args.out}")
