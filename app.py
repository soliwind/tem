
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urljoin


# =========================================================
# 1. 페이지 기본 설정
# =========================================================

st.set_page_config(
    page_title="Daily Box Office",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 2. 화면 디자인
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #f6f7f9;
        color: #17191c;
    }

    html, body, [class*="css"] {
        font-family:
            Pretendard,
            "Noto Sans KR",
            "Apple SD Gothic Neo",
            "Malgun Gothic",
            sans-serif;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 3.2rem;
        padding-bottom: 4rem;
    }

    .page-title {
        font-size: 2.15rem;
        font-weight: 750;
        letter-spacing: -0.045em;
        color: #111318;
        margin-bottom: 0.35rem;
    }

    .page-subtitle {
        color: #737982;
        font-size: 0.94rem;
        margin-bottom: 2rem;
        letter-spacing: -0.02em;
    }

    .date-label {
        display: inline-block;
        padding: 0.42rem 0.72rem;
        border-radius: 7px;
        background: #ffffff;
        border: 1px solid #e3e6eb;
        color: #5f656e;
        font-size: 0.82rem;
        margin-bottom: 1.2rem;
    }

    /* 1위 영화 메인 영역 */
    .hero-card {
        background: #ffffff;
        border: 1px solid #e4e7eb;
        border-radius: 18px;
        padding: 1.15rem;
        box-shadow: 0 5px 24px rgba(20, 24, 32, 0.045);
        height: 100%;
    }

    .hero-poster {
        width: 100%;
        aspect-ratio: 2 / 3;
        object-fit: cover;
        border-radius: 11px;
        display: block;
        background: #eceef1;
    }

    .hero-info {
        padding: 0.45rem 0.25rem 0.25rem 0.4rem;
    }

    .hero-rank {
        color: #8a9098;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 0.45rem;
    }

    .hero-title {
        color: #15171b;
        font-size: 1.65rem;
        line-height: 1.25;
        font-weight: 750;
        letter-spacing: -0.045em;
        margin-bottom: 0.45rem;
    }

    .hero-meta {
        color: #858b94;
        font-size: 0.84rem;
        margin-bottom: 1.15rem;
    }

    .synopsis-title {
        color: #444a52;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .synopsis {
        color: #686e77;
        font-size: 0.9rem;
        line-height: 1.7;
        word-break: keep-all;
        display: -webkit-box;
        -webkit-line-clamp: 7;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    /* 지표 */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e4e7eb;
        border-radius: 14px;
        padding: 1.05rem 1.15rem;
        min-height: 104px;
        box-shadow: 0 4px 18px rgba(20, 24, 32, 0.03);
    }

    .metric-label {
        color: #777d86;
        font-size: 0.79rem;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        color: #16181c;
        font-size: 1.45rem;
        line-height: 1.15;
        font-weight: 750;
        letter-spacing: -0.04em;
    }

    /* 섹션 */
    .section-title {
        color: #202329;
        font-size: 1.05rem;
        font-weight: 750;
        margin-top: 2.4rem;
        margin-bottom: 0.85rem;
        letter-spacing: -0.025em;
    }

    /* 2~5위 카드 */
    .movie-card {
        background: #ffffff;
        border: 1px solid #e4e7eb;
        border-radius: 14px;
        overflow: hidden;
        height: 100%;
        box-shadow: 0 4px 18px rgba(20, 24, 32, 0.025);
    }

    .movie-poster {
        width: 100%;
        aspect-ratio: 2 / 3;
        object-fit: cover;
        display: block;
        background: #eceef1;
    }

    .movie-card-body {
        padding: 0.9rem;
    }

    .movie-rank {
        color: #8b9199;
        font-size: 0.73rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }

    .movie-name {
        color: #1a1c20;
        font-size: 0.96rem;
        line-height: 1.35;
        font-weight: 700;
        letter-spacing: -0.025em;
        min-height: 2.55em;
        margin-bottom: 0.55rem;
    }

    .movie-audience {
        color: #626871;
        font-size: 0.78rem;
    }

    /* 안내 박스 */
    .guide-box {
        background: #ffffff;
        border: 1px solid #dfe3e8;
        border-radius: 12px;
        padding: 1.1rem 1.2rem;
        color: #565c65;
        font-size: 0.9rem;
        line-height: 1.7;
    }

    .guide-box strong {
        color: #262a30;
    }

    /* 출처 */
    .source-note {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e4e7eb;
        color: #8a9098;
        font-size: 0.77rem;
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. 상수
# =========================================================

KOBIS_API_URL = (
    "https://www.kobis.or.kr/"
    "kobisopenapi/webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)

KOBIS_BASE_URL = "https://www.kobis.or.kr"


# =========================================================
# 4. 한국 시간 기준으로 어제 구하기
# =========================================================

def get_yesterday_kst():
    """
    배포 서버의 시간대와 관계없이
    한국 시간(Asia/Seoul)을 기준으로 어제 날짜를 계산합니다.
    """
    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst).date()
    return today_kst - timedelta(days=1)


# =========================================================
# 5. 숫자 표시용 함수
# =========================================================

def format_number(value):
    """숫자를 1,234처럼 보기 좋게 표시합니다."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "-"


# =========================================================
# 6. 포스터 URL 정리
# =========================================================

def make_poster_url(poster_url):
    """
    KOBIS에서 상대경로로 포스터 주소가 오는 경우
    실제 접속 가능한 전체 주소로 바꿉니다.

    이미 https://로 시작하는 주소라면 그대로 사용합니다.
    """
    if not poster_url:
        return None

    poster_url = str(poster_url).strip()

    if poster_url.startswith("http://") or poster_url.startswith("https://"):
        return poster_url

    return urljoin(KOBIS_BASE_URL, poster_url)


# =========================================================
# 7. 줄거리 정리
# =========================================================

def clean_synopsis(synopsis):
    """KOBIS 줄거리의 불필요한 공백과 줄바꿈을 정리합니다."""
    if not synopsis:
        return "등록된 줄거리 정보가 없습니다."

    text = str(synopsis).replace("\r", "\n")

    # 너무 많은 빈 줄을 하나의 공백으로 정리합니다.
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    return " ".join(lines)


# =========================================================
# 8. KOBIS API 호출
# =========================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_box_office(target_date):
    """
    KOBIS 일일 박스오피스 API를 호출합니다.

    캐시를 30분 적용해 새로고침을 반복해도
    API를 불필요하게 계속 호출하지 않도록 합니다.

    반환:
        성공 -> 영화 목록, None
        실패 -> None, 오류 메시지
    """

    # 인증키는 코드에 직접 작성하지 않고
    # Streamlit Cloud Secrets에서 가져옵니다.
    try:
        api_key = st.secrets["KOBIS_KEY"]
    except KeyError:
        return None, (
            "KOBIS_KEY를 찾을 수 없습니다. "
            "Streamlit Cloud의 App settings > Secrets에서 "
            "KOBIS_KEY가 등록되어 있는지 확인해 주세요."
        )

    if not api_key or not str(api_key).strip():
        return None, (
            "KOBIS_KEY가 비어 있습니다. "
            "Streamlit Cloud Secrets에 유효한 KOBIS 인증키를 등록해 주세요."
        )

    target_dt = target_date.strftime("%Y%m%d")

    params = {
        "key": str(api_key).strip(),
        "targetDt": target_dt,
    }

    try:
        response = requests.get(
            KOBIS_API_URL,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout:
        return None, (
            "KOBIS API 요청 시간이 초과되었습니다. "
            "잠시 후 다시 실행해 주세요."
        )

    except requests.exceptions.HTTPError:
        return None, (
            f"KOBIS API가 HTTP {response.status_code} 오류를 반환했습니다. "
            "KOBIS API 서버 상태를 확인해 주세요."
        )

    except requests.exceptions.RequestException as exc:
        return None, (
            "KOBIS API에 연결하지 못했습니다. "
            "네트워크 연결 또는 KOBIS API 서버 상태를 확인해 주세요."
        )

    # HTTP 200이어도 KOBIS가 faultInfo를 반환할 수 있으므로
    # 응답 내용을 반드시 별도로 확인합니다.
    try:
        data = response.json()
    except ValueError:
        return None, (
            "KOBIS API 응답을 JSON으로 읽을 수 없습니다. "
            "API 응답 상태를 확인해 주세요."
        )

    fault_info = data.get("faultInfo")

    if fault_info:
        error_code = fault_info.get("errorCode", "알 수 없음")
        message = fault_info.get(
            "message",
            "KOBIS API 오류가 발생했습니다.",
        )

        return None, (
            f"KOBIS API 오류가 발생했습니다. "
            f"오류 코드: {error_code}. {message} "
            "KOBIS_KEY가 정확한지 확인해 주세요."
        )

    box_office_result = data.get("boxOfficeResult")

    if not isinstance(box_office_result, dict):
        return None, (
            "KOBIS 응답에 boxOfficeResult가 없습니다. "
            "조회 날짜와 KOBIS API 응답 상태를 확인해 주세요."
        )

    movie_list = box_office_result.get("dailyBoxOfficeList")

    if not isinstance(movie_list, list) or not movie_list:
        return None, (
            f"{target_dt}의 일일 박스오피스 목록이 없습니다. "
            "KOBIS에서 해당 날짜의 집계가 완료되었는지 확인해 주세요."
        )

    return movie_list, None


# =========================================================
# 9. API 데이터를 화면용 데이터프레임으로 변환
# =========================================================

def make_dataframe(movie_list):
    """
    KOBIS 응답의 문자열 숫자를 실제 숫자로 변환하고
    화면에서 사용할 컬럼을 정리합니다.
    """

    rows = []

    for movie in movie_list:
        try:
            rank = int(movie.get("rank", 0))
        except (TypeError, ValueError):
            rank = 0

        try:
            audience = int(movie.get("audiCnt", 0))
        except (TypeError, ValueError):
            audience = 0

        try:
            accumulated = int(movie.get("audiAcc", 0))
        except (TypeError, ValueError):
            accumulated = 0

        try:
            screens = int(movie.get("scrnCnt", 0))
        except (TypeError, ValueError):
            screens = 0

        rows.append(
            {
                "순위": rank,
                "영화명": str(movie.get("movieNm") or "-").strip(),
                "개봉일": str(movie.get("openDt") or "-").strip(),
                "관객수": audience,
                "누적관객": accumulated,
                "스크린수": screens,

                # 아래 정보는 포스터와 설명을 위해 사용합니다.
                "포스터": make_poster_url(movie.get("thumbUrl")),
                "줄거리": clean_synopsis(movie.get("synop")),

                # 일부 KOBIS 응답에서 제공되는 영화 코드입니다.
                "movieCd": movie.get("movieCd"),
            }
        )

    return pd.DataFrame(rows)


# =========================================================
# 10. HTML에 넣기 전 텍스트 안전 처리
# =========================================================

def safe_text(value):
    """
    영화 제목이나 설명에 HTML 특수문자가 있어도
    화면의 HTML 구조가 깨지지 않도록 처리합니다.
    """
    text = str(value or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# =========================================================
# 11. 제목
# =========================================================

st.markdown(
    '<div class="page-title">Daily Box Office</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="page-subtitle">전국 일일 박스오피스 주요 지표</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 12. 조회 날짜
# =========================================================

yesterday = get_yesterday_kst()

st.markdown(
    f"""
    <div class="date-label">
        집계 기준일 · {yesterday.strftime("%Y.%m.%d")}
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 13. API 데이터 가져오기
# =========================================================

movie_list, error_message = get_box_office(yesterday)


# =========================================================
# 14. API 오류 처리
# =========================================================

if error_message:
    st.markdown(
        f"""
        <div class="guide-box">
            <strong>박스오피스 데이터를 불러오지 못했습니다.</strong><br><br>
            {safe_text(error_message)}<br><br>

            <strong>확인할 항목</strong><br>
            · Streamlit Cloud Secrets에 <code>KOBIS_KEY</code>가 등록되어 있는지 확인<br>
            · KOBIS 인증키가 정확하고 활성 상태인지 확인<br>
            · 조회일의 일일 박스오피스가 집계되었는지 확인<br>
            · KOBIS API 서버가 정상적으로 응답하는지 확인
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# =========================================================
# 15. 영화 목록이 비어 있는 경우
# =========================================================

if not movie_list:
    st.markdown(
        """
        <div class="guide-box">
            <strong>표시할 박스오피스 데이터가 없습니다.</strong><br><br>
            KOBIS에서 해당 날짜의 일일 박스오피스가 아직 집계되지 않았거나
            API 응답에 영화 목록이 포함되지 않았을 수 있습니다.<br><br>
            조회 기준일, KOBIS API 상태, KOBIS_KEY 설정을 확인해 주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# =========================================================
# 16. 데이터프레임 생성
# =========================================================

df = make_dataframe(movie_list)

if df.empty:
    st.markdown(
        """
        <div class="guide-box">
            <strong>표시할 영화 데이터가 없습니다.</strong><br><br>
            KOBIS API에서 영화 목록을 받았지만
            화면에 표시할 데이터로 변환하지 못했습니다.
            API 응답 형식을 확인해 주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# 순위가 정상적으로 들어온 영화부터 표시합니다.
df = df.sort_values("순위").reset_index(drop=True)


# =========================================================
# 17. 1위 영화
# =========================================================

first_movie = df.iloc[0]

poster_url = first_movie["포스터"]

if poster_url:
    poster_html = (
        f'<img class="hero-poster" '
        f'src="{safe_text(poster_url)}" '
        f'alt="{safe_text(first_movie["영화명"])} 포스터">'
    )
else:
    poster_html = (
        '<div class="hero-poster" '
        'style="display:flex;align-items:center;'
        'justify-content:center;color:#8a9098;">'
        "포스터 없음"
        "</div>"
    )


hero_col1, hero_col2 = st.columns([0.33, 0.67], gap="large")

with hero_col1:
    st.markdown(
        f"""
        <div class="hero-card">
            {poster_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_col2:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-info">
                <div class="hero-rank">BOX OFFICE No. 1</div>

                <div class="hero-title">
                    {safe_text(first_movie["영화명"])}
                </div>

                <div class="hero-meta">
                    개봉일 {safe_text(first_movie["개봉일"])}
                </div>

                <div class="synopsis-title">줄거리</div>

                <div class="synopsis">
                    {safe_text(first_movie["줄거리"])}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 18. 1위 영화 지표 카드
# =========================================================

st.markdown(
    '<div class="section-title">1위 주요 지표</div>',
    unsafe_allow_html=True,
)

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">관객수</div>
            <div class="metric-value">
                {format_number(first_movie["관객수"])}명
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric_col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">누적관객</div>
            <div class="metric-value">
                {format_number(first_movie["누적관객"])}명
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric_col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">스크린수</div>
            <div class="metric-value">
                {format_number(first_movie["스크린수"])}개
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 19. 2~5위 영화 포스터 카드
# =========================================================

if len(df) > 1:
    st.markdown(
        '<div class="section-title">상위권 영화</div>',
        unsafe_allow_html=True,
    )

    top_movies = df.iloc[1:5]

    columns = st.columns(len(top_movies), gap="medium")

    for column, (_, movie) in zip(columns, top_movies.iterrows()):

        with column:
            movie_poster = movie["포스터"]

            if movie_poster:
                poster_html = (
                    f'<img class="movie-poster" '
                    f'src="{safe_text(movie_poster)}" '
                    f'alt="{safe_text(movie["영화명"])} 포스터">'
                )
            else:
                poster_html = (
                    '<div class="movie-poster" '
                    'style="display:flex;align-items:center;'
                    'justify-content:center;color:#8a9098;">'
                    "포스터 없음"
                    "</div>"
                )

            st.markdown(
                f"""
                <div class="movie-card">
                    {poster_html}

                    <div class="movie-card-body">
                        <div class="movie-rank">
                            No. {movie["순위"]}
                        </div>

                        <div class="movie-name">
                            {safe_text(movie["영화명"])}
                        </div>

                        <div class="movie-audience">
                            관객 {format_number(movie["관객수"])}명
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================
# 20. 관객수 상위 5편 그래프
# =========================================================

st.markdown(
    '<div class="section-title">관객수 상위 5편</div>',
    unsafe_allow_html=True,
)

top5 = df.head(5).copy()

chart_data = (
    top5[["영화명", "관객수"]]
    .set_index("영화명")
)

st.bar_chart(
    chart_data,
    horizontal=True,
    x="관객수",
    height=320,
)


# =========================================================
# 21. 전체 순위 표
# =========================================================

st.markdown(
    '<div class="section-title">전체 순위</div>',
    unsafe_allow_html=True,
)

display_df = df[
    [
        "순위",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]
].copy()

# 화면에서는 천 단위 쉼표를 붙여 읽기 쉽게 표시합니다.
display_df["관객수"] = display_df["관객수"].map(
    lambda value: f"{value:,}"
)

display_df["누적관객"] = display_df["누적관객"].map(
    lambda value: f"{value:,}"
)

display_df["스크린수"] = display_df["스크린수"].map(
    lambda value: f"{value:,}"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위",
            width="small",
        ),
        "영화명": st.column_config.TextColumn(
            "영화명",
            width="large",
        ),
        "개봉일": st.column_config.TextColumn(
            "개봉일",
            width="medium",
        ),
        "관객수": st.column_config.TextColumn(
            "관객수",
            width="medium",
        ),
        "누적관객": st.column_config.TextColumn(
            "누적관객",
            width="medium",
        ),
        "스크린수": st.column_config.TextColumn(
            "스크린수",
            width="medium",
        ),
    },
)


# =========================================================
# 22. 데이터 출처
# =========================================================

st.markdown(
    """
    <div class="source-note">
        데이터 출처 · 영화진흥위원회 영화관입장권통합전산망(KOBIS)
    </div>
    """,
    unsafe_allow_html=True,
)