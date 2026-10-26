
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
# 1. 페이지 설정과 디자인
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

# KOBIS 웹페이지가 제공하는 보조 데이터입니다.
# 일일 오픈API에 없는 포스터/줄거리를 보완하는 용도이며,
# 날짜와 영화 코드가 맞을 때에만 사용합니다.
KOBIS_WEB_DAILY_URL = (
    "https://www.kobis.or.kr/kobis/business/main/searchMainDailyBoxOffice.do"
)
KOBIS_SITE_URL = "https://www.kobis.or.kr"
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

st.markdown(
    """
    <style>
    :root {
        --ink: #14212B;
        --gold: #B99752;
        --paper: #F5F2EB;
        --line: #DCD7CD;
        --muted: #69737B;
        --card: #FFFEFC;
    }

    html, body, [class*="css"] {
        font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo",
                     "Malgun Gothic", sans-serif;
    }

    .stApp {
        background: var(--paper);
        color: var(--ink);
    }

    .block-container {
        max-width: 1280px;
        padding-top: 2.1rem;
        padding-bottom: 3.5rem;
    }

    h1, h2, h3 {
        color: var(--ink) !important;
        letter-spacing: -0.045em !important;
    }

    h1 {
        font-size: clamp(2rem, 4vw, 3rem) !important;
        font-weight: 760 !important;
    }

    h2 {
        font-size: 1.55rem !important;
        font-weight: 720 !important;
    }

    h3 {
        font-size: 1.13rem !important;
        font-weight: 700 !important;
    }

    .masthead-kicker {
        color: var(--gold);
        font-size: .72rem;
        font-weight: 750;
        letter-spacing: .18em;
        text-transform: uppercase;
        margin-bottom: .5rem;
    }

    .masthead-deck {
        color: var(--muted);
        font-size: .95rem;
        margin-top: -.65rem;
        margin-bottom: 1.35rem;
    }

    .section-eyebrow {
        color: var(--gold);
        font-size: .7rem;
        font-weight: 750;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: .25rem;
    }

    .rank-number {
        font-size: .76rem;
        font-weight: 750;
        letter-spacing: .08em;
        color: var(--gold);
        margin-bottom: .3rem;
    }

    .movie-card-title {
        color: var(--ink);
        font-size: .98rem;
        font-weight: 700;
        line-height: 1.45;
        overflow-wrap: anywhere;
        margin: .25rem 0 .2rem 0;
    }

    .small-muted {
        color: var(--muted);
        font-size: .78rem;
        line-height: 1.55;
    }

    .poster-placeholder {
        box-sizing: border-box;
        width: 100%;
        aspect-ratio: 2 / 3;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #E9E5DC;
        border: 1px solid var(--line);
        color: #777D81;
        font-size: .8rem;
        text-align: center;
        padding: .7rem;
    }

    .rule {
        height: 1px;
        background: var(--line);
        margin: .6rem 0 1.1rem 0;
    }

    .source-note {
        color: var(--muted);
        font-size: .78rem;
        line-height: 1.7;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 7px;
        box-shadow: none;
    }

    div[data-testid="stMetric"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 7px;
        padding: 14px 16px;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: .82rem;
    }

    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-weight: 720;
        font-variant-numeric: tabular-nums;
    }

    div[data-testid="stImage"] img {
        border-radius: 3px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 5px;
    }

    div[data-testid="stExpander"] {
        border-color: var(--line);
        border-radius: 5px;
    }

    .stButton button, .stDownloadButton button {
        border-radius: 5px;
        border-color: #C9C3B7;
        font-weight: 650;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. 공통 함수
# ============================================================
def read_secret(name: str) -> str:
    """Streamlit Secrets에서 값을 읽습니다. 없으면 빈 문자열을 반환합니다."""
    try:
        return str(st.secrets[name]).strip()
    except Exception:
        return ""


def clean_text(value) -> str:
    """HTML 태그와 엔티티를 제거하고 일반 텍스트로 정리합니다."""
    if value is None:
        return ""

    text = str(value)

    for _ in range(2):
        text = html.unescape(text)

    text = re.sub(
        r"<\s*br\s*/?\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<\s*/?\s*[a-zA-Z][^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = html.unescape(text)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)

    return text.strip()


def to_int(value) -> int:
    """API 숫자 문자열을 안전하게 정수로 바꿉니다."""
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def format_number(value) -> str:
    return f"{to_int(value):,}"


def format_date(value) -> str:
    """YYYYMMDD, YYYY-MM-DD, YYYY.MM.DD를 YYYY.MM.DD로 표시합니다."""
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) >= 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:8]}"

    return str(value or "정보 없음")


def get_kst_dates():
    """한국 시간 기준 어제와 그 전날을 반환합니다."""
    today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()

    return (
        (today_kst - timedelta(days=1)).strftime("%Y%m%d"),
        (today_kst - timedelta(days=2)).strftime("%Y%m%d"),
    )


def normalize_title(value) -> str:
    text = clean_text(value).lower()
    return re.sub(r"[\W_]", "", text, flags=re.UNICODE)


def get_rank_change(row) -> str:
    change = to_int(row.get("rankInten", 0))
    status = str(row.get("rankOldAndNew", "")).upper()

    if status == "NEW":
        return "신규 진입"

    if change > 0:
        return f"▲ {change}"

    if change < 0:
        return f"▼ {abs(change)}"

    return "변동 없음"


# ============================================================
# 3. KOBIS 일일 박스오피스 오픈API
# ============================================================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(target_date: str, api_key: str):
    """KOBIS 일일 박스오피스를 조회합니다."""
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

    fault = data.get("faultInfo") if isinstance(data, dict) else None

    if fault:
        return {
            "data": [],
            "error": "KOBIS API 오류: " + clean_text(
                fault.get("message", "요청에 실패했습니다.")
            ),
        }

    result = data.get("boxOfficeResult", {}) if isinstance(data, dict) else {}
    rows = result.get("dailyBoxOfficeList", []) if isinstance(result, dict) else []

    if not rows:
        return {
            "data": [],
            "error": f"{format_date(target_date)} 박스오피스 데이터가 없습니다.",
        }

    return {"data": rows, "error": None}


# ============================================================
# 4. KOBIS 웹페이지의 포스터/한국어 줄거리 보조 데이터
# ============================================================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_kobis_web_metadata(target_date: str):
    """
    KOBIS 메인 일일 박스오피스 페이지가 반환하는 데이터를 읽습니다.

    공개 OpenAPI 규격과는 별개의 웹페이지 데이터이므로,
    응답 형식이나 날짜가 다르면 사용하지 않습니다.
    """
    try:
        response = requests.get(
            KOBIS_WEB_DAILY_URL,
            timeout=12,
        )

        response.raise_for_status()
        data = response.json()

    except (requests.exceptions.RequestException, ValueError):
        return {}

    # 응답 형식이 바뀔 경우를 대비합니다.
    if isinstance(data, dict):
        data = data.get("data", data.get("result", []))

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

        # 요청한 날짜와 일치하는 데이터만 사용합니다.
        if show_date != target_date:
            continue

        movie_code = str(item.get("movieCd", "")).strip()

        if movie_code:
            thumb_path = str(item.get("thumbUrl", "")).strip()

            metadata[movie_code] = {
                "poster_url": (
                    urljoin(KOBIS_SITE_URL, thumb_path)
                    if thumb_path
                    else None
                ),
                "overview": clean_text(item.get("synop", "")),
                "english_title": clean_text(item.get("movieNmEn", "")),
            }

    return metadata


# ============================================================
# 5. TMDB 대체 조회
#    KOBIS 보조 데이터가 없을 때만 사용합니다.
# ============================================================
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_tmdb_fallback(
    korean_title: str,
    english_title: str,
    release_date: str,
    api_key: str,
):
    """TMDB에서 포스터와 한국어 줄거리를 조회합니다."""
    empty = {
        "poster_url": None,
        "overview": "",
        "error": None,
    }

    if not api_key:
        return empty

    year = re.sub(r"\D", "", str(release_date or ""))[:4]

    queries = []

    if korean_title:
        queries.append(korean_title)

    if (
        english_title
        and normalize_title(english_title) != normalize_title(korean_title)
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
                    "error": "TMDB_API_KEY 인증에 실패했습니다.",
                }

            response.raise_for_status()
            results = response.json().get("results", [])

            # 한국 개봉연도와 TMDB 등록 연도가 다른 경우,
            # 연도 필터를 제거하고 다시 검색합니다.
            if not results and "primary_release_year" in params:
                params.pop("primary_release_year", None)

                response = requests.get(
                    TMDB_SEARCH_URL,
                    params=params,
                    timeout=12,
                )

                response.raise_for_status()
                results = response.json().get("results", [])

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
            normalize_title(item.get("title", "")),
            normalize_title(item.get("original_title", "")),
        ]

        titles = [title for title in titles if title]
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
                    score = max(score, 0.85)

                similarity = max(similarity, score)

        candidate_year = str(item.get("release_date", ""))[:4]

        score = similarity * 10

        if year and candidate_year == year:
            score += 2

        if item.get("poster_path"):
            score += 0.2

        scored.append((score, similarity, item))

    scored.sort(key=lambda item: item[0], reverse=True)

    _, similarity, movie = scored[0]
    candidate_year = str(movie.get("release_date", ""))[:4]

    same_year_single = (
        len(candidates) == 1
        and year
        and candidate_year == year
    )

    # 제목이 충분히 일치하지 않으면 다른 영화의 포스터를 쓰지 않습니다.
    if similarity < 0.45 and not same_year_single:
        return empty

    poster_path = movie.get("poster_path")
    poster_url = (
        f"{TMDB_IMAGE_BASE}{poster_path}"
        if poster_path
        else None
    )

    overview = clean_text(movie.get("overview", ""))
    movie_id = movie.get("id")

    # 검색 결과에 줄거리가 없으면 한국어 상세정보를 조회합니다.
    if movie_id and not overview:
        try:
            detail_response = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}",
                params={
                    "api_key": api_key,
                    "language": "ko-KR",
                },
                timeout=10,
            )

            detail_response.raise_for_status()

            overview = clean_text(
                detail_response.json().get("overview", "")
            )

        except (requests.exceptions.RequestException, ValueError):
            overview = ""

    # 상세정보에도 한국어 줄거리가 없으면 번역 목록을 확인합니다.
    if movie_id and not overview:
        try:
            translations_response = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/translations",
                params={"api_key": api_key},
                timeout=10,
            )

            translations_response.raise_for_status()

            translations = translations_response.json().get(
                "translations",
                [],
            )

            for translation in translations:
                if (
                    translation.get("iso_3166_1") == "KR"
                    or translation.get("iso_639_1") == "ko"
                ):
                    translation_data = translation.get("data", {})

                    overview = clean_text(
                        translation_data.get("overview", "")
                    )

                    if overview:
                        break

        except (requests.exceptions.RequestException, ValueError):
            pass

    return {
        "poster_url": poster_url,
        "overview": overview,
        "error": None,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def download_image(image_url: str):
    """이미지를 내려받아 bytes로 반환합니다. 실패 시 None을 반환합니다."""
    if not image_url or not image_url.startswith("https://"):
        return None

    try:
        response = requests.get(
            image_url,
            timeout=12,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if (
            not content_type.startswith("image/")
            or not response.content
        ):
            return None

        return response.content

    except requests.exceptions.RequestException:
        return None


# ============================================================
# 6. 조회 및 데이터 정리
# ============================================================
kobis_api_key = read_secret("KOBIS_KEY")
tmdb_api_key = read_secret("TMDB_API_KEY")  # 선택 사항

yesterday, day_before = get_kst_dates()
yesterday_label = format_date(yesterday)

header_left, header_right = st.columns([5, 1])

with header_left:
    st.markdown(
        '<div class="masthead-kicker">SCREEN REPORT / DAILY</div>',
        unsafe_allow_html=True,
    )

    st.title("어제의 박스오피스")

    st.markdown(
        f'<div class="masthead-deck">{yesterday_label} 기준 · 순위, 관객 수, 상영 현황</div>',
        unsafe_allow_html=True,
    )

with header_right:
    st.write("")
    st.write("")

    if st.button("새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown(
    '<div class="rule"></div>',
    unsafe_allow_html=True,
)

if not kobis_api_key:
    st.error(
        "KOBIS_KEY가 없습니다. "
        "Streamlit Cloud의 Secrets에 KOBIS_KEY를 등록해 주세요."
    )
    st.stop()

with st.spinner("박스오피스 데이터를 불러오는 중입니다..."):
    current_result = fetch_boxoffice(
        yesterday,
        kobis_api_key,
    )

if current_result["error"]:
    st.error(current_result["error"])

    with st.container(border=True):
        st.markdown("**확인할 항목**")
        st.write(
            "Secrets의 KOBIS_KEY, 날짜, API 응답 상태를 확인해 주세요."
        )

    st.stop()

current_raw = current_result["data"]

# 전일 데이터는 비교 기능에만 사용합니다.
# 전일 조회에 실패해도 현재 박스오피스는 계속 표시합니다.
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
    str(item.get("movieCd", "")): item
    for item in previous_raw
    if item.get("movieCd")
}

rows = []

for item in current_raw:
    movie_code = str(item.get("movieCd", ""))
    prior = previous_by_code.get(movie_code)

    current_audience = to_int(item.get("audiCnt"))
    prior_audience = to_int(prior.get("audiCnt")) if prior else None

    if previous_result["error"]:
        audience_change = "비교 불가"

    elif prior is None:
        audience_change = "전일 TOP 10 밖"

    else:
        delta = current_audience - prior_audience

        if prior_audience > 0:
            percent = (delta / prior_audience) * 100
            audience_change = f"{delta:+,}명 ({percent:+.1f}%)"
        else:
            audience_change = f"{delta:+,}명"

    rows.append(
        {
            "순위": to_int(item.get("rank")),
            "영화명": clean_text(item.get("movieNm", "")),
            "개봉일": str(item.get("openDt", "") or ""),
            "매출액": to_int(item.get("salesAmt")),
            "관객 수": current_audience,
            "누적 관객 수": to_int(item.get("audiAcc")),
            "스크린 수": to_int(item.get("scrnCnt")),
            "상영 횟수": to_int(item.get("showCnt")),
            "영화코드": movie_code,
            "순위 변동": get_rank_change(item),
            "전일 대비 관객": audience_change,
        }
    )

df = pd.DataFrame(rows)

if df.empty:
    st.info("표시할 영화 데이터가 없습니다.")
    st.stop()

df = df.sort_values("순위").reset_index(drop=True)


# ============================================================
# 7. 포스터/줄거리: KOBIS 우선, TMDB 보완
# ============================================================
with st.spinner("포스터와 한국어 줄거리를 확인하는 중입니다..."):
    kobis_metadata = fetch_kobis_web_metadata(yesterday)

    assets = {}
    tmdb_error_messages = set()

    for _, row in df.iterrows():
        code = row["영화코드"]
        meta = kobis_metadata.get(code, {})

        poster_url = meta.get("poster_url") or None
        overview = clean_text(meta.get("overview", ""))
        english_title = clean_text(meta.get("english_title", ""))

        # KOBIS 데이터에 포스터 또는 줄거리가 없을 때만 TMDB를 조회합니다.
        if (not poster_url or not overview) and tmdb_api_key:
            fallback = fetch_tmdb_fallback(
                korean_title=row["영화명"],
                english_title=english_title,
                release_date=row["개봉일"],
                api_key=tmdb_api_key,
            )

            if not poster_url:
                poster_url = fallback.get("poster_url")

            if not overview:
                overview = clean_text(fallback.get("overview", ""))

            if fallback.get("error"):
                tmdb_error_messages.add(fallback["error"])

        poster_bytes = (
            download_image(poster_url)
            if poster_url
            else None
        )

        assets[code] = {
            "poster_url": poster_url,
            "poster_bytes": poster_bytes,
            "overview": overview,
        }

if tmdb_error_messages:
    st.warning(
        "TMDB 보완 조회 중 문제가 발생했습니다: "
        + " / ".join(sorted(tmdb_error_messages))
    )


def show_poster(asset):
    """내려받은 포스터를 표시하고, 없으면 자리표시자를 표시합니다."""
    image_data = asset.get("poster_bytes")

    if image_data:
        st.image(
            image_data,
            use_container_width=True,
        )
    else:
        st.markdown(
            '<div class="poster-placeholder">포스터 이미지 없음</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# 8. 1위 영화 하이라이트
# ============================================================
top = df.iloc[0]
top_asset = assets.get(top["영화코드"], {})

st.markdown(
    '<div class="section-eyebrow">NUMBER ONE</div>',
    unsafe_allow_html=True,
)

st.subheader("오늘의 1위")

# 여는 HTML과 닫는 HTML을 서로 다른 호출에 나누지 않습니다.
# 포스터와 텍스트를 같은 Streamlit 컨테이너 안에 배치합니다.
with st.container(border=True):
    poster_col, information_col = st.columns(
        [1, 2.25],
        gap="large",
    )

    with poster_col:
        show_poster(top_asset)

    with information_col:
        st.markdown(
            f'<div class="rank-number">RANK {int(top["순위"]):02d}</div>',
            unsafe_allow_html=True,
        )

        st.header(top["영화명"])

        st.caption(
            f"개봉일 {format_date(top['개봉일'])}"
            f"  ·  순위 변동 {top['순위 변동']}"
        )

        if top_asset.get("overview"):
            # 줄거리는 일반 텍스트로 출력합니다.
            st.write(top_asset["overview"])
        else:
            st.caption("한국어 줄거리가 등록되어 있지 않습니다.")

st.write("")

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:
    st.metric(
        "일일 관객",
        f"{format_number(top['관객 수'])}명",
    )

with metric2:
    st.metric(
        "누적 관객",
        f"{format_number(top['누적 관객 수'])}명",
    )

with metric3:
    st.metric(
        "매출액",
        f"₩{format_number(top['매출액'])}",
    )

with metric4:
    st.metric(
        "스크린 수",
        f"{format_number(top['스크린 수'])}개",
    )


# ============================================================
# 9. 전체 TOP 10 영화 카드와 검색
# ============================================================
st.markdown(
    '<div class="section-eyebrow">THE DAILY TEN</div>',
    unsafe_allow_html=True,
)

st.subheader("일일 박스오피스 전체 10편")

st.caption(
    "KOBIS 일일 박스오피스 API에서 제공하는 영화 목록을 모두 표시합니다."
)

search_query = st.text_input(
    "영화명 검색",
    placeholder="영화 제목을 입력하세요",
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
    st.info("검색어와 일치하는 영화가 없습니다.")

else:
    # 한 줄에 다섯 편씩, 기본적으로 1~10위를 모두 보여줍니다.
    for start in range(0, len(filtered_df), 5):
        chunk = filtered_df.iloc[start:start + 5]
        columns = st.columns(5, gap="medium")

        for column, (_, movie) in zip(columns, chunk.iterrows()):
            asset = assets.get(movie["영화코드"], {})

            with column:
                with st.container(border=True):
                    show_poster(asset)

                    st.markdown(
                        f'<div class="rank-number">RANK {int(movie["순위"]):02d} · {html.escape(movie["순위 변동"])}</div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<div class="movie-card-title">{html.escape(movie["영화명"])}</div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<div class="small-muted">관객 {format_number(movie["관객 수"])}명</div>',
                        unsafe_allow_html=True,
                    )

                    if asset.get("overview"):
                        with st.expander("줄거리"):
                            st.write(asset["overview"])
                    else:
                        st.caption("한국어 줄거리 없음")


# ============================================================
# 10. 차트: 관객 수 또는 매출액
# ============================================================
st.markdown(
    '<div class="section-eyebrow">COMPARISON</div>',
    unsafe_allow_html=True,
)

st.subheader("지표 비교")

chart_choice = st.radio(
    "비교 지표",
    options=["관객 수", "매출액"],
    horizontal=True,
    label_visibility="collapsed",
)

chart_df = filtered_df[["영화명", chart_choice]].copy()

if not chart_df.empty:
    chart_df = (
        chart_df.sort_values(chart_choice, ascending=True)
        .set_index("영화명")
    )

    st.bar_chart(
        chart_df,
        horizontal=True,
        use_container_width=True,
    )


# ============================================================
# 11. 전체 표와 CSV 다운로드
# ============================================================
st.markdown(
    '<div class="section-eyebrow">DATA TABLE</div>',
    unsafe_allow_html=True,
)

st.subheader("상세 기록")

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

table_df = filtered_df[visible_columns].copy()

table_df["개봉일"] = table_df["개봉일"].map(format_date)

for column in [
    "관객 수",
    "매출액",
    "누적 관객 수",
    "스크린 수",
    "상영 횟수",
]:
    table_df[column] = table_df[column].map(format_number)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)

csv_bytes = table_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="현재 표를 CSV로 저장",
    data=csv_bytes,
    file_name=f"k obis_boxoffice_{yesterday}.csv".replace(" ", ""),
    mime="text/csv",
)

if previous_result["error"]:
    st.caption(
        "전일 자료를 조회하지 못해 관객 증감 비교 일부를 표시하지 못했습니다."
    )

st.markdown(
    '<div class="rule"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="source-note">
        박스오피스 순위·매출·관객 수: 영화진흥위원회 KOBIS 오픈API<br>
        포스터·한국어 줄거리: KOBIS 웹페이지 제공 데이터 우선,
        누락 시 TMDB API(키 등록 시) 보완<br>
        전일 대비 관객 수는 전일 TOP 10에 포함된 영화만 직접 비교합니다.
        전일 TOP 10 밖인 영화는 비교값을 단정하지 않습니다.
    </div>
    """,
    unsafe_allow_html=True,
)

if tmdb_api_key:
    st.caption(
        "This product uses the TMDB API but is not endorsed or certified by TMDB."
    )
