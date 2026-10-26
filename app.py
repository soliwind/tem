
import html
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# ============================================================
# 1. 기본 설정
# ============================================================

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

KOBIS_API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)

KOBIS_WEB_DAILY_URL = (
    "https://www.kobis.or.kr/kobis/business/main/searchMainDailyBoxOffice.do"
)

KOBIS_SITE_URL = "https://www.kobis.or.kr"

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie"

# 일반 영화 카드용
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"

# 1위 영화의 큰 포스터용
TMDB_IMAGE_LARGE_BASE = "https://image.tmdb.org/t/p/w1280"


# ============================================================
# 2. 디자인
#
# 컨셉: Cinema Journal
#
# 따뜻한 아이보리 + 딥 네이비 + 무광 골드
# 세리프 제목 + 산세리프 데이터
# 카드 느낌을 줄이고 영화 잡지/프로그램북 분위기를 냅니다.
# ============================================================

st.markdown(
    """
    <style>

    :root {
        --paper: #F5F2EB;
        --paper-dark: #ECE7DD;
        --card: #FFFEFB;

        --ink: #14212B;
        --ink-soft: #39454D;
        --muted: #737A7D;

        --gold: #B99752;
        --gold-light: #D4C19A;

        --line: #D8D1C4;
        --line-dark: #BFB6A7;
    }


    /* --------------------------------------------------------
       전체 페이지
    -------------------------------------------------------- */

    .stApp {
        background: var(--paper);
        color: var(--ink);
    }

    .block-container {
        max-width: 1260px;
        padding-top: 2.8rem;
        padding-bottom: 4rem;
    }


    /* --------------------------------------------------------
       폰트
       제목은 세리프,
       데이터와 본문은 산세리프를 사용합니다.
    -------------------------------------------------------- */

    html,
    body,
    [class*="css"] {
        font-family:
            "Pretendard",
            "Noto Sans KR",
            "Apple SD Gothic Neo",
            "Malgun Gothic",
            sans-serif;
    }

    h1,
    h2,
    h3 {
        color: var(--ink) !important;
        font-family:
            "Noto Serif KR",
            "Nanum Myeongjo",
            "Batang",
            Georgia,
            serif !important;
        letter-spacing: -0.055em !important;
    }

    h1 {
        font-size: clamp(2.3rem, 5vw, 3.8rem) !important;
        line-height: 1.12 !important;
        font-weight: 650 !important;
    }

    h2 {
        font-size: 1.65rem !important;
        line-height: 1.25 !important;
        font-weight: 650 !important;
    }

    h3 {
        font-size: 1.2rem !important;
        font-weight: 650 !important;
    }


    /* --------------------------------------------------------
       헤더
    -------------------------------------------------------- */

    .journal-name {
        font-size: 0.68rem;
        font-weight: 750;
        letter-spacing: 0.22em;
        color: var(--gold);
        margin-bottom: 0.75rem;
        text-transform: uppercase;
    }

    .journal-description {
        color: var(--muted);
        font-size: 0.9rem;
        letter-spacing: -0.01em;
        margin-top: -0.7rem;
        margin-bottom: 1.8rem;
    }

    .date-line {
        color: var(--ink-soft);
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        margin-top: 0.5rem;
    }

    .gold-rule {
        width: 100%;
        height: 2px;
        background: var(--gold);
        margin: 0.3rem 0 0.45rem 0;
    }

    .thin-rule {
        width: 100%;
        height: 1px;
        background: var(--line);
        margin: 0.7rem 0 2rem 0;
    }


    /* --------------------------------------------------------
       섹션 제목
    -------------------------------------------------------- */

    .section-number {
        color: var(--gold);
        font-size: 0.66rem;
        font-weight: 800;
        letter-spacing: 0.2em;
        margin-bottom: 0.25rem;
    }

    .section-title {
        color: var(--ink);
        font-family:
            "Noto Serif KR",
            "Nanum Myeongjo",
            "Batang",
            Georgia,
            serif;
        font-size: 1.55rem;
        font-weight: 650;
        letter-spacing: -0.045em;
        margin-bottom: 1.15rem;
    }


    /* --------------------------------------------------------
       1위 영화
       일반적인 카드 대신 영화 저널의 메인 기사처럼 만듭니다.
    -------------------------------------------------------- */

    .hero-frame {
        border-top: 1px solid var(--ink);
        border-bottom: 1px solid var(--line-dark);
        padding: 1.35rem 0 1.4rem 0;
        margin-bottom: 1.3rem;
    }

    .hero-rank {
        color: var(--gold);
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        margin-bottom: 0.5rem;
    }

    .hero-meta {
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.7;
        margin-bottom: 1.1rem;
    }

    .hero-description {
        color: var(--ink-soft);
        font-size: 0.91rem;
        line-height: 1.9;
        max-width: 650px;
    }

    .hero-poster img {
        width: 100%;
        display: block;
    }


    /* --------------------------------------------------------
       숫자 지표
    -------------------------------------------------------- */

    .stat-box {
        border-top: 1px solid var(--line-dark);
        border-bottom: 1px solid var(--line);
        padding: 0.85rem 0 0.9rem 0;
    }

    .stat-label {
        color: var(--muted);
        font-size: 0.68rem;
        letter-spacing: 0.12em;
        font-weight: 750;
        margin-bottom: 0.3rem;
    }

    .stat-value {
        color: var(--ink);
        font-size: 1.18rem;
        font-weight: 720;
        font-variant-numeric: tabular-nums;
    }


    /* --------------------------------------------------------
       영화 목록
    -------------------------------------------------------- */

    .film-index {
        color: var(--gold);
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 0.15em;
        margin-top: 0.65rem;
    }

    .film-title {
        color: var(--ink);
        font-family:
            "Noto Serif KR",
            "Nanum Myeongjo",
            "Batang",
            Georgia,
            serif;
        font-size: 1rem;
        font-weight: 650;
        line-height: 1.5;
        letter-spacing: -0.025em;
        margin: 0.2rem 0;
        overflow-wrap: anywhere;
    }

    .film-meta {
        color: var(--muted);
        font-size: 0.72rem;
        line-height: 1.6;
    }

    .poster-placeholder {
        width: 100%;
        aspect-ratio: 2 / 3;
        display: flex;
        align-items: center;
        justify-content: center;

        background: var(--paper-dark);
        border: 1px solid var(--line);

        color: var(--muted);
        font-size: 0.72rem;
        letter-spacing: 0.03em;
        text-align: center;
    }


    /* --------------------------------------------------------
       Streamlit 기본 카드
       너무 둥근 AI 대시보드 느낌을 없앱니다.
    -------------------------------------------------------- */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 2px;
        box-shadow: none;
    }

    div[data-testid="stMetric"] {
        background: transparent;
        border-top: 1px solid var(--line-dark);
        border-bottom: 1px solid var(--line);
        border-left: none;
        border-right: none;
        border-radius: 0;
        padding: 0.75rem 0;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 0.72rem;
        letter-spacing: 0.05em;
    }

    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-weight: 720;
        font-variant-numeric: tabular-nums;
    }


    /* --------------------------------------------------------
       이미지
    -------------------------------------------------------- */

    div[data-testid="stImage"] img {
        border-radius: 1px;
        display: block;
    }


    /* --------------------------------------------------------
       버튼
    -------------------------------------------------------- */

    .stButton button,
    .stDownloadButton button {
        border-radius: 2px;
        border: 1px solid var(--line-dark);
        background: transparent;
        color: var(--ink);
        font-weight: 650;
        box-shadow: none;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        border-color: var(--gold);
        color: var(--ink);
    }


    /* --------------------------------------------------------
       검색창
    -------------------------------------------------------- */

    div[data-baseweb="input"] {
        border-radius: 2px;
        border-color: var(--line);
        background: var(--card);
    }


    /* --------------------------------------------------------
       데이터프레임
    -------------------------------------------------------- */

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 2px;
    }


    /* --------------------------------------------------------
       하단 출처
    -------------------------------------------------------- */

    .source-note {
        color: var(--muted);
        font-size: 0.72rem;
        line-height: 1.8;
    }

    .footer-mark {
        color: var(--gold);
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 0.2em;
        margin-bottom: 0.6rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. 텍스트 / 숫자 처리 함수
# ============================================================

def read_secret(name: str) -> str:
    """Streamlit Secrets에서 값을 읽습니다."""
    try:
        return str(st.secrets[name]).strip()
    except Exception:
        return ""


def clean_text(value) -> str:
    """
    HTML 태그와 HTML 엔티티를 제거합니다.

    예:
    <div>치이카와: 인어섬의 비밀</div>
    ->
    치이카와: 인어섬의 비밀
    """

    if value is None:
        return ""

    text = str(value)

    # HTML 엔티티를 먼저 해석합니다.
    text = html.unescape(text)

    # 줄바꿈 태그는 실제 줄바꿈으로 바꿉니다.
    text = re.sub(
        r"<\s*br\s*/?\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # 나머지 HTML 태그 제거
    text = re.sub(
        r"<\s*/?\s*[a-zA-Z][^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 태그 제거 후 다시 HTML 엔티티 처리
    text = html.unescape(text)

    # 너무 많은 빈 줄 정리
    text = re.sub(
        r"\n[ \t]*\n(?:[ \t]*\n)+",
        "\n\n",
        text,
    )

    return text.strip()


def to_int(value) -> int:
    """숫자 문자열을 안전하게 정수로 변환합니다."""
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def format_number(value) -> str:
    return f"{to_int(value):,}"


def format_date(value) -> str:
    """YYYYMMDD를 YYYY.MM.DD로 표시합니다."""
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) >= 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:8]}"

    return str(value or "정보 없음")


def normalize_title(value) -> str:
    text = clean_text(value).lower()
    return re.sub(r"[\W_]", "", text, flags=re.UNICODE)


def get_kst_dates():
    """서버가 어느 나라에 있어도 한국 날짜를 기준으로 계산합니다."""
    today_kst = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    yesterday = today_kst - timedelta(days=1)
    day_before = today_kst - timedelta(days=2)

    return (
        yesterday.strftime("%Y%m%d"),
        day_before.strftime("%Y%m%d"),
    )


def get_rank_change(row) -> str:
    change = to_int(row.get("rankInten", 0))
    status = str(row.get("rankOldAndNew", "")).upper()

    if status == "NEW":
        return "신규"

    if change > 0:
        return f"▲ {change}"

    if change < 0:
        return f"▼ {abs(change)}"

    return "―"


# ============================================================
# 4. KOBIS 박스오피스
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(
    target_date: str,
    api_key: str,
):
    """KOBIS 일일 박스오피스를 가져옵니다."""

    try:
        response = requests.get(
            KOBIS_API_URL,
            params={
                "key": api_key,
                "targetDt": target_date,
                "itemPerPage": 10,
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:
        return {
            "data": [],
            "error": "KOBIS API 응답 시간이 초과되었습니다.",
        }

    except requests.exceptions.HTTPError:
        return {
            "data": [],
            "error": f"KOBIS API HTTP 오류: {response.status_code}",
        }

    except requests.exceptions.RequestException:
        return {
            "data": [],
            "error": "KOBIS API에 연결하지 못했습니다.",
        }

    except ValueError:
        return {
            "data": [],
            "error": "KOBIS 응답을 JSON으로 읽을 수 없습니다.",
        }

    # KOBIS는 API 키 오류 등을 HTTP 200으로 반환할 수도 있습니다.
    fault = data.get("faultInfo") if isinstance(data, dict) else None

    if fault:
        return {
            "data": [],
            "error": "KOBIS API 오류: "
            + clean_text(
                fault.get(
                    "message",
                    "요청에 실패했습니다.",
                )
            ),
        }

    result = data.get(
        "boxOfficeResult",
        {},
    )

    rows = (
        result.get("dailyBoxOfficeList", [])
        if isinstance(result, dict)
        else []
    )

    if not rows:
        return {
            "data": [],
            "error": (
                f"{format_date(target_date)} "
                "박스오피스 데이터가 없습니다."
            ),
        }

    return {
        "data": rows,
        "error": None,
    }


# ============================================================
# 5. KOBIS 보조 메타데이터
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_kobis_web_metadata(
    target_date: str,
):
    """
    KOBIS 웹페이지의 포스터/줄거리 정보를 확인합니다.

    이 데이터는 공개 OpenAPI 응답과 별개이므로
    응답 구조가 바뀌더라도 앱 전체가 중단되지 않도록
    실패하면 빈 딕셔너리를 반환합니다.
    """

    try:
        response = requests.get(
            KOBIS_WEB_DAILY_URL,
            timeout=12,
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.exceptions.RequestException,
        ValueError,
    ):
        return {}

    if isinstance(data, dict):
        data = data.get(
            "data",
            data.get("result", []),
        )

    if not isinstance(data, list):
        return {}

    metadata = {}

    for item in data:

        if not isinstance(item, dict):
            continue

        show_date = re.sub(
            r"\D",
            "",
            str(item.get("showDt", "")),
        )

        if show_date != target_date:
            continue

        movie_code = str(
            item.get("movieCd", "")
        ).strip()

        if not movie_code:
            continue

        thumb_path = str(
            item.get("thumbUrl", "")
        ).strip()

        poster_url = (
            urljoin(
                KOBIS_SITE_URL,
                thumb_path,
            )
            if thumb_path
            else None
        )

        metadata[movie_code] = {
            "poster_url": poster_url,
            "overview": clean_text(
                item.get("synop", "")
            ),
            "english_title": clean_text(
                item.get("movieNmEn", "")
            ),
        }

    return metadata


# ============================================================
# 6. TMDB 보완 조회
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_tmdb_fallback(
    korean_title: str,
    english_title: str,
    release_date: str,
    api_key: str,
    large: bool = False,
):
    """
    TMDB에서 포스터와 한국어 줄거리를 가져옵니다.

    large=True이면 1위 영화처럼 큰 포스터에 적합한
    w1280 이미지를 사용합니다.
    """

    empty = {
        "poster_url": None,
        "overview": "",
        "error": None,
    }

    if not api_key:
        return empty

    year = re.sub(
        r"\D",
        "",
        str(release_date or ""),
    )[:4]

    queries = []

    if korean_title:
        queries.append(korean_title)

    if (
        english_title
        and normalize_title(english_title)
        != normalize_title(korean_title)
    ):
        queries.append(english_title)

    candidates = {}

    try:

        for query in queries:

            params = {
                "api_key": api_key,
                "query": query,
                "language": "ko-KR",
                "region": "KR",
                "include_adult": "false",
            }

            if len(year) == 4:
                params["primary_release_year"] = year

            response = requests.get(
                TMDB_SEARCH_URL,
                params=params,
                timeout=12,
            )

            if response.status_code == 401:
                return {
                    **empty,
                    "error": (
                        "TMDB_API_KEY 인증에 실패했습니다."
                    ),
                }

            response.raise_for_status()

            results = response.json().get(
                "results",
                [],
            )

            # 개봉연도가 다르게 등록된 경우
            # 연도 제한을 제거하고 다시 검색합니다.
            if (
                not results
                and "primary_release_year" in params
            ):
                params.pop(
                    "primary_release_year",
                    None,
                )

                response = requests.get(
                    TMDB_SEARCH_URL,
                    params=params,
                    timeout=12,
                )

                response.raise_for_status()

                results = response.json().get(
                    "results",
                    [],
                )

            for item in results:

                if item.get("id") is not None:
                    candidates[item["id"]] = item

    except requests.exceptions.RequestException:

        return {
            **empty,
            "error": "TMDB에 연결하지 못했습니다.",
        }

    except ValueError:

        return {
            **empty,
            "error": "TMDB 응답을 읽을 수 없습니다.",
        }

    if not candidates:
        return empty

    query_norms = [
        normalize_title(query)
        for query in queries
        if normalize_title(query)
    ]

    scored = []

    for item in candidates.values():

        titles = [
            normalize_title(
                item.get("title", "")
            ),
            normalize_title(
                item.get("original_title", "")
            ),
        ]

        titles = [
            title
            for title in titles
            if title
        ]

        similarity = 0.0

        for query_norm in query_norms:

            for candidate_title in titles:

                score = SequenceMatcher(
                    None,
                    query_norm,
                    candidate_title,
                ).ratio()

                if query_norm == candidate_title:
                    score = 1.0

                elif (
                    len(query_norm) >= 3
                    and (
                        query_norm in candidate_title
                        or candidate_title in query_norm
                    )
                ):
                    score = max(
                        score,
                        0.85,
                    )

                similarity = max(
                    similarity,
                    score,
                )

        candidate_year = str(
            item.get("release_date", "")
        )[:4]

        score = similarity * 10

        if (
            year
            and candidate_year == year
        ):
            score += 2

        if item.get("poster_path"):
            score += 0.2

        scored.append(
            (
                score,
                similarity,
                item,
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    _, similarity, movie = scored[0]

    candidate_year = str(
        movie.get("release_date", "")
    )[:4]

    same_year_single = (
        len(candidates) == 1
        and year
        and candidate_year == year
    )

    # 다른 영화의 포스터가 잘못 표시되는 것을 방지합니다.
    if (
        similarity < 0.45
        and not same_year_single
    ):
        return empty

    poster_path = movie.get(
        "poster_path"
    )

    if poster_path:

        image_base = (
            TMDB_IMAGE_LARGE_BASE
            if large
            else TMDB_IMAGE_BASE
        )

        poster_url = (
            image_base
            + poster_path
        )

    else:
        poster_url = None

    overview = clean_text(
        movie.get(
            "overview",
            "",
        )
    )

    movie_id = movie.get("id")

    # 상세정보에서 한국어 줄거리 확인
    if movie_id and not overview:

        try:

            detail_response = requests.get(
                f"{TMDB_MOVIE_URL}/{movie_id}",
                params={
                    "api_key": api_key,
                    "language": "ko-KR",
                },
                timeout=10,
            )

            detail_response.raise_for_status()

            overview = clean_text(
                detail_response.json().get(
                    "overview",
                    "",
                )
            )

        except (
            requests.exceptions.RequestException,
            ValueError,
        ):
            overview = ""

    # 번역 데이터까지 확인
    if movie_id and not overview:

        try:

            translations_response = requests.get(
                f"{TMDB_MOVIE_URL}/{movie_id}/translations",
                params={
                    "api_key": api_key,
                },
                timeout=10,
            )

            translations_response.raise_for_status()

            translations = (
                translations_response.json().get(
                    "translations",
                    [],
                )
            )

            for translation in translations:

                if (
                    translation.get(
                        "iso_3166_1"
                    ) == "KR"
                    or translation.get(
                        "iso_639_1"
                    ) == "ko"
                ):

                    translation_data = (
                        translation.get(
                            "data",
                            {},
                        )
                    )

                    overview = clean_text(
                        translation_data.get(
                            "overview",
                            "",
                        )
                    )

                    if overview:
                        break

        except (
            requests.exceptions.RequestException,
            ValueError,
        ):
            pass

    return {
        "poster_url": poster_url,
        "overview": overview,
        "error": None,
    }


# ============================================================
# 7. 이미지 다운로드
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def download_image(
    image_url: str,
):
    """
    포스터를 bytes로 다운로드합니다.

    이전 버전의 w500보다 큰 이미지를 사용하므로
    Streamlit에서 표시할 때 훨씬 선명합니다.
    """

    if not image_url:
        return None

    if not image_url.startswith(
        "https://"
    ):
        return None

    try:

        response = requests.get(
            image_url,
            timeout=15,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if (
            not content_type.startswith(
                "image/"
            )
            or not response.content
        ):
            return None

        return response.content

    except requests.exceptions.RequestException:
        return None


# ============================================================
# 8. 날짜 및 API 키
# ============================================================

kobis_api_key = read_secret(
    "KOBIS_KEY"
)

tmdb_api_key = read_secret(
    "TMDB_API_KEY"
)

yesterday, day_before = get_kst_dates()

yesterday_label = format_date(
    yesterday
)


# ============================================================
# 9. 헤더
# ============================================================

header_left, header_right = st.columns(
    [5, 1]
)

with header_left:

    st.markdown(
        '<div class="journal-name">'
        'DAILY SCREEN REPORT'
        '</div>',
        unsafe_allow_html=True,
    )

    st.title(
        "어제의 박스오피스"
    )

    st.markdown(
        '<div class="journal-description">'
        '하루의 관객 흐름을 기록합니다.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="date-line">'
        f'{yesterday_label} · KOREA'
        f'</div>',
        unsafe_allow_html=True,
    )

with header_right:

    st.write("")
    st.write("")

    if st.button(
        "새로고침",
        use_container_width=True,
    ):

        st.cache_data.clear()
        st.rerun()


st.markdown(
    '<div class="gold-rule"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="thin-rule"></div>',
    unsafe_allow_html=True,
)


# ============================================================
# 10. KOBIS API 키 확인
# ============================================================

if not kobis_api_key:

    st.error(
        "KOBIS_KEY가 없습니다. "
        "Streamlit Cloud의 Secrets에 "
        "KOBIS_KEY를 등록해 주세요."
    )

    st.stop()


# ============================================================
# 11. 현재 / 전일 데이터 조회
# ============================================================

with st.spinner(
    "오늘의 상영 기록을 불러오는 중입니다..."
):

    current_result = fetch_boxoffice(
        yesterday,
        kobis_api_key,
    )

if current_result["error"]:

    st.error(
        current_result["error"]
    )

    with st.container(
        border=True
    ):

        st.markdown(
            "### 확인할 항목"
        )

        st.write(
            "KOBIS_KEY가 정확한지, "
            "KOBIS API가 정상적으로 응답하는지 "
            "확인해 주세요."
        )

    st.stop()


current_raw = (
    current_result["data"]
)


previous_result = fetch_boxoffice(
    day_before,
    kobis_api_key,
)

previous_raw = (
    previous_result["data"]
    if not previous_result["error"]
    else []
)


previous_by_code = {
    str(
        item.get(
            "movieCd",
            "",
        )
    ): item

    for item in previous_raw

    if item.get(
        "movieCd"
    )
}


# ============================================================
# 12. 데이터프레임 구성
# ============================================================

rows = []

for item in current_raw:

    movie_code = str(
        item.get(
            "movieCd",
            "",
        )
    )

    prior = previous_by_code.get(
        movie_code
    )

    current_audience = to_int(
        item.get(
            "audiCnt"
        )
    )

    prior_audience = (
        to_int(
            prior.get(
                "audiCnt"
            )
        )
        if prior
        else None
    )

    if previous_result["error"]:

        audience_change = "비교 불가"

    elif prior is None:

        audience_change = "전일 TOP 10 밖"

    else:

        delta = (
            current_audience
            - prior_audience
        )

        if prior_audience > 0:

            percent = (
                delta
                / prior_audience
                * 100
            )

            audience_change = (
                f"{delta:+,}명 "
                f"({percent:+.1f}%)"
            )

        else:

            audience_change = (
                f"{delta:+,}명"
            )

    rows.append(
        {
            "순위": to_int(
                item.get(
                    "rank"
                )
            ),
            "영화명": clean_text(
                item.get(
                    "movieNm",
                    "",
                )
            ),
            "개봉일": str(
                item.get(
                    "openDt",
                    "",
                )
            ),
            "매출액": to_int(
                item.get(
                    "salesAmt"
                )
            ),
            "관객 수": current_audience,
            "누적 관객 수": to_int(
                item.get(
                    "audiAcc"
                )
            ),
            "스크린 수": to_int(
                item.get(
                    "scrnCnt"
                )
            ),
            "상영 횟수": to_int(
                item.get(
                    "showCnt"
                )
            ),
            "영화코드": movie_code,
            "순위 변동": get_rank_change(
                item
            ),
            "전일 대비 관객": audience_change,
        }
    )


df = pd.DataFrame(
    rows
)

if df.empty:

    st.info(
        "표시할 영화 데이터가 없습니다."
    )

    st.stop()


df = (
    df.sort_values(
        "순위"
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 13. 포스터와 줄거리
# ============================================================

with st.spinner(
    "영화 이미지를 준비하는 중입니다..."
):

    kobis_metadata = (
        fetch_kobis_web_metadata(
            yesterday
        )
    )

    assets = {}

    tmdb_errors = set()

    for _, row in df.iterrows():

        code = row[
            "영화코드"
        ]

        meta = kobis_metadata.get(
            code,
            {}
        )

        poster_url = (
            meta.get(
                "poster_url"
            )
            or None
        )

        overview = clean_text(
            meta.get(
                "overview",
                "",
            )
        )

        english_title = clean_text(
            meta.get(
                "english_title",
                "",
            )
        )

        # KOBIS 정보가 없거나 포스터가 없으면
        # TMDB를 보조 수단으로 사용합니다.
        if (
            (
                not poster_url
                or not overview
            )
            and tmdb_api_key
        ):

            fallback = (
                fetch_tmdb_fallback(
                    korean_title=row[
                        "영화명"
                    ],
                    english_title=english_title,
                    release_date=row[
                        "개봉일"
                    ],
                    api_key=tmdb_api_key,
                    large=(
                        row["순위"] == 1
                    ),
                )
            )

            if not poster_url:

                poster_url = (
                    fallback.get(
                        "poster_url"
                    )
                )

            if not overview:

                overview = clean_text(
                    fallback.get(
                        "overview",
                        "",
                    )
                )

            if fallback.get(
                "error"
            ):

                tmdb_errors.add(
                    fallback[
                        "error"
                    ]
                )

        poster_bytes = (
            download_image(
                poster_url
            )
            if poster_url
            else None
        )

        assets[code] = {
            "poster_url": poster_url,
            "poster_bytes": poster_bytes,
            "overview": overview,
        }


# ============================================================
# 14. 포스터 출력 함수
# ============================================================

def show_poster(
    asset,
):
    """포스터가 있으면 선명하게 표시하고 없으면 안내합니다."""

    image_data = asset.get(
        "poster_bytes"
    )

    if image_data:

        st.image(
            image_data,
            use_container_width=True,
        )

    else:

        st.markdown(
            '<div class="poster-placeholder">'
            'POSTER NOT AVAILABLE'
            '</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# 15. 1위 영화
# ============================================================

top = df.iloc[0]

top_asset = assets.get(
    top["영화코드"],
    {},
)


st.markdown(
    '<div class="section-number">'
    '01 · FEATURED FILM'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">'
    '오늘의 1위'
    '</div>',
    unsafe_allow_html=True,
)


with st.container(
    border=True
):

    hero_poster, hero_info = st.columns(
        [1.05, 2.2],
        gap="large",
    )

    with hero_poster:

        show_poster(
            top_asset
        )

    with hero_info:

        st.markdown(
            '<div class="hero-frame">',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="hero-rank">'
            f'RANK {int(top["순위"]):02d}'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.header(
            top["영화명"]
        )

        st.markdown(
            f'<div class="hero-meta">'
            f'개봉 {format_date(top["개봉일"])}'
            f'　·　'
            f'순위 {top["순위 변동"]}'
            f'</div>',
            unsafe_allow_html=True,
        )

        overview = top_asset.get(
            "overview",
            "",
        )

        if overview:

            st.markdown(
                '<div class="hero-description">'
                + html.escape(
                    overview
                ).replace(
                    "\n",
                    "<br>",
                )
                + "</div>",
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                '<div class="hero-description">'
                '한국어 줄거리가 등록되어 있지 않습니다.'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# 16. 1위 주요 기록
# ============================================================

st.write("")

metric1, metric2, metric3, metric4 = st.columns(
    4,
    gap="large",
)

with metric1:

    st.metric(
        "DAILY AUDIENCE",
        f"{format_number(top['관객 수'])}명",
    )

with metric2:

    st.metric(
        "TOTAL AUDIENCE",
        f"{format_number(top['누적 관객 수'])}명",
    )

with metric3:

    st.metric(
        "BOX OFFICE",
        f"₩{format_number(top['매출액'])}",
    )

with metric4:

    st.metric(
        "SCREENS",
        f"{format_number(top['스크린 수'])}",
    )


# ============================================================
# 17. 전체 영화 목록
# ============================================================

st.write("")
st.write("")

st.markdown(
    '<div class="section-number">'
    '02 · DAILY PROGRAM'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">'
    '오늘 상영 중인 영화'
    '</div>',
    unsafe_allow_html=True,
)

st.caption(
    "KOBIS 일일 박스오피스에서 제공하는 전체 영화 목록입니다."
)


search_query = st.text_input(
    "영화명 검색",
    placeholder="영화 제목으로 검색",
    label_visibility="collapsed",
)


if search_query.strip():

    filtered_df = df[
        df["영화명"].str.contains(
            search_query.strip(),
            case=False,
            na=False,
        )
    ].copy()

else:

    filtered_df = df.copy()


if filtered_df.empty:

    st.info(
        "검색어와 일치하는 영화가 없습니다."
    )

else:

    # 5편씩 영화 프로그램북처럼 보여줍니다.
    for start in range(
        0,
        len(filtered_df),
        5,
    ):

        chunk = filtered_df.iloc[
            start:start + 5
        ]

        columns = st.columns(
            5,
            gap="medium",
        )

        for column, (
            _,
            movie,
        ) in zip(
            columns,
            chunk.iterrows(),
        ):

            asset = assets.get(
                movie["영화코드"],
                {},
            )

            with column:

                show_poster(
                    asset
                )

                st.markdown(
                    f'<div class="film-index">'
                    f'{int(movie["순위"]):02d}'
                    f'　{html.escape(movie["순위 변동"])}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div class="film-title">'
                    f'{html.escape(movie["영화명"])}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div class="film-meta">'
                    f'관객 {format_number(movie["관객 수"])}명'
                    f'<br>'
                    f'스크린 {format_number(movie["스크린 수"])}개'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                overview = asset.get(
                    "overview",
                    "",
                )

                if overview:

                    with st.expander(
                        "줄거리"
                    ):

                        st.write(
                            overview
                        )

                st.write("")


# ============================================================
# 18. 비교 차트
# ============================================================

st.write("")
st.write("")

st.markdown(
    '<div class="section-number">'
    '03 · BOX OFFICE NUMBERS'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">'
    '흥행 지표'
    '</div>',
    unsafe_allow_html=True,
)


chart_choice = st.radio(
    "비교 지표",
    [
        "관객 수",
        "매출액",
    ],
    horizontal=True,
    label_visibility="collapsed",
)


chart_df = filtered_df[
    [
        "영화명",
        chart_choice,
    ]
].copy()


if not chart_df.empty:

    chart_df = (
        chart_df
        .sort_values(
            chart_choice,
            ascending=True,
        )
        .set_index(
            "영화명"
        )
    )

    st.bar_chart(
        chart_df,
        horizontal=True,
        use_container_width=True,
    )


# ============================================================
# 19. 상세 표
# ============================================================

st.write("")
st.write("")

st.markdown(
    '<div class="section-number">'
    '04 · ARCHIVE'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">'
    '상세 기록'
    '</div>',
    unsafe_allow_html=True,
)


visible_columns = [
    "순위",
    "영화명",
    "개봉일",
    "순위 변동",
    "관객 수",
    "전일 대비 관객",
    "매출액",
    "누적 관객 수",
    "스크린 수",
    "상영 횟수",
]


table_df = filtered_df[
    visible_columns
].copy()


table_df[
    "개봉일"
] = table_df[
    "개봉일"
].map(
    format_date
)


for column in [
    "관객 수",
    "매출액",
    "누적 관객 수",
    "스크린 수",
    "상영 횟수",
]:

    table_df[
        column
    ] = table_df[
        column
    ].map(
        format_number
    )


st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 20. CSV 다운로드
# ============================================================

csv_bytes = table_df.to_csv(
    index=False
).encode(
    "utf-8-sig"
)


st.download_button(
    label="현재 표 CSV 저장",
    data=csv_bytes,
    file_name=(
        f"boxoffice_{yesterday}.csv"
    ),
    mime="text/csv",
)


# ============================================================
# 21. 안내 / 출처
# ============================================================

if previous_result["error"]:

    st.caption(
        "전일 자료를 조회하지 못해 "
        "일부 관객 증감 비교를 표시하지 못했습니다."
    )


st.markdown(
    '<div class="thin-rule"></div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="footer-mark">'
    'DAILY SCREEN REPORT'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="source-note">
        박스오피스 순위·매출·관객 수 · 영화진흥위원회 KOBIS 오픈API<br>
        포스터·한국어 줄거리 · KOBIS 데이터 우선, 누락 시 TMDB 보완<br>
        전일 대비 관객 수는 전일 TOP 10 자료를 기준으로 계산합니다.
    </div>
    """,
    unsafe_allow_html=True,
)


if tmdb_api_key:

    st.caption(
        "This product uses the TMDB API but is not endorsed or certified by TMDB."
    )
