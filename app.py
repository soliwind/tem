import html
import re
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# =========================================================
# 1. 기본 설정
# =========================================================

st.set_page_config(
    page_title="어제의 박스오피스",
    layout="wide",
)

KOBIS_BOXOFFICE_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

KOBIS_MOVIE_INFO_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "movie/searchMovieInfo.json"
)

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# =========================================================
# 2. 페이지 디자인
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family:
            "Noto Sans KR",
            "Pretendard",
            "Apple SD Gothic Neo",
            "Malgun Gothic",
            sans-serif;
    }

    .stApp {
        background: #f5f6f8;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    h1 {
        color: #191b20;
        font-weight: 800 !important;
        letter-spacing: -0.055em;
    }

    h2, h3 {
        color: #202329;
        font-weight: 700 !important;
        letter-spacing: -0.035em;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 18px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border-radius: 20px;
        border-color: #e5e7eb;
    }

    div[data-testid="stImage"] img {
        border-radius: 10px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    .source-note {
        color: #858a93;
        font-size: 0.82rem;
        line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. 공통 함수
# =========================================================

def read_secret(name):
    """Streamlit Secrets에서 설정값을 안전하게 읽습니다."""
    try:
        return str(st.secrets[name]).strip()
    except Exception:
        return ""


def clean_text(value):
    """
    HTML 태그와 HTML 특수문자를 정리합니다.

    예:
    <div>영화 제목</div> -> 영화 제목
    &lt;div&gt;영화 제목&lt;/div&gt; -> 영화 제목
    """

    if value is None:
        return ""

    text = str(value)

    # 이중으로 인코딩된 HTML도 처리할 수 있게 디코딩합니다.
    for _ in range(2):
        text = html.unescape(text)

    # 줄바꿈 태그는 실제 줄바꿈으로 변경합니다.
    text = re.sub(
        r"<\s*br\s*/?\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # 일반적인 HTML 태그를 제거합니다.
    text = re.sub(
        r"<\s*/?\s*[a-zA-Z][^>]*>",
        "",
        text,
    )

    # 남은 HTML 특수문자를 일반 문자로 변환합니다.
    text = html.unescape(text)

    # 연속된 빈 줄을 정리합니다.
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)

    return text.strip()


def to_int(value):
    """API에서 문자열로 받은 숫자도 정수로 변환합니다."""
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def format_number(value):
    """숫자에 천 단위 쉼표를 붙입니다."""
    return f"{to_int(value):,}"


def format_date(value):
    """YYYYMMDD 형식의 날짜를 YYYY.MM.DD 형식으로 표시합니다."""
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) == 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:8]}"

    return str(value or "정보 없음")


def normalize_title(value):
    """영화 제목 비교를 위해 공백과 문장부호를 제거합니다."""
    text = clean_text(value).lower()
    return re.sub(r"[\W_]", "", text, flags=re.UNICODE)


def get_yesterday_kst():
    """한국 시간 기준으로 어제 날짜를 YYYYMMDD 형식으로 반환합니다."""
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    yesterday = now_kst - timedelta(days=1)

    return yesterday.strftime("%Y%m%d")


