# eeegp-sqlgen: 전전 졸업작품 발표회 엑셀 기반 SQL 생성기

전기전자컴퓨터공학부 졸업작품 발표회용 명단 엑셀 파일을 기반으로
`category`, `post`, `exhibition`, `file` 테이블에 대한 `SQL INSERT` 문 자동 생성 기능 제공


## 설치 방법 (uv 기반)

### 1. 가상환경 생성

```bash
uv venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### 2. 개발 모드 설치

```bash
uv pip install -e .
```

- 의존성 자동 설치
- `egg-info` 디렉토리는 `.gitignore`를 통해 무시 권장


## 사용법

### query console을 이용한 max id 조회

```sql
SELECT
    (SELECT MAX(id) FROM year)       AS year_max;
    (SELECT MAX(id) FROM category)   AS cat_max,
    (SELECT MAX(id) FROM post)       AS post_max,
    (SELECT MAX(id) FROM exhibition) AS exh_max,
    (SELECT MAX(id) FROM file)       AS file_max,
```

### CLI 사용

```bash
# db max id 지정 / 출력 SQL 파일 지정 / 연도 세그먼트 지정
eeegp 명단.xlsx --year-max 7 --cat-max 10 --post-max 20 --exh-max 30 --file-max 40 -o output.sql --year 20252
```

### Python API 사용

```python
import pandas as pd
from eeegp_sqlgen.main import generate_sql

df = pd.read_excel("명단.xlsx")

generate_sql(
    df,
    year_max=7,  # 현재 year 테이블의 최대 ID
    cat_max=10,  # 현재 category 테이블의 최대 ID
    post_max=20,  # 현재 post 테이블의 최대 ID
    exh_max=30,  # 현재 exhibition 테이블의 최대 ID
    file_max=40,  # 현재 file 테이블의 최대 ID
    out_path="output.sql",
    year_segment="20251"
)
```


## 엑셀 파일 양식

### 필수 열

| 열 이름                     | 설명                      |
| --------------------------- | ------------------------- |
| `분반` 또는 `category_name` | 분반 정보 (`"분반41"` 등) |
| `작품명` 또는 `post_title`  | 작품 제목                 |

### 선택 열

| 열 이름                     | 설명                             |
| --------------------------- | -------------------------------- |
| `조원` 또는 `participants`  | 참여 학생 명단                   |
| `담당교수` 또는 `professor` | 담당 교수 이름                   |
| `파일명` 또는 `file_names`  | 슬래시(`/`)로 구분된 다중 파일명 |
| `thumbnail`                 | 썸네일 이미지 파일명             |
| `poster`                    | 포스터 이미지 파일명             |
| `video`                     | 영상 파일 파일명                 |


## 정리 방법

빌드 캐시 및 임시 파일 제거:

```bash
find . -type d -name "__pycache__" -exec rm -r {} +
rm -rf *.egg-info build dist
```


## 참고 사항

- `uv pip install . --system` 명령어를 통해 전역 설치 가능하나, 가상환경 사용 권장
- 출력 SQL 파일은 UTF-8 인코딩으로 저장됨
- 엑셀 입력 파일은 `.xlsx` 형식만 지원
