
import re
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from zoneinfo import ZoneInfo


# =========================================================
# 1. 기본 설정
# =========================================================

st.set_page_config(
    page_title="Daily Box Office",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 2. API 주소
# =========================================================

KOBIS_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


# =========================================================
# 3. Secret 읽기
# =========================================================

def read_secret(name):
    """
    Streamlit Cloud의 Secrets에서 값을 읽는다.
    값이 없으면 빈 문자열을 반환한다.
    """
    try:
        value = st.secrets.get(name, "")
        return str(value).strip()
    except Exception:
        return ""


KOBIS_KEY = read_secret("KOBIS_KEY")

# 둘 중 하나만 있어도 작동한다.
TMDB_API_KEY = read_secret("TMDB_API_KEY")
TMDB_ACCESS_TOKEN = read_secret("TMDB_ACCESS_TOKEN")


# =========================================================
# 4. 디자인
# =========================================================

st.markdown(
    """
    <style>

    /* -----------------------------------------------------
       전체 페이지
    ----------------------------------------------------- */

    .stApp {
        background: #f5f2eb;
        color: #17212b;
    }

    .block-container {
        max-width: 1320px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    /* Streamlit 기본 헤더 공간 최소화 */
    header[data-testid="stHeader"] {
        background: transparent;
    }

    /* -----------------------------------------------------
       기본 폰트
    ----------------------------------------------------- */

    html,
    body,
    [class*="css"] {
        font-family:
            "Noto Sans KR",
            "Noto Sans",
            "Apple SD Gothic Neo",
            "Malgun Gothic",
            Arial,
            sans-serif;
    }

    /* 제목 계열은 세리프 계열 */
    .cinema-title,
    .hero-title,
    .section-title {
        font-family:
            "Noto Serif KR",
            "Noto Serif",
            Georgia,
            "Batang",
            serif;
    }

    /* -----------------------------------------------------
       헤더
    ----------------------------------------------------- */

    .masthead {
        border-top: 1px solid #17212b;
        border-bottom: 1px solid #17212b;
        padding: 15px 0 17px 0;
        margin-bottom: 42px;
    }

    .masthead-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
        margin-bottom: 24px;
    }

    .masthead-kicker {
        font-size: 11px;
        letter-spacing: 0.19em;
        font-weight: 700;
        color: #8a7448;
        text-transform: uppercase;
    }

    .masthead-date {
        font-size: 12px;
        letter-spacing: 0.08em;
        color: #68727a;
    }

    .masthead-main {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 40px;
    }

    .masthead-title {
        margin: 0;
        font-family:
            "Noto Serif KR",
            "Noto Serif",
            Georgia,
            "Batang",
            serif;
        font-size: clamp(42px, 6vw, 78px);
        line-height: 0.94;
        font-weight: 500;
        letter-spacing: -0.055em;
        color: #17212b;
    }

    .masthead-subtitle {
        max-width: 390px;
        margin: 0 0 5px auto;
        font-size: 13px;
        line-height: 1.75;
        color: #68727a;
        text-align: right;
        word-break: keep-all;
    }

    /* -----------------------------------------------------
       공통
    ----------------------------------------------------- */

    .eyebrow {
        margin-bottom: 10px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.18em;
        color: #9b7b3f;
        text-transform: uppercase;
    }

    .hairline {
        height: 1px;
        background: #d4cec1;
        margin: 34px 0;
    }

    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 20px;
        margin-bottom: 18px;
        border-bottom: 1px solid #17212b;
        padding-bottom: 11px;
    }

    .section-title {
        margin: 0;
        font-size: 27px;
        font-weight: 500;
        letter-spacing: -0.04em;
    }

    .section-meta {
        font-size: 11px;
        color: #737c83;
        letter-spacing: 0.04em;
    }

    /* -----------------------------------------------------
       1위 영화
    ----------------------------------------------------- */

    .hero-wrap {
        background: #eeeae1;
        border-top: 1px solid #17212b;
        border-bottom: 1px solid #17212b;
        padding: 30px;
    }

    .hero-rank {
        font-family: Georgia, serif;
        font-size: 15px;
        color: #9b7b3f;
        letter-spacing: 0.05em;
        margin-bottom: 13px;
    }

    .hero-title {
        margin: 0 0 15px 0;
        font-size: clamp(30px, 4vw, 55px);
        line-height: 1.08;
        font-weight: 500;
        letter-spacing: -0.045em;
        overflow-wrap: anywhere;
        word-break: keep-all;
    }

    .hero-copy {
        margin: 0;
        color: #626b72;
        font-size: 13px;
        line-height: 1.85;
        word-break: keep-all;
    }

    .hero-meta {
        margin-top: 19px;
        padding-top: 14px;
        border-top: 1px solid #d2ccc0;
        color: #707980;
        font-size: 11px;
    }

    /* -----------------------------------------------------
       포스터
    ----------------------------------------------------- */

    .poster-caption {
        margin-top: 10px;
        font-size: 12px;
        line-height: 1.55;
        color: #3d474e;
        word-break: keep-all;
    }

    .poster-rank {
        font-family: Georgia, serif;
        color: #9b7b3f;
        font-size: 12px;
        margin-right: 5px;
    }

    .poster-empty {
        display: flex;
        align-items: center;
        justify-content: center;
        aspect-ratio: 2 / 3;
        background: #e4dfd5;
        color: #8b8a83;
        font-size: 11px;
        letter-spacing: 0.06em;
        text-align: center;
        padding: 20px;
    }

    /* -----------------------------------------------------
       필터 영역
    ----------------------------------------------------- */

    .filter-label {
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.15em;
        color: #817b70;
        margin-bottom: 7px;
    }

    /* -----------------------------------------------------
       순위 리스트
    ----------------------------------------------------- */

    .ranking-row {
        display: grid;
        grid-template-columns: 60px minmax(0, 1fr) 130px 110px;
        align-items: center;
        gap: 18px;
        padding: 15px 0;
        border-bottom: 1px solid #d8d2c6;
    }

    .ranking-number {
        font-family: Georgia, serif;
        font-size: 22px;
        color: #9b7b3f;
    }

    .ranking-title {
        font-family:
            "Noto Serif KR",
            Georgia,
            serif;
        font-size: 17px;
        color: #202b34;
        overflow-wrap: anywhere;
        word-break: keep-all;
    }

    .ranking-sub {
        margin-top: 4px;
        font-size: 10px;
        color: #858b8f;
    }

    .ranking-value {
        text-align: right;
        font-size: 13px;
        color: #39434a;
    }

    /* -----------------------------------------------------
       모바일 대응
    ----------------------------------------------------- */

    @media (max-width: 760px) {

        .block-container {
            padding-top: 1.2rem;
        }

        .masthead-main {
            display: block;
        }

        .masthead-title {
            font-size: 48px;
        }

        .masthead-subtitle {
            margin: 18px 0 0 0;
            text-align: left;
        }

        .hero-wrap {
            padding: 20px;
        }

        .ranking-row {
            grid-template-columns: 42px minmax(0, 1fr);
        }

        .ranking-value {
            display: none;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 5. 텍스트 정리
# =========================================================

def clean_text(text):
    """
    HTML 태그와 HTML 특수문자를 제거한다.
    """
    if not text:
        return ""

    text = unescape(str(text))

    # <div>, <br>, <p> 등의 태그 제거
    text = re.sub(r"<[^>]+>", " ", text)

    # 연속 공백 제거
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def format_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


# =========================================================
# 6. 날짜
# =========================================================

def get_yesterday_korea():
    """
    서버 위치가 아니라 한국 시간 기준으로 어제를 계산한다.
    """
    korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
    return korea_now - timedelta(days=1)


target_date = get_yesterday_korea()
target_dt = target_date.strftime("%Y%m%d")
display_date = target_date.strftime("%Y.%m.%d")


# =========================================================
# 7. KOBIS
# =========================================================

@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_kobis(target_dt):
    """
    KOBIS 일일 박스오피스를 가져온다.

    KOBIS의 일일 박스오피스 API는 영화 순위와
    관객 수 등의 국내 박스오피스 데이터를 담당한다.
    """

    if not KOBIS_KEY:
        return {
            "ok": False,
            "error": "KOBIS_KEY_MISSING",
            "rows": [],
        }

    params = {
        "key": KOBIS_KEY,
        "targetDt": target_dt,
        # 5편이 아니라 더 많은 영화를 받는다.
        "itemPerPage": 100,
    }

    try:
        response = requests.get(
            KOBIS_URL,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException:
        return {
            "ok": False,
            "error": "KOBIS_REQUEST_ERROR",
            "rows": [],
        }

    except ValueError:
        return {
            "ok": False,
            "error": "KOBIS_JSON_ERROR",
            "rows": [],
        }

    # KOBIS는 인증 오류 등도 HTTP 200으로 반환할 수 있다.
    fault_info = data.get("faultInfo")

    if fault_info:
        return {
            "ok": False,
            "error": "KOBIS_FAULT",
            "fault": fault_info,
            "rows": [],
        }

    result = data.get("boxOfficeResult", {})
    rows = result.get("dailyBoxOfficeList", [])

    if not rows:
        return {
            "ok": False,
            "error": "KOBIS_EMPTY",
            "rows": [],
        }

    return {
        "ok": True,
        "error": "",
        "rows": rows,
    }


kobis_result = fetch_kobis(target_dt)


# =========================================================
# 8. TMDB 요청
# =========================================================

def tmdb_request(endpoint, params=None):
    """
    TMDB 요청을 한 곳에서 처리한다.

    TMDB_ACCESS_TOKEN이 있으면 Bearer 인증을 사용한다.
    없으면 TMDB_API_KEY를 사용한다.
    """

    if not TMDB_ACCESS_TOKEN and not TMDB_API_KEY:
        return None, "TMDB_KEY_MISSING"

    url = f"{TMDB_API_URL}{endpoint}"

    params = dict(params or {})

    headers = {
        "accept": "application/json",
    }

    # Access Token을 우선 사용한다.
    if TMDB_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {TMDB_ACCESS_TOKEN}"

    elif TMDB_API_KEY:
        params["api_key"] = TMDB_API_KEY

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15,
        )

    except requests.RequestException:
        return None, "TMDB_REQUEST_ERROR"

    if response.status_code == 401:
        return None, "TMDB_AUTH_ERROR"

    if response.status_code == 429:
        return None, "TMDB_RATE_LIMIT"

    if not response.ok:
        return None, f"TMDB_HTTP_{response.status_code}"

    try:
        return response.json(), ""

    except ValueError:
        return None, "TMDB_JSON_ERROR"


# =========================================================
# 9. TMDB 영화 검색
# =========================================================

@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def search_tmdb_movie(movie_name, open_dt):
    """
    KOBIS 영화명을 기준으로 TMDB 영화를 찾는다.

    제목 + 개봉연도를 함께 고려해서
    같은 제목의 다른 작품이 선택될 가능성을 줄인다.
    """

    year = ""

    if open_dt:
        try:
            year = str(open_dt)[:4]
        except Exception:
            year = ""

    # 1차: 한국어 제목 검색
    data, error = tmdb_request(
        "/search/movie",
        {
            "query": movie_name,
            "language": "ko-KR",
            "include_adult": "false",
            "page": 1,
        },
    )

    if error or not data:
        return None

    results = data.get("results", [])

    if not results:
        return None

    # -----------------------------------------------------
    # 검색 결과를 점수화한다.
    # -----------------------------------------------------

    normalized_name = clean_text(movie_name).lower()

    candidates = []

    for movie in results:
        title_ko = clean_text(movie.get("title", ""))
        original_title = clean_text(movie.get("original_title", ""))

        release_date = movie.get("release_date", "") or ""
        release_year = release_date[:4]

        score = 0

        # 제목 정확 일치
        if title_ko.lower() == normalized_name:
            score += 100

        if original_title.lower() == normalized_name:
            score += 80

        # 개봉연도 일치
        if year and release_year == year:
            score += 50

        # 포스터가 있는 영화 우선
        if movie.get("poster_path"):
            score += 20

        # 한국어 제목이 있는 경우
        if title_ko:
            score += 5

        candidates.append((score, movie))

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return candidates[0][1]


# =========================================================
# 10. TMDB 포스터 후보 선택
# =========================================================

@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_best_tmdb_poster(movie_id):
    """
    TMDB 영화의 포스터 목록을 직접 조회한다.

    단순 poster_path 하나를 사용하는 대신,
    실제 포스터 후보의 width / height / 언어를 비교한다.
    """

    if not movie_id:
        return None

    data, error = tmdb_request(
        f"/movie/{movie_id}/images",
        {
            # 한국어를 우선하고 영어 및 언어 없음도 허용한다.
            "include_image_language": "ko,en,null",
        },
    )

    if error or not data:
        return None

    posters = data.get("posters", [])

    if not posters:
        return None

    candidates = []

    for poster in posters:
        file_path = poster.get("file_path")

        if not file_path:
            continue

        width = int(poster.get("width") or 0)
        height = int(poster.get("height") or 0)

        if width <= 0 or height <= 0:
            continue

        language = poster.get("iso_639_1")

        # 포스터답지 않은 비율은 제외한다.
        ratio = width / height

        if ratio < 0.55 or ratio > 0.82:
            continue

        score = 0

        # -------------------------------------------------
        # 해상도
        # -------------------------------------------------

        # 가장 중요한 요소
        score += min(width, 3000) / 10

        # -------------------------------------------------
        # 언어
        # -------------------------------------------------

        if language == "ko":
            score += 120

        elif language == "en":
            score += 35

        elif language is None:
            score += 20

        # -------------------------------------------------
        # 세로 해상도가 충분한 이미지 선호
        # -------------------------------------------------

        if height >= 2000:
            score += 70

        elif height >= 1500:
            score += 45

        elif height >= 1000:
            score += 20

        candidates.append(
            {
                "score": score,
                "file_path": file_path,
                "width": width,
                "height": height,
                "language": language,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return candidates[0]


# =========================================================
# 11. TMDB 줄거리
# =========================================================

@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_tmdb_details(movie_id):
    """
    한국어 줄거리를 가져온다.
    """

    if not movie_id:
        return {}

    data, error = tmdb_request(
        f"/movie/{movie_id}",
        {
            "language": "ko-KR",
        },
    )

    if error or not data:
        return {}

    return data


# =========================================================
# 12. 포스터 URL 만들기
# =========================================================

def build_poster_url(file_path):
    """
    선택된 포스터의 원본 이미지를 사용한다.

    TMDB는 base URL + file size + file path로
    이미지 URL을 구성한다.
    """

    if not file_path:
        return None

    return f"{TMDB_IMAGE_BASE}/original{file_path}"


# =========================================================
# 13. 포스터 다운로드
# =========================================================

@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def download_image(image_url):
    """
    실제 이미지 응답인지 확인하고 bytes로 가져온다.
    """

    if not image_url:
        return None

    try:
        response = requests.get(
            image_url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
        )

        if not response.ok:
            return None

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if not content_type.startswith("image/"):
            return None

        return response.content

    except requests.RequestException:
        return None


# =========================================================
# 14. 영화별 TMDB 정보 통합
# =========================================================

@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_movie_metadata(movie_name, open_dt):
    """
    KOBIS 영화 한 편에 대한 TMDB 정보를 가져온다.
    """

    movie = search_tmdb_movie(
        movie_name,
        open_dt,
    )

    if not movie:
        return {
            "matched": False,
            "poster_url": None,
            "poster_bytes": None,
            "overview": "",
            "tmdb_id": None,
            "poster_width": 0,
            "poster_height": 0,
        }

    movie_id = movie.get("id")

    poster = get_best_tmdb_poster(movie_id)

    poster_url = None
    poster_bytes = None
    poster_width = 0
    poster_height = 0

    if poster:
        poster_url = build_poster_url(
            poster.get("file_path")
        )

        poster_width = poster.get("width", 0)
        poster_height = poster.get("height", 0)

        poster_bytes = download_image(
            poster_url
        )

    details = get_tmdb_details(movie_id)

    overview = clean_text(
        details.get("overview", "")
    )

    # TMDB 한국어 줄거리가 없는 경우
    # 검색 결과의 overview를 한 번 더 확인한다.
    if not overview:
        overview = clean_text(
            movie.get("overview", "")
        )

    return {
        "matched": True,
        "poster_url": poster_url,
        "poster_bytes": poster_bytes,
        "overview": overview,
        "tmdb_id": movie_id,
        "poster_width": poster_width,
        "poster_height": poster_height,
    }


# =========================================================
# 15. KOBIS 오류 처리
# =========================================================

if not kobis_result["ok"]:

    error_type = kobis_result["error"]

    if error_type == "KOBIS_KEY_MISSING":
        st.error(
            "KOBIS_KEY가 없습니다. "
            "Streamlit Cloud의 Secrets에 KOBIS_KEY를 등록해주세요."
        )

    elif error_type == "KOBIS_FAULT":
        st.error(
            "KOBIS API에서 오류가 반환되었습니다. "
            "API 키와 요청 날짜를 확인해주세요."
        )

    elif error_type == "KOBIS_EMPTY":
        st.warning(
            f"{display_date} 박스오피스 데이터가 없습니다."
        )

    else:
        st.error(
            "KOBIS 데이터를 불러오지 못했습니다. "
            "잠시 후 다시 접속해주세요."
        )

    st.stop()


# =========================================================
# 16. KOBIS 데이터 정리
# =========================================================

rows = kobis_result["rows"]

records = []

for row in rows:

    try:
        rank = int(row.get("rank", 0))
    except Exception:
        rank = 0

    records.append(
        {
            "rank": rank,
            "movieCd": row.get("movieCd", ""),
            "movieNm": clean_text(row.get("movieNm", "")),
            "openDt": row.get("openDt", ""),
            "audiCnt": int(row.get("audiCnt", 0) or 0),
            "audiAcc": int(row.get("audiAcc", 0) or 0),
            "scrnCnt": int(row.get("scrnCnt", 0) or 0),
            "showCnt": int(row.get("showCnt", 0) or 0),
            "salesAmt": int(row.get("salesAmt", 0) or 0),
        }
    )

df = pd.DataFrame(records)

if df.empty:
    st.warning("표시할 박스오피스 데이터가 없습니다.")
    st.stop()

df = df.sort_values("rank").reset_index(drop=True)


# =========================================================
# 17. 헤더
# =========================================================

st.markdown(
    f"""
    <div class="masthead">

        <div class="masthead-top">
            <div class="masthead-kicker">
                KOBIS DAILY BOX OFFICE · KOREA
            </div>

            <div class="masthead-date">
                {display_date}
            </div>
        </div>

        <div class="masthead-main">

            <h1 class="masthead-title">
                Daily<br>Box Office
            </h1>

            <p class="masthead-subtitle">
                하루 동안 극장에서 가장 많이 선택된 영화들.
                <br>
                한국 영화관 박스오피스를 한 장의 지면처럼 정리합니다.
            </p>

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 18. 데이터 안내
# =========================================================

st.markdown(
    f"""
    <div class="section-header">
        <div>
            <div class="eyebrow">Yesterday's Report</div>
            <h2 class="section-title">
                {display_date} Box Office
            </h2>
        </div>

        <div class="section-meta">
            {len(df)} MOVIES · KOBIS
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 19. 1위
# =========================================================

top_movie = df.iloc[0]

top_metadata = get_movie_metadata(
    top_movie["movieNm"],
    top_movie["openDt"],
)


hero_col1, hero_col2 = st.columns(
    [0.9, 1.5],
    gap="large",
)


with hero_col1:

    if top_metadata.get("poster_bytes"):

        st.image(
            top_metadata["poster_bytes"],
            width=420,
        )

    else:

        st.markdown(
            """
            <div class="poster-empty">
                POSTER<br>
                NOT AVAILABLE
            </div>
            """,
            unsafe_allow_html=True,
        )


with hero_col2:

    st.markdown(
        '<div class="hero-wrap">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="hero-rank">NO. 01 · DAILY BOX OFFICE</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <h2 class="hero-title">
            {clean_text(top_movie["movieNm"])}
        </h2>
        """,
        unsafe_allow_html=True,
    )

    if top_metadata.get("overview"):

        st.markdown(
            f"""
            <p class="hero-copy">
                {clean_text(top_metadata["overview"])}
            </p>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
            <p class="hero-copy">
                등록된 한국어 줄거리 정보가 없습니다.
            </p>
            """,
            unsafe_allow_html=True,
        )

    open_date = top_movie["openDt"] or "-"

    st.markdown(
        f"""
        <div class="hero-meta">
            개봉 {open_date}
            &nbsp;&nbsp;·&nbsp;&nbsp;
            {format_number(top_movie["scrnCnt"])}개 스크린
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# 20. 핵심 수치
# =========================================================

st.markdown(
    '<div class="hairline"></div>',
    unsafe_allow_html=True,
)

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        "어제 관객",
        f'{format_number(top_movie["audiCnt"])}명',
    )

with metric2:
    st.metric(
        "누적 관객",
        f'{format_number(top_movie["audiAcc"])}명',
    )

with metric3:
    st.metric(
        "스크린 수",
        f'{format_number(top_movie["scrnCnt"])}개',
    )


# =========================================================
# 21. TMDB 상태 안내
# =========================================================

if not TMDB_ACCESS_TOKEN and not TMDB_API_KEY:

    st.info(
        "TMDB 포스터와 한국어 줄거리를 사용하려면 "
        "Secrets에 TMDB_ACCESS_TOKEN 또는 TMDB_API_KEY를 등록해주세요."
    )

elif TMDB_ACCESS_TOKEN or TMDB_API_KEY:

    # 실제 1위 포스터 매칭이 실패했을 때만 안내
    if not top_metadata.get("poster_bytes"):

        st.caption(
            "현재 1위 영화의 TMDB 포스터를 찾지 못했습니다. "
            "박스오피스 데이터는 KOBIS 기준으로 정상 표시됩니다."
        )


# =========================================================
# 22. 주요 포스터
# =========================================================

st.markdown(
    '<div class="hairline"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-header">
        <div>
            <div class="eyebrow">Selected Titles</div>
            <h2 class="section-title">
                Today's Selection
            </h2>
        </div>

        <div class="section-meta">
            TOP 6
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# 1위 제외하고 2~6위
poster_movies = df.head(6)

poster_cols = st.columns(
    6,
    gap="medium",
)

for column, (_, movie) in zip(
    poster_cols,
    poster_movies.iterrows(),
):

    metadata = get_movie_metadata(
        movie["movieNm"],
        movie["openDt"],
    )

    with column:

        if metadata.get("poster_bytes"):

            st.image(
                metadata["poster_bytes"],
                use_container_width=True,
            )

        else:

            st.markdown(
                """
                <div class="poster-empty">
                    POSTER<br>
                    UNAVAILABLE
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="poster-caption">
                <span class="poster-rank">
                    {int(movie["rank"]):02d}
                </span>
                {clean_text(movie["movieNm"])}
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# 23. 관객 수 차트
# =========================================================

st.markdown(
    '<div class="hairline"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-header">
        <div>
            <div class="eyebrow">Audience</div>
            <h2 class="section-title">
                Daily Attendance
            </h2>
        </div>

        <div class="section-meta">
            ALL AVAILABLE TITLES
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


chart_df = (
    df[
        [
            "movieNm",
            "audiCnt",
        ]
    ]
    .copy()
)

chart_df = chart_df.set_index("movieNm")

st.bar_chart(
    chart_df,
    use_container_width=True,
)


# =========================================================
# 24. 전체 순위
# =========================================================

st.markdown(
    '<div class="hairline"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-header">
        <div>
            <div class="eyebrow">Full Report</div>
            <h2 class="section-title">
                Complete Ranking
            </h2>
        </div>

        <div class="section-meta">
            KOBIS DAILY BOX OFFICE
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


ranking_search = st.text_input(
    "영화 검색",
    placeholder="영화 제목을 입력하세요",
    label_visibility="collapsed",
)


filtered_df = df.copy()

if ranking_search.strip():

    keyword = ranking_search.strip().lower()

    filtered_df = filtered_df[
        filtered_df["movieNm"]
        .str.lower()
        .str.contains(
            keyword,
            na=False,
        )
    ]


# ---------------------------------------------------------
# 전체 순위 표시
# ---------------------------------------------------------

for _, movie in filtered_df.iterrows():

    rank = int(movie["rank"])

    st.markdown(
        f"""
        <div class="ranking-row">

            <div class="ranking-number">
                {rank:02d}
            </div>

            <div>
                <div class="ranking-title">
                    {clean_text(movie["movieNm"])}
                </div>

                <div class="ranking-sub">
                    개봉 {movie["openDt"] or "-"}
                    &nbsp;·&nbsp;
                    {format_number(movie["scrnCnt"])} screens
                </div>
            </div>

            <div class="ranking-value">
                {format_number(movie["audiCnt"])}명
            </div>

            <div class="ranking-value">
                누적 {format_number(movie["audiAcc"])}명
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 25. CSV 다운로드
# =========================================================

st.markdown(
    '<div class="hairline"></div>',
    unsafe_allow_html=True,
)

download_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
        "showCnt",
    ]
].copy()

download_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "일일관객수",
    "누적관객수",
    "스크린수",
    "상영횟수",
]

csv_data = download_df.to_csv(
    index=False,
    encoding="utf-8-sig",
)

st.download_button(
    label="박스오피스 CSV 저장",
    data=csv_data,
    file_name=f"boxoffice_{target_dt}.csv",
    mime="text/csv",
)


# =========================================================
# 26. 출처
# =========================================================

st.markdown(
    """
    <div style="
        margin-top: 30px;
        padding-top: 18px;
        border-top: 1px solid #d4cec1;
        color: #7a7f82;
        font-size: 10px;
        line-height: 1.7;
    ">
        BOX OFFICE DATA · KOBIS
        <br>
        POSTERS & MOVIE INFORMATION · TMDB
        <br>
        This product uses the TMDB API but is not endorsed or certified by TMDB.
    </div>
    """,
    unsafe_allow_html=True,
)