# =========================================================
# 4. KOBIS 일일 박스오피스 조회
# =========================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_box_office(target_date, api_key):
    """
    KOBIS에서 일일 박스오피스 데이터를 불러옵니다.

    포스터와 줄거리는 이 API의 응답에 있다고 가정하지 않습니다.
    """

    params = {
        "key": api_key,
        "targetDt": target_date,
    }

    try:
        response = requests.get(
            KOBIS_BOXOFFICE_URL,
            params=params,
            timeout=15,
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        return None, "KOBIS API 응답 시간이 초과되었습니다."

    except requests.exceptions.HTTPError:
        return None, (
            "KOBIS API에서 HTTP 오류가 발생했습니다. "
            "API 상태와 요청 정보를 확인해 주세요."
        )

    except requests.exceptions.RequestException:
        return None, (
            "KOBIS API에 연결하지 못했습니다. "
            "네트워크 또는 API 서버 상태를 확인해 주세요."
        )

    try:
        data = response.json()
    except ValueError:
        return None, "KOBIS 응답을 JSON으로 읽을 수 없습니다."

    # KOBIS는 일부 API 오류를 HTTP 200 응답 안에 담기도 합니다.
    fault = data.get("faultInfo")

    if fault:
        message = clean_text(
            fault.get("message", "알 수 없는 API 오류")
        )
        return None, f"KOBIS API 오류: {message}"

    result = data.get("boxOfficeResult")

    if not isinstance(result, dict):
        return None, (
            "박스오피스 결과가 응답에 없습니다. "
            "API 요청 날짜와 키를 확인해 주세요."
        )

    movie_list = result.get("dailyBoxOfficeList", [])

    if not movie_list:
        return None, (
            f"{format_date(target_date)} 날짜의 "
            "박스오피스 데이터가 없습니다."
        )

    return movie_list, None


# =========================================================
# 5. KOBIS 영화 상세정보에서 영문 제목 보조 조회
# =========================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_kobis_english_title(movie_code, api_key):
    """
    영화 코드로 KOBIS 영화 상세정보를 조회합니다.

    영문 제목을 TMDB 검색에 보조적으로 사용합니다.
    실패해도 박스오피스 화면에는 영향을 주지 않습니다.
    """

    if not movie_code or not api_key:
        return ""

    try:
        response = requests.get(
            KOBIS_MOVIE_INFO_URL,
            params={
                "key": api_key,
                "movieCd": movie_code,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("faultInfo"):
            return ""

        movie_info = (
            data.get("movieInfoResult", {})
            .get("movieInfo", {})
        )

        return clean_text(movie_info.get("movieNmEn", ""))

    except (
        requests.exceptions.RequestException,
        ValueError,
        TypeError,
    ):
        return ""


# =========================================================
# 6. TMDB에서 포스터와 줄거리 검색
# =========================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_tmdb_movie_data(
    korean_title,
    english_title,
    release_date,
    tmdb_api_key,
):
    """
    TMDB에서 영화 제목을 검색하고 포스터와 줄거리를 가져옵니다.

    제목과 개봉연도를 함께 비교해 엉뚱한 영화가 선택될
    가능성을 줄입니다.
    """

    empty_result = {
        "poster_bytes": None,
        "poster_url": None,
        "overview": "",
        "tmdb_url": None,
        "message": None,
    }

    if not tmdb_api_key:
        return empty_result

    year = str(release_date or "")[:4]

    # 한국어 제목을 먼저 검색하고, 영문 제목이 있으면
    # 영어 검색도 추가로 실행합니다.
    search_queries = []

    if korean_title:
        search_queries.append((korean_title, "ko-KR"))

    if (
        english_title
        and normalize_title(english_title)
        != normalize_title(korean_title)
    ):
        search_queries.append((english_title, "en-US"))

    if not search_queries:
        return {
            **empty_result,
            "message": "검색할 영화 제목이 없습니다.",
        }

    results_by_id = {}

    try:
        for query, language in search_queries:
            params = {
                "api_key": tmdb_api_key,
                "query": query,
                "language": language,
                "include_adult": "false",
            }

            if year.isdigit() and len(year) == 4:
                params["primary_release_year"] = year

            response = requests.get(
                TMDB_SEARCH_URL,
                params=params,
                timeout=12,
            )

            if response.status_code == 401:
                return {
                    **empty_result,
                    "message": (
                        "TMDB API 키 인증에 실패했습니다. "
                        "Secrets의 TMDB_API_KEY를 확인해 주세요."
                    ),
                }

            response.raise_for_status()
            search_data = response.json()

            results = search_data.get("results", [])

            # 개봉연도 필터로 검색 결과가 없으면
            # 연도 필터를 빼고 다시 검색합니다.
            if not results and "primary_release_year" in params:
                params.pop("primary_release_year")

                response = requests.get(
                    TMDB_SEARCH_URL,
                    params=params,
                    timeout=12,
                )
                response.raise_for_status()
                results = response.json().get("results", [])

            for item in results:
                item_id = item.get("id")

                if item_id is not None:
                    results_by_id[item_id] = item

    except requests.exceptions.RequestException:
        return {
            **empty_result,
            "message": "TMDB API에 연결하지 못했습니다.",
        }

    except ValueError:
        return {
            **empty_result,
            "message": "TMDB 응답을 JSON으로 읽지 못했습니다.",
        }

    candidates = list(results_by_id.values())

    if not candidates:
        return {
            **empty_result,
            "message": "TMDB에서 일치하는 영화를 찾지 못했습니다.",
        }

    # 검색어와 영화 제목의 유사도를 계산합니다.
    normalized_queries = [
        normalize_title(query)
        for query, _ in search_queries
        if normalize_title(query)
    ]

    scored_candidates = []

    for item in candidates:
        candidate_titles = [
            normalize_title(item.get("title", "")),
            normalize_title(item.get("original_title", "")),
        ]

        candidate_titles = [
            value for value in candidate_titles if value
        ]

        similarity = 0.0
        exact_match = False

        for query in normalized_queries:
            for candidate_title in candidate_titles:
                ratio = SequenceMatcher(
                    None,
                    query,
                    candidate_title,
                ).ratio()

                if query == candidate_title:
                    exact_match = True
                    ratio = 1.0

                elif (
                    len(query) >= 3
                    and (
                        query in candidate_title
                        or candidate_title in query
                    )
                ):
                    ratio = max(ratio, 0.85)

                similarity = max(similarity, ratio)

        candidate_year = str(
            item.get("release_date", "")
        )[:4]

        # 제목이 잘 맞는 결과를 우선하고,
        # 개봉연도가 같으면 추가 점수를 줍니다.
        score = similarity * 10

        if exact_match:
            score += 5

        if (
            year.isdigit()
            and candidate_year == year
        ):
            score += 2

        if item.get("poster_path"):
            score += 0.2

        score += min(
            to_int(item.get("vote_count", 0)),
            1000,
        ) / 100000

        scored_candidates.append(
            (score, similarity, item)
        )

    scored_candidates.sort(
        key=lambda candidate: candidate[0],
        reverse=True,
    )

    _, best_similarity, best_movie = scored_candidates[0]

    # 이름이 너무 다르면 다른 영화의 포스터를 임의로
    # 표시하지 않습니다.
    same_year_single_result = (
        len(candidates) == 1
        and year.isdigit()
        and str(best_movie.get("release_date", ""))[:4] == year
    )

    if (
        best_similarity < 0.45
        and not same_year_single_result
    ):
        return {
            **empty_result,
            "message": (
                "영화 제목이 충분히 일치하는 검색 결과가 없습니다."
            ),
        }

    poster_path = best_movie.get("poster_path")
    poster_url = (
        f"{TMDB_IMAGE_BASE}{poster_path}"
        if poster_path
        else None
    )

    overview = clean_text(best_movie.get("overview", ""))

    # 검색 결과에 줄거리가 없으면 영화 상세정보를 조회합니다.
    movie_id = best_movie.get("id")

    if not overview and movie_id:
        try:
            detail_response = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}",
                params={
                    "api_key": tmdb_api_key,
                    "language": "ko-KR",
                },
                timeout=10,
            )
            detail_response.raise_for_status()

            detail_data = detail_response.json()
            overview = clean_text(
                detail_data.get("overview", "")
            )

        except (
            requests.exceptions.RequestException,
            ValueError,
        ):
            pass

    # 포스터 파일을 서버에서 직접 내려받습니다.
    # 이미지 주소를 브라우저에서 직접 읽는 데 실패하는
    # 상황을 줄이기 위한 처리입니다.
    poster_bytes = None

    if poster_url:
        try:
            image_response = requests.get(
                poster_url,
                timeout=12,
            )
            image_response.raise_for_status()

            content_type = image_response.headers.get(
                "Content-Type",
                "",
            )

            if (
                content_type.lower().startswith("image/")
                and image_response.content
            ):
                poster_bytes = image_response.content

        except requests.exceptions.RequestException:
            poster_bytes = None

    tmdb_url = (
        f"https://www.themoviedb.org/movie/{movie_id}"
        if movie_id
        else None
    )

    return {
        "poster_bytes": poster_bytes,
        "poster_url": poster_url,
        "overview": overview,
        "tmdb_url": tmdb_url,
        "message": None,
    }


