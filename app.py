import html
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# ---------------------------------------------------------
# 기본 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="",
    layout="wide",
)


# ---------------------------------------------------------
# 화면 디자인
# ---------------------------------------------------------
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
        padding-top: 3rem;
        padding-bottom: 4rem;
    }

    .page-title {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.06em;
        color: #15171a;
        margin-bottom: 0.3rem;
    }

    .page-subtitle {
        color: #73777d;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #202226;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
    }

    .hero-card {
        background: white;
        border: 1px solid #e7e9ed;
        border-radius: 22px;
        padding: 24px;
        box-shadow: 0 8px 28px rgba(20, 25, 35, 0.05);
    }

    .movie-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #16181c;
        letter-spacing: -0.04em;
        margin-bottom: 0.6rem;
    }

    .movie-meta {
        color: #73777d;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }

    .movie-description {
        color: #44484e;
        font-size: 0.96rem;
        line-height: 1.75;
        white-space: pre-line;
    }

    .metric-card {
        background: white;
        border: 1px solid #e7e9ed;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 6px 20px rgba(20, 25, 35, 0.04);
    }

    .metric-label {
        color: #777c83;
        font-size: 0.85rem;
        margin-bottom: 0.4rem;
    }

    .metric-value {
        color: #17191d;
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: -0.03em;
    }

    .poster-card {
        background: white;
        border: 1px solid #e7e9ed;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 5px 18px rgba(20, 25, 35, 0.04);
    }

    .poster-title {
        padding: 12px 14px 14px;
        font-size: 0.92rem;
        font-weight: 700;
        color: #24272c;
        line-height: 1.4;
    }

    .info-box {
        background: #ffffff;
        border: 1px solid #e2e5e9;
        border-radius: 16px;
        padding: 20px;
        color: #4d5259;
        line-height: 1.7;
    }

    .source-text {
        color: #92969c;
        font-size: 0.8rem;
        margin-top: 2rem;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e7e9ed;
        border-radius: 18px;
        padding: 18px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# KOBIS API 주소
# ---------------------------------------------------------
KOBIS_API_URL = (
    "https://www.kobis.or.kr/"
    "kobisopenapi/webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)

# 중요:
# thumbUrl은 "/common/mast/..."처럼 KOBIS 사이트 기준의
# 상대 주소로 내려오기 때문에 API 주소가 아닌
# KOBIS 홈페이지 주소를 기준으로 붙여야 합니다.
KOBIS_SITE_URL = "https://www.kobis.or.kr"


# ---------------------------------------------------------
# 한국 시간 기준으로 어제 날짜 구하기
# ---------------------------------------------------------
def get_yesterday_kst():
    """한국 시간(KST)을 기준으로 어제 날짜를 YYYYMMDD로 반환합니다."""
    korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
    yesterday = korea_now - timedelta(days=1)

    return yesterday.strftime("%Y%m%d")


# ---------------------------------------------------------
# 숫자를 보기 좋게 표시
# ---------------------------------------------------------
def format_number(value):
    """숫자에 천 단위 쉼표를 붙입니다."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"


# ---------------------------------------------------------
# HTML 태그와 HTML 특수문자 정리
# ---------------------------------------------------------
def clean_text(value):
    """
    API에서 설명이 HTML 형태로 들어오는 경우를 대비합니다.

    예:
    <div>치이카와: 인어섬의 비밀</div>

    -> 치이카와: 인어섬의 비밀
    """

    if value is None:
        return ""

    text = str(value)

    # <br>, <br/> 등을 줄바꿈으로 바꿉니다.
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)

    # 나머지 HTML 태그를 제거합니다.
    text = re.sub(r"<[^>]+>", "", text)

    # &nbsp;, &amp; 등의 HTML 특수문자를 실제 문자로 바꿉니다.
    text = html.unescape(text)

    # 줄바꿈이 너무 많이 반복되면 정리합니다.
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------
# 포스터 주소 만들기
# ---------------------------------------------------------
def make_poster_url(poster_path):
    """
    KOBIS에서 받은 포스터 경로를 실제 이미지 주소로 변환합니다.

    예:
    /common/mast/movie/2026/08/thumb/example.jpg

    ->
    https://www.kobis.or.kr/common/mast/movie/2026/08/thumb/example.jpg
    """

    if not poster_path:
        return None

    poster_path = str(poster_path).strip()

    if not poster_path:
        return None

    # 이미 완전한 URL이면 그대로 사용합니다.
    if poster_path.startswith("http://") or poster_path.startswith("https://"):
        return poster_path

    # 상대 경로이면 KOBIS 홈페이지 주소를 기준으로 합칩니다.
    return urljoin(KOBIS_SITE_URL, poster_path)


# ---------------------------------------------------------
# KOBIS 박스오피스 데이터 가져오기
# ---------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_box_office(target_date):
    """
    KOBIS에서 특정 날짜의 일일 박스오피스 데이터를 가져옵니다.
    """

    # Streamlit Cloud의 Secrets에서 API 키를 가져옵니다.
    try:
        api_key = st.secrets["KOBIS_KEY"].strip()
    except Exception:
        return None, (
            "KOBIS_KEY를 찾을 수 없습니다. "
            "Streamlit Cloud의 Secrets에 KOBIS_KEY가 등록되어 있는지 확인해 주세요."
        )

    if not api_key:
        return None, (
            "KOBIS_KEY가 비어 있습니다. "
            "Streamlit Cloud의 Secrets에 실제 API 키를 입력해 주세요."
        )

    params = {
        "key": api_key,
        "targetDt": target_date,
        "itemPerPage": 10,
        "multiMovieYn": "N",
        "repNationCd": "",
        "wideAreaCd": "",
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

    except requests.exceptions.HTTPError as e:
        return None, (
            f"KOBIS API에서 HTTP 오류가 발생했습니다. "
            f"상태 코드: {response.status_code}"
        )

    except requests.exceptions.RequestException as e:
        return None, (
            "KOBIS API에 연결하지 못했습니다. "
            "인터넷 연결 또는 KOBIS API 상태를 확인해 주세요."
        )

    # JSON 변환
    try:
        data = response.json()
    except ValueError:
        return None, (
            "KOBIS에서 올바른 JSON 데이터를 받지 못했습니다. "
            "잠시 후 다시 실행해 주세요."
        )

    # -----------------------------------------------------
    # 중요:
    # KOBIS는 API 키가 잘못되어도 HTTP 200을 반환하면서
    # faultInfo를 넣어주는 경우가 있습니다.
    # 따라서 HTTP 상태 코드만 확인하면 안 됩니다.
    # -----------------------------------------------------
    if "faultInfo" in data:
        fault_info = data["faultInfo"]

        error_message = fault_info.get(
            "message",
            "KOBIS API 요청에 실패했습니다.",
        )

        return None, (
            f"KOBIS API 오류: {error_message}\n\n"
            "API 키가 올바른지 확인해 주세요."
        )

    # 정상적인 박스오피스 결과가 있는지 확인
    box_office_result = data.get("boxOfficeResult")

    if not box_office_result:
        return None, (
            "KOBIS에서 박스오피스 결과를 받지 못했습니다. "
            "응답 형식을 확인해 주세요."
        )

    movie_list = box_office_result.get("dailyBoxOfficeList", [])

    if not movie_list:
        return None, (
            f"{target_date} 날짜의 박스오피스 데이터가 없습니다.\n\n"
            "KOBIS에 해당 날짜의 데이터가 등록되어 있는지 확인해 주세요."
        )

    return movie_list, None


# ---------------------------------------------------------
# DataFrame으로 변환
# ---------------------------------------------------------
def make_dataframe(movie_list):
    """KOBIS 데이터를 화면에 표시하기 편한 DataFrame으로 변환합니다."""

    rows = []

    for movie in movie_list:
        rows.append(
            {
                "순위": int(movie.get("rank", 0) or 0),
                "영화명": clean_text(movie.get("movieNm", "")),
                "개봉일": movie.get("openDt", ""),
                "관객 수": int(movie.get("audiCnt", 0) or 0),
                "누적 관객 수": int(movie.get("audiAcc", 0) or 0),
                "스크린 수": int(movie.get("scrnCnt", 0) or 0),
                "포스터": make_poster_url(movie.get("thumbUrl")),
                "줄거리": clean_text(movie.get("synop", "")),
                "영화코드": movie.get("movieCd", ""),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# 페이지 제목
# ---------------------------------------------------------
yesterday = get_yesterday_kst()

display_date = (
    f"{yesterday[:4]}년 "
    f"{int(yesterday[4:6])}월 "
    f"{int(yesterday[6:8])}일"
)

st.markdown(
    '<div class="page-title">어제의 박스오피스</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="page-subtitle">{display_date} · KOBIS 기준</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 데이터 요청
# ---------------------------------------------------------
movie_list, error_message = get_box_office(yesterday)


# ---------------------------------------------------------
# API 오류가 발생했을 때
# ---------------------------------------------------------
if error_message:
    st.markdown(
        f"""
        <div class="info-box">
            <strong>박스오피스 데이터를 불러오지 못했습니다.</strong>
            <br><br>
            {clean_text(error_message).replace(chr(10), "<br>")}
            <br><br>
            다음 항목을 확인해 주세요.
            <br>
            1. Streamlit Cloud의 Secrets에 <strong>KOBIS_KEY</strong>가 있는지
            <br>
            2. API 키에 불필요한 공백이나 따옴표가 없는지
            <br>
            3. KOBIS API가 정상적으로 응답하고 있는지
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# ---------------------------------------------------------
# 빈 데이터 방지
# ---------------------------------------------------------
if not movie_list:
    st.markdown(
        """
        <div class="info-box">
            박스오피스 데이터가 없습니다.<br><br>
            KOBIS에서 해당 날짜의 데이터가 제공되는지 확인해 주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# ---------------------------------------------------------
# DataFrame 생성
# ---------------------------------------------------------
df = make_dataframe(movie_list)

if df.empty:
    st.markdown(
        """
        <div class="info-box">
            표시할 영화 데이터가 없습니다.<br><br>
            KOBIS API 응답을 확인해 주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# ---------------------------------------------------------
# 1위 영화
# ---------------------------------------------------------
top_movie = df.iloc[0]

st.markdown(
    '<div class="section-title">오늘의 1위</div>',
    unsafe_allow_html=True,
)

hero_left, hero_right = st.columns([1, 2.3], gap="large")

with hero_left:
    poster_url = top_movie["포스터"]

    if poster_url:
        try:
            st.image(
                poster_url,
                use_container_width=True,
            )
        except Exception:
            st.info("포스터 이미지를 불러오지 못했습니다.")
    else:
        st.info("등록된 포스터가 없습니다.")


with hero_right:
    st.markdown('<div class="hero-card">', unsafe_allow_html=True)

    # 영화 제목은 HTML에 직접 넣지 않고
    # Streamlit의 일반 텍스트 출력으로 표시합니다.
    # 따라서 영화 제목에 <div> 같은 문자열이 들어와도
    # HTML 코드로 해석되지 않습니다.
    st.markdown(
        f'<div class="movie-title">{html.escape(str(top_movie["영화명"]))}</div>',
        unsafe_allow_html=True,
    )

    release_date = top_movie["개봉일"]

    if release_date and len(release_date) == 8:
        release_date = (
            f"{release_date[:4]}.{release_date[4:6]}.{release_date[6:8]}"
        )

    st.markdown(
        f'<div class="movie-meta">개봉일 {html.escape(str(release_date))}</div>',
        unsafe_allow_html=True,
    )

    synopsis = clean_text(top_movie["줄거리"])

    if synopsis:
        # 줄거리 역시 HTML을 제거한 뒤 표시합니다.
        st.markdown(
            f'<div class="movie-description">{html.escape(synopsis).replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="movie-description">등록된 줄거리가 없습니다.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# 1위 영화 주요 지표
# ---------------------------------------------------------
st.markdown(
    '<div class="section-title">주요 기록</div>',
    unsafe_allow_html=True,
)

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        "일일 관객",
        f'{format_number(top_movie["관객 수"])}명',
    )

with metric2:
    st.metric(
        "누적 관객",
        f'{format_number(top_movie["누적 관객 수"])}명',
    )

with metric3:
    st.metric(
        "스크린 수",
        f'{format_number(top_movie["스크린 수"])}개',
    )


# ---------------------------------------------------------
# 포스터 목록
# ---------------------------------------------------------
st.markdown(
    '<div class="section-title">오늘의 영화</div>',
    unsafe_allow_html=True,
)

poster_columns = st.columns(min(len(df), 5))

for index, (_, movie) in enumerate(df.head(5).iterrows()):
    with poster_columns[index]:
        poster_url = movie["포스터"]

        if poster_url:
            try:
                st.image(
                    poster_url,
                    use_container_width=True,
                )
            except Exception:
                st.info("이미지 없음")
        else:
            st.info("포스터 없음")

        # 영화 제목도 HTML로 해석하지 않도록 escape 처리
        safe_title = html.escape(str(movie["영화명"]))

        st.markdown(
            f'<div class="poster-title">{safe_title}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------
# TOP 5 관객 수 차트
# ---------------------------------------------------------
st.markdown(
    '<div class="section-title">TOP 5 관객 수</div>',
    unsafe_allow_html=True,
)

chart_df = df.head(5)[["영화명", "관객 수"]].copy()

# 차트에서는 영화 제목을 세로축에 표시합니다.
chart_df = chart_df.set_index("영화명")

st.bar_chart(
    chart_df,
    horizontal=True,
    x="관객 수",
)


# ---------------------------------------------------------
# 전체 박스오피스 표
# ---------------------------------------------------------
st.markdown(
    '<div class="section-title">전체 박스오피스</div>',
    unsafe_allow_html=True,
)

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

# 화면에서 숫자를 보기 좋게 표시
table_df["관객 수"] = table_df["관객 수"].map(format_number)
table_df["누적 관객 수"] = table_df["누적 관객 수"].map(format_number)
table_df["스크린 수"] = table_df["스크린 수"].map(format_number)

table_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객 수",
    "누적 관객 수",
    "스크린 수",
]

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# 하단 안내
# ---------------------------------------------------------
st.markdown(
    '<div class="source-text">데이터 출처: 영화진흥위원회 KOBIS 오픈API · 한국 시간 기준 전일 데이터</div>',
    unsafe_allow_html=True,
)
