# TILE TEN — Streamlit Block Puzzle

Python과 Streamlit으로 만든 10×10 블록 퍼즐 게임입니다. 클래식 블록 퍼즐의 규칙에서 영감을 얻었으며, 독자적인 이름과 색상 시스템으로 구성했습니다.

## 주요 기능

- 10×10 퍼즐 보드와 무작위 블록 3개
- 블록 선택, 배치 좌표 지정, 배치 전 미리보기
- 가로·세로 줄 제거 및 동시 제거 보너스
- 점수, 콤보, 최고 점수 표시
- 놓을 수 있는 블록이 없을 때 게임 오버 처리
- HTML/CSS 기반의 반응형 UI

## 로컬에서 실행하기

Python 3.10 이상을 권장합니다.

### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

터미널에 표시되는 로컬 URL을 브라우저에서 엽니다.

## GitHub에 업로드하기

### 방법 A: Git 명령어 사용

1. GitHub에서 새 저장소를 만듭니다. 예를 들어 저장소 이름은 `tile-ten`으로 지정할 수 있습니다.
2. 기존 파일을 업로드할 것이므로 GitHub 저장소 생성 시 README, `.gitignore`, 라이선스 파일을 자동 생성하는 옵션은 선택하지 않아도 됩니다.
3. 이 프로젝트 폴더에서 아래 명령어를 실행합니다. `YOUR-USERNAME`은 본인의 GitHub 사용자 이름으로 바꿉니다.

```bash
git init
git add app.py requirements.txt README.md .gitignore
git commit -m "Initial commit: TILE TEN block puzzle"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/tile-ten.git
git push -u origin main
```

### 방법 B: 웹사이트에서 파일 업로드

1. GitHub에서 새 저장소를 만듭니다.
2. 저장소 화면에서 **Add file → Upload files**를 선택합니다.
3. `app.py`, `requirements.txt`, `README.md`를 업로드하고 커밋합니다.
4. `.gitignore`도 저장소에 추가합니다. 터미널을 이용할 수 있다면 방법 A가 더 간편합니다.

## 웹에서 게임 공개하기

GitHub에 코드를 올리는 것만으로 Streamlit 앱이 실행되는 것은 아닙니다. 브라우저에서 다른 사람도 플레이하도록 공개하려면 Streamlit Community Cloud 같은 앱 호스팅 서비스에 배포하세요.

1. [Streamlit Community Cloud](https://share.streamlit.io/)를 엽니다.
2. GitHub 계정으로 로그인하고 **Create app**을 선택합니다.
3. 본인의 저장소, `main` 브랜치, 엔트리 파일 `app.py`를 지정합니다.
4. **Deploy**를 눌러 배포합니다.

배포가 완료되면 공유할 수 있는 `streamlit.app` 주소가 생성됩니다. GitHub 저장소에 변경 사항을 푸시하면 배포된 앱도 업데이트됩니다. 자세한 내용은 [공식 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)를 참고하세요.

## 조작법

1. 아래에서 사용할 블록을 선택합니다.
2. 시작 행과 시작 열을 고릅니다. 선택한 위치는 블록의 왼쪽 위 기준점입니다.
3. 보드의 배치 미리보기를 확인한 뒤 **블록 배치**를 누릅니다.
4. 가로 또는 세로 한 줄이 모두 채워지면 해당 줄이 제거됩니다. 줄이 지워져도 다른 블록은 떨어지지 않습니다.
5. 남아 있는 블록을 어느 곳에도 놓을 수 없으면 게임이 종료됩니다.

## 점수 규칙

- 배치한 블록 칸마다 1점
- 제거한 가로·세로 줄마다 10점
- 한 번에 여러 줄 제거 시 추가 점수
- 연속으로 줄을 제거하면 콤보 보너스

최고 점수는 `.tile_ten_data.json` 파일에 로컬로 저장됩니다. 이 파일은 `.gitignore`에 포함되어 GitHub에 올라가지 않습니다. 호스팅 환경에서는 파일 저장이 초기화될 수 있으며, 현재 방식은 사용자별 온라인 랭킹을 제공하지 않습니다.

## 파일 구조

```text
tile-ten/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

UI는 Streamlit과 HTML/CSS로 구현했으며 외부 이미지나 별도의 게임 엔진은 필요하지 않습니다.