# =========================================================
# 7. 포스터 출력
# =========================================================

def render_poster(movie_data, use_container_width=True):
    """
    내려받은 이미지 데이터를 먼저 사용하고,
    필요하면 이미지 URL을 대체 수단으로 사용합니다.
    """

    poster = movie_data.get("poster_bytes")

    if poster is None:
        poster = movie_data.get("poster_url")

    if not poster:
        st.caption("등록된 포스터를 찾지 못했습니다.")
        return

    try:
        st.image(
            poster,
            use_container_width=use_container_width,
        )
    except Exception:
        st.caption("포스터 이미지를 표시하지 못했습니다.")


# =========================================================
# 8. API 키와 날짜 설정
# =========================================================

kobis_api_key = read_secret("KOBIS_KEY")
tmdb_api_key = read_secret("TMDB_API_KEY")

yesterday = get_yesterday_kst()

st.title("어제의 박스오피스")

st.caption(
    f"{format_date(yesterday)} 기준 · "
    "영화진흥위원회 KOBIS 일일 박스오피스"
)

if not kobis_api_key:
    st.error(
        "KOBIS_KEY가 없습니다. "
        "Streamlit Cloud의 Secrets에 KOBIS_KEY를 등록해 주세요."
    )
    st.stop()

if not tmdb_api_key:
    st.warning(
        "포스터와 줄거리를 표시하려면 Streamlit Cloud의 Secrets에 "
        "TMDB_API_KEY를 추가해야 합니다. "
        "KOBIS_KEY는 관객 수와 순위 조회에 사용됩니다."
    )


