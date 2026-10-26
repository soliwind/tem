
import html
import re
import unicodedata
from html.parser import HTMLParser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# =========================================================
# 1. 페이지 설정
# =========================================================

st.set_page_config(
    page_title="Daily Box Office",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 2. API 설정
# =========================================================

KOBIS_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

# 텍스트 처리 로직을 수정했으므로 캐시 키도 변경한다.
# 이전 버전에서 저장된 영화 메타데이터를 재사용하지 않도록 한다.
TEXT_NORMALIZER_VERSION = "html-parser-v3"


# =========================================================
# 3. Secrets
# =========================================================

def read_secret(name):
    """Streamlit Secrets에서 값을 안전하게 읽는다."""
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


KOBIS_KEY = read_secret("KOBIS_KEY")
TMDB_ACCESS_TOKEN = read_secret("TMDB_ACCESS_TOKEN")
TMDB_API_KEY = read_secret("TMDB_API_KEY")


# =========================================================
# 4. HTML 태그 제거기
# =========================================================

class VisibleTextParser(HTMLParser):
    """
    HTML에서 사용자에게 표시할 텍스트만 추출한다.

    단순 정규식만 사용하는 대신 HTMLParser를 사용해서
    일반 태그, 속성이 있는 태그, 줄바꿈 태그 등을 처리한다.
    """

    BLOCK_TAGS = {
        "br", "p", "div", "li", "tr",
        "h1", "h2", "h3", "h4",
        "section", "article",
    }

    HIDDEN_TAGS = {
        "script", "style", "noscript",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in self.HIDDEN_TAGS:
            self.hidden_depth += 1
            return

        if not self.hidden_depth and tag in self.BLOCK_TAGS:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()

        if not self.hidden_depth and tag in self.BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in self.HIDDEN_TAGS:
            if self.hidden_depth > 0:
                self.hidden_depth -= 1
            return

        if not self.hidden_depth and tag in self.BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


# =========================================================
# 5. 텍스트 정리 — 핵심 수정 부분
# =========================================================

def clean_text(value):
    """
    외부 API의 텍스트를 일반 문자열로 정리한다.

    처리 순서:
    1. 유니코드 정규화
    2. HTML 엔티티 디코딩
    3. HTML 태그 제거
    4. 디코딩과 태그 제거를 반복
    5. 공백 정리

    예시:
        &amp;lt;div&amp;gt;치이카와&amp;lt;/div&amp;gt;
        <div>치이카와</div>
        &lt;div&gt;치이카와&lt;/div&gt;

    모두 최종적으로:
        치이카와
    """

    if value is None:
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\x00", "")
    text = text.replace("\ufeff", "")

    # 엔티티 디코딩과 태그 제거를 한 단계씩 반복한다.
    # 디코딩 후 새롭게 드러난 태그도 반드시 제거한다.
    for _ in range(20):
        previous = text

        text = html.unescape(text)

        # HTML 주석 제거
        text = re.sub(
            r"<!--.*?-->",
            " ",
            text,
            flags=re.DOTALL,
        )

        parser = VisibleTextParser()

        try:
            parser.feed(text)
            parser.close()
            text = "".join(parser.parts)

        except Exception:
            # 비정상 HTML이 들어와도 최소한의 정리는 시도한다.
            text = re.sub(
                r"<[^>]*>",
                " ",
                text,
            )

        # 디코딩 결과가 새 태그가 되는 경우를 포함해
        # 다음 반복에서 다시 검사할 수 있도록 한다.
        text = text.strip()

        if text == previous:
            break

    # 남은 엔티티가 텍스트 안에 더 깊이 인코딩된 경우를
    # 마지막으로 확인한다.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def safe_html_text(value):
    """
    HTML 블록 안에 동적으로 표시할 텍스트를 안전하게 변환한다.

    clean_text:
        API 데이터의 엔티티와 HTML 태그 정리

    html.escape:
        정리된 텍스트가 HTML 코드로 실행되지 않도록 처리
    """

    return html.escape(
        clean_text(value),
        quote=True,
    )


def format_number(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"


# =========================================================
# 6. 날짜 — 한국 시간 기준 어제
# =========================================================

def get_yesterday_korea():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    return now - timedelta(days=1)


target_date = get_yesterday_korea()
target_dt = target_date.strftime("%Y%m%d")
display_date = target_date.strftime("%Y.%m.%d")


# =========================================================
# 7. 디자인
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f2eb;
        color: #17212b;
    }

    .block-container {
        max-width: 1320px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    html, body, [class*="css"] {
        font-family:
            "Noto Sans KR",
            "Noto Sans",
            "Apple SD Gothic Neo",
            "Malgun Gothic",
            Arial,
            sans-serif;
    }

    .masthead {
        border-top: 1px solid #17212b;
        border-bottom: 1px solid #17212b;
        padding: 15px 0 17px;
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
        letter-spacing: .19em;
        font-weight: 700;
        color: #8a7448;
        text-transform: uppercase;
    }

    .masthead-date {
        font-size: 12px;
        letter-spacing: .08em;
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
        line-height: .94;
        font-weight: 500;
        letter-spacing: -.055em;
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

    .eyebrow {
        margin-bottom: 10px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .18em;
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
        font-family:
            "Noto Serif KR",
            Georgia,
            "Batang",
            serif;
        font-size: 27px;
        font-weight: 500;
        letter-spacing: -.04em;
    }

    .section-meta {
        font-size: 11px;
        color: #737c83;
        letter-spacing: .04em;
    }

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
        letter-spacing: .05em;
        margin-bottom: 13px;
    }

    .hero-title {
        margin: 0 0 15px;
        font-family:
            "Noto Serif KR",
            Georgia,
            "Batang",
            serif;
        font-size: clamp(30px, 4vw, 55px);
        line-height: 1.12;
        font-weight: 500;
        letter-spacing: -.045em;
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
        letter-spacing: .06em;
        text-align: center;
        padding: 20px;
    }

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
            "Batang",
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
            margin: 18px 0 0;
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
# 8. KOBIS 데이터 가져오기
# =========================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_kobis(target_dt):
    if not KOBIS_KEY:
        return {
            "ok": False,
            "error": "KOBIS_KEY_MISSING",
            "rows": [],
        }

    params = {
        "key": KOBIS_KEY,
        "targetDt": target_dt,
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

    if data.get("faultInfo"):
        return {
            "ok": False,
            "error": "KOBIS_FAULT",
            "rows": [],
        }

    rows = (
        data
        .get("boxOfficeResult", {})
        .get("dailyBoxOfficeList", [])
    )

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

if not kobis_result["ok"]:
    error_type = kobis_result["error"]

    error_messages = {
        "KOBIS_KEY_MISSING": (
            "KOBIS_KEY가 없습니다. "
            "Streamlit Secrets를 확인해주세요."
        ),
        "KOBIS_REQUEST_ERROR": (
            "KOBIS 데이터를 불러오지 못했습니다. "
            "네트워크 상태를 확인해주세요."
        ),
        "KOBIS_JSON_ERROR": (
            "KOBIS 응답을 읽을 수 없습니다."
        ),
        "KOBIS_FAULT": (
            "KOBIS API에서 오류가 반환되었습니다. "
            "API 키를 확인해주세요."
        ),
        "KOBIS_EMPTY": (
            f"{display_date} 박스오피스 데이터가 없습니다."
        ),
    }

    st.error(
        error_messages.get(
            error_type,
            "박스오피스 데이터를 불러오지 못했습니다.",
        )
    )
    st.stop()


# =========================================================
# 9. KOBIS 응답 정리
# =========================================================

records = []

for row in kobis_result["rows"]:
    try:
        rank = int(row.get("rank", 0))
        audi_cnt = int(row.get("audiCnt", 0) or 0)
        audi_acc = int(row.get("audiAcc", 0) or 0)
        screen_cnt = int(row.get("scrnCnt", 0) or 0)
        show_cnt = int(row.get("showCnt", 0) or 0)
    except (ValueError, TypeError):
        continue

    records.append({
        "rank": rank,
        "movieCd": clean_text(row.get("movieCd", "")),
        "movieNm": clean_text(row.get("movieNm", "")),
        "openDt": clean_text(row.get("openDt", "")),
        "audiCnt": audi_cnt,
        "audiAcc": audi_acc,
        "scrnCnt": screen_cnt,
        "showCnt": show_cnt,
    })

df = pd.DataFrame(records)

if df.empty:
    st.warning("표시할 박스오피스 데이터가 없습니다.")
    st.stop()

# 표와 차트에 들어가는 영화명도 한 번 더 정규화한다.
df["movieNm"] = df["movieNm"].map(clean_text)
df["openDt"] = df["openDt"].map(clean_text)

df = (
    df
    .sort_values("rank")
    .reset_index(drop=True)
)


# =========================================================
# 10. TMDB API 요청
# =========================================================

def tmdb_request(endpoint, params=None):
    if not TMDB_ACCESS_TOKEN and not TMDB_API_KEY:
        return None, "TMDB_KEY_MISSING"

    request_params = dict(params or {})
    headers = {"accept": "application/json"}

    if TMDB_ACCESS_TOKEN:
        headers["Authorization"] = (
            f"Bearer {TMDB_ACCESS_TOKEN}"
        )
    else:
        request_params["api_key"] = TMDB_API_KEY

    try:
        response = requests.get(
            f"{TMDB_API_URL}{endpoint}",
            params=request_params,
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
# 11. TMDB 영화 검색
# =========================================================

@st.cache_data(ttl=43200, show_spinner=False)
def search_tmdb_movie(movie_name, open_dt):
    movie_name = clean_text(movie_name)

    year = str(open_dt or "")[:4]

    params = {
        "query": movie_name,
        "language": "ko-KR",
        "include_adult": "false",
        "page": 1,
    }

    data, error = tmdb_request(
        "/search/movie",
        params,
    )

    if error or not data:
        return None

    candidates = []

    for movie in data.get("results", []):
        title = clean_text(movie.get("title", ""))
        original_title = clean_text(
            movie.get("original_title", "")
        )
        release_date = clean_text(
            movie.get("release_date", "")
        )
        release_year = release_date[:4]

        score = 0

        if title.casefold() == movie_name.casefold():
            score += 100

        if original_title.casefold() == movie_name.casefold():
            score += 80

        if year and release_year == year:
            score += 50

        if movie.get("poster_path"):
            score += 20

        candidates.append((score, movie))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # 캐시에 이전 버전 정보가 있어도 표시 직전에 다시 정리한다.
    return candidates[0][1]


# =========================================================
# 12. TMDB 포스터 목록에서 고해상도 이미지 선택
# =========================================================

@st.cache_data(ttl=43200, show_spinner=False)
def get_best_tmdb_poster(movie_id):
    if not movie_id:
        return None

    data, error = tmdb_request(
        f"/movie/{movie_id}/images",
        {
            "include_image_language": "ko,en,null",
        },
    )

    if error or not data:
        return None

    candidates = []

    for poster in data.get("posters", []):
        file_path = poster.get("file_path")

        if not file_path:
            continue

        try:
            width = int(poster.get("width") or 0)
            height = int(poster.get("height") or 0)
        except (ValueError, TypeError):
            continue

        if width <= 0 or height <= 0:
            continue

        ratio = width / height

        if not 0.55 <= ratio <= 0.82:
            continue

        language = poster.get("iso_639_1")

        # 해상도에 가장 큰 비중을 둔다.
        score = min(width, 4000) / 10

        if language == "ko":
            score += 120
        elif language == "en":
            score += 35
        elif language is None:
            score += 20

        candidates.append({
            "score": score,
            "file_path": file_path,
            "width": width,
            "height": height,
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return candidates[0]


# =========================================================
# 13. TMDB 상세 정보 및 줄거리
# =========================================================

@st.cache_data(ttl=43200, show_spinner=False)
def get_tmdb_details(movie_id):
    if not movie_id:
        return {}

    data, error = tmdb_request(
        f"/movie/{movie_id}",
        {"language": "ko-KR"},
    )

    if error or not data:
        return {}

    return data


# =========================================================
# 14. 포스터 이미지 다운로드
# =========================================================

def build_poster_url(file_path):
    if not file_path:
        return None

    return f"{TMDB_IMAGE_BASE}/original{file_path}"


@st.cache_data(ttl=43200, show_spinner=False)
def download_image(image_url):
    if not image_url:
        return None

    try:
        response = requests.get(
            image_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
    except requests.RequestException:
        return None

    if not response.ok:
        return None

    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    if not content_type.startswith("image/"):
        return None

    return response.content


# =========================================================
# 15. 영화 메타데이터
# =========================================================

@st.cache_data(ttl=43200, show_spinner=False)
def get_movie_metadata(
    movie_name,
    open_dt,
    normalizer_version,
):
    """
    normalizer_version은 캐시 버전 변경을 위한 인자다.
    텍스트 정리 로직을 변경하면 이 값도 변경한다.
    """

    movie = search_tmdb_movie(
        clean_text(movie_name),
        clean_text(open_dt),
    )

    if not movie:
        return {
            "matched": False,
            "poster_bytes": None,
            "overview": "",
            "tmdb_id": None,
            "poster_width": 0,
            "poster_height": 0,
        }

    movie_id = movie.get("id")
    poster = get_best_tmdb_poster(movie_id)

    poster_bytes = None
    poster_width = 0
    poster_height = 0

    if poster:
        poster_url = build_poster_url(
            poster.get("file_path")
        )

        poster_bytes = download_image(poster_url)
        poster_width = poster.get("width", 0)
        poster_height = poster.get("height", 0)

    details = get_tmdb_details(movie_id)

    # API의 줄거리는 캐시에서 읽은 이후에도 반드시 정규화한다.
    overview = clean_text(
        details.get("overview", "")
    )

    if not overview:
        overview = clean_text(
            movie.get("overview", "")
        )

    return {
        "matched": True,
        "poster_bytes": poster_bytes,
        "overview": overview,
        "tmdb_id": movie_id,
        "poster_width": poster_width,
        "poster_height": poster_height,
    }


# =========================================================
# 16. 헤더
# =========================================================

st.markdown(
    f"""
    <div class="masthead">
        <div class="masthead-top">
            <div class="masthead-kicker">
                KOBIS DAILY BOX OFFICE · KOREA
            </div>
            <div class="masthead-date">
                {safe_html_text(display_date)}
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
# 17. 보고서 제목
# =========================================================

st.markdown(
    f"""
    <div class="section-header">
        <div>
            <div class="eyebrow">Yesterday's Report</div>
            <h2 class="section-title">
                {safe_html_text(display_date)} Box Office
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
# 18. 1위 영화
# =========================================================

top_movie = df.iloc[0]

top_metadata = get_movie_metadata(
    top_movie["movieNm"],
    top_movie["openDt"],
    TEXT_NORMALIZER_VERSION,
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
                POSTER<br>NOT AVAILABLE
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
        '<div class="hero-rank">'
        'NO. 01 · DAILY BOX OFFICE'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <h2 class="hero-title">
            {safe_html_text(top_movie["movieNm"])}
        </h2>
        """,
        unsafe_allow_html=True,
    )

    overview = clean_text(
        top_metadata.get("overview", "")
    )

    if overview:
        st.markdown(
            f"""
            <p class="hero-copy">
                {safe_html_text(overview)}
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

    st.markdown(
        f"""
        <div class="hero-meta">
            개봉 {safe_html_text(top_movie["openDt"] or "-")}
            &nbsp;&nbsp;·&nbsp;&nbsp;
            {format_number(top_movie["scrnCnt"])}개 스크린
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# 19. 핵심 수치
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
# 20. TMDB 상태 안내
# =========================================================

if not TMDB_ACCESS_TOKEN and not TMDB_API_KEY:
    st.info(
        "포스터와 줄거리를 표시하려면 "
        "Secrets에 TMDB_ACCESS_TOKEN 또는 TMDB_API_KEY를 등록해주세요."
    )
elif not top_metadata.get("poster_bytes"):
    st.caption(
        "현재 1위 영화의 TMDB 포스터를 찾지 못했습니다. "
        "박스오피스 데이터는 KOBIS 기준으로 표시됩니다."
    )


# =========================================================
# 21. 포스터 선택
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
            <h2 class="section-title">Today's Selection</h2>
        </div>
        <div class="section-meta">TOP 6</div>
    </div>
    """,
    unsafe_allow_html=True,
)

poster_movies = df.head(6)
poster_cols = st.columns(6, gap="medium")

for column, (_, movie) in zip(
    poster_cols,
    poster_movies.iterrows(),
):
    metadata = get_movie_metadata(
        movie["movieNm"],
        movie["openDt"],
        TEXT_NORMALIZER_VERSION,
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
                    POSTER<br>UNAVAILABLE
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
                {safe_html_text(movie["movieNm"])}
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# 22. 관객 수 차트
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
            <h2 class="section-title">Daily Attendance</h2>
        </div>
        <div class="section-meta">ALL AVAILABLE TITLES</div>
    </div>
    """,
    unsafe_allow_html=True,
)

chart_df = (
    df[["movieNm", "audiCnt"]]
    .copy()
    .set_index("movieNm")
)

st.bar_chart(
    chart_df,
    use_container_width=True,
)


# =========================================================
# 23. 전체 순위
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
            <h2 class="section-title">Complete Ranking</h2>
        </div>
        <div class="section-meta">KOBIS DAILY BOX OFFICE</div>
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
    keyword = clean_text(ranking_search).casefold()

    filtered_df = filtered_df[
        filtered_df["movieNm"]
        .map(clean_text)
        .str.casefold()
        .str.contains(keyword, na=False)
    ]

for _, movie in filtered_df.iterrows():
    st.markdown(
        f"""
        <div class="ranking-row">
            <div class="ranking-number">
                {int(movie["rank"]):02d}
            </div>

            <div>
                <div class="ranking-title">
                    {safe_html_text(movie["movieNm"])}
                </div>
                <div class="ranking-sub">
                    개봉 {safe_html_text(movie["openDt"] or "-")}
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
# 24. CSV 다운로드
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
# 25. 출처
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