# =========================================================
# 9. 박스오피스 조회 및 데이터 정리
# =========================================================

with st.spinner("박스오피스 데이터를 불러오는 중입니다..."):
    movie_list, error_message = get_box_office(
        yesterday,
        kobis_api_key,
    )

if error_message:
    st.error(error_message)

    with st.container(border=True):
        st.subheader("확인할 사항")
        st.write(
            "KOBIS_KEY가 올바른지, "
            "Streamlit Cloud의 Secrets 설정에 오타가 없는지, "
            "KOBIS API가 정상적으로 응답하는지 확인해 주세요."
        )

    st.stop()

if not movie_list:
    st.info("표시할 박스오피스 데이터가 없습니다.")
    st.stop()


rows = []

for movie in movie_list:
    rows.append(
        {
            "순위": to_int(movie.get("rank")),
            "영화명": clean_text(movie.get("movieNm", "")),
            "개봉일": str(movie.get("openDt", "") or ""),
            "관객 수": to_int(movie.get("audiCnt")),
            "누적 관객 수": to_int(movie.get("audiAcc")),
            "스크린 수": to_int(movie.get("scrnCnt")),
            "영화코드": str(movie.get("movieCd", "") or ""),
        }
    )

df = pd.DataFrame(rows)

if df.empty:
    st.info("표시할 영화 데이터가 없습니다.")
    st.stop()

df = df.sort_values("순위").reset_index(drop=True)


# =========================================================
# 10. 상위 5개 영화의 포스터 및 줄거리 조회
# =========================================================

movie_assets = {}

if tmdb_api_key:
    with st.spinner("영화 포스터와 줄거리를 불러오는 중입니다..."):
        for _, movie in df.head(5).iterrows():
            movie_code = movie["영화코드"]
            movie_title = movie["영화명"]

            # 한국어 제목 검색이 잘 되지 않는 경우를 위해
            # KOBIS 상세정보의 영문 제목도 보조로 사용합니다.
            english_title = get_kobis_english_title(
                movie_code,
                kobis_api_key,
            )

            asset = get_tmdb_movie_data(
                korean_title=movie_title,
                english_title=english_title,
                release_date=movie["개봉일"],
                tmdb_api_key=tmdb_api_key,
            )

            movie_assets[movie_code] = asset

    # API 키가 틀렸을 때 원인을 화면에 안내합니다.
    tmdb_messages = {
        asset["message"]
        for asset in movie_assets.values()
        if asset.get("message")
    }

    if any(
        "API 키 인증" in message
        for message in tmdb_messages
    ):
        st.error(
            "TMDB_API_KEY 인증에 실패했습니다. "
            "TMDB의 API v3 키가 올바르게 등록되어 있는지 확인해 주세요."
        )


# =========================================================
# 11. 1위 영화
# =========================================================

top_movie = df.iloc[0]
top_asset = movie_assets.get(
    top_movie["영화코드"],
    {},
)

st.subheader("오늘의 1위")

# 중요:
# 여는 HTML 태그와 닫는 HTML 태그를 서로 다른 호출에
# 나누지 않습니다. 포스터와 모든 텍스트가 같은
# Streamlit 컨테이너 안에 있어야 카드가 깨지지 않습니다.
with st.container(border=True, key="hero-card"):
    poster_col, detail_col = st.columns(
        [0.85, 2.15],
        gap="large",
    )

    with poster_col:
        render_poster(top_asset)

    with detail_col:
        st.subheader(top_movie["영화명"])

        st.caption(
            f"개봉일 {format_date(top_movie['개봉일'])}"
            f"  ·  박스오피스 {int(top_movie['순위'])}위"
        )

        overview = clean_text(
            top_asset.get("overview", "")
        )

        if overview:
            # clean_text로 태그를 정리한 일반 텍스트를 출력합니다.
            # unsafe_allow_html을 사용하지 않습니다.
            st.write(overview)
        else:
            st.write(
                "등록된 줄거리가 없습니다. "
                "TMDB 검색 결과와 API 키를 확인해 주세요."
            )

        if top_asset.get("tmdb_url"):
            st.markdown(
                f"[TMDB에서 영화 정보 확인하기]({top_asset['tmdb_url']})"
            )


# =========================================================
# 12. 1위 영화 주요 지표
# =========================================================

st.subheader("주요 기록")

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        "일일 관객 수",
        f"{format_number(top_movie['관객 수'])}명",
    )

with metric2:
    st.metric(
        "누적 관객 수",
        f"{format_number(top_movie['누적 관객 수'])}명",
    )

with metric3:
    st.metric(
        "스크린 수",
        f"{format_number(top_movie['스크린 수'])}개",
    )


# =========================================================
# 13. 상위 5개 영화 카드
# =========================================================

st.subheader("오늘의 영화 TOP 5")

poster_columns = st.columns(5)

for index, (_, movie) in enumerate(
    df.head(5).iterrows()
):
    movie_asset = movie_assets.get(
        movie["영화코드"],
        {},
    )

    with poster_columns[index]:
        with st.container(border=True):
            render_poster(movie_asset)

            # 제목은 HTML에 삽입하지 않고 일반 텍스트로 출력합니다.
            st.write(movie["영화명"])

            st.caption(
                f"관객 {format_number(movie['관객 수'])}명"
            )


# =========================================================
# 14. 관객 수 TOP 5 차트
# =========================================================

st.subheader("TOP 5 관객 수")

chart_df = (
    df.head(5)[["영화명", "관객 수"]]
    .set_index("영화명")
)

st.bar_chart(
    chart_df,
    horizontal=True,
)


# =========================================================
# 15. 전체 박스오피스 표
# =========================================================

st.subheader("전체 박스오피스")

table_df = df[
    [
        "순위",
        "영화명",
        "개봉일",
        "관객 수",
        "누적 관객 수",
        "스크린 수",
    ]
].copy()

table_df["개봉일"] = table_df["개봉일"].map(format_date)

for column in [
    "관객 수",
    "누적 관객 수",
    "스크린 수",
]:
    table_df[column] = table_df[column].map(format_number)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# 16. 데이터 출처 및 안내
# =========================================================

st.divider()

st.markdown(
    """
    <div class="source-note">
        박스오피스 순위 및 관객 수: 영화진흥위원회 KOBIS 오픈API<br>
        영화 포스터 및 줄거리: <a href="https://www.themoviedb.org/">
        TMDB</a><br><br>
        This product uses the TMDB API but is not endorsed or certified by TMDB.
    </div>
    """,
    unsafe_allow_html=True,
)
