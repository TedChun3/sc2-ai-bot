# SC2 AI Bot

StarCraft II AI bot project built on [BurnySc2](https://github.com/BurnySc2/python-sc2).

이 저장소에서 가장 실용적인 사용 방식은 2가지입니다.

- 호스트 1명이 SC2를 실행하고, 친구 1명이 `bot.py`를 업로드해서 실시간 1:1 하기
- 같은 PC에서 `bot.py` 두 개를 바로 붙여서 로컬 1:1 하기

중요한 제한:

- 업로드 대전은 `1:1`만 지원합니다.
- `AcropolisLE`는 2인용 맵입니다.
- 업로드되는 파일은 기본적으로 `bot.py` 1개입니다. 즉 친구 `bot.py`는 가능하면 단일 파일이어야 합니다.

## Requirements

호스트 PC:

- StarCraft II 설치
- Python 3.12 권장
- `pip install -r requirements.txt`
- `AcropolisLE` 맵 사용 가능 상태

친구 PC:

- Python 3.10+
- 저장소 클론
- 업로드할 `bot.py`

친구 PC에는 다음이 필요 없습니다.

- StarCraft II
- `pip install -r requirements.txt`
- 맵 설치

## Setup

### macOS

```bash
brew install python@3.12
python3.12 --version
python3.12 -m pip install -r requirements.txt

# Recent yarl versions can break port parsing on macOS
python3.12 -m pip install "aiohttp>=3.11.10" "yarl<1.18" --break-system-packages

export SC2PATH="/Applications/StarCraft II"
```

### Linux

```bash
sudo apt install python3.12 python3.12-pip
python3.12 -m pip install -r requirements.txt
export SC2PATH="$HOME/StarCraftII"
```

### Download Ladder Maps (Optional)

기본 맵은 SC2에 포함되어 있지만, 래더 맵이 더 필요하면:

```bash
cd "/Applications/StarCraft II/Maps"    # macOS
# cd "$HOME/StarCraftII/Maps"           # Linux

curl -LO https://github.com/BurnySc2/python-sc2/releases/download/maps/maps.zip
unzip maps.zip
rm maps.zip
```

또는:

```bash
python3.12 download_maps.py
```

## Host vs Friend Quick Start

### 1. 호스트가 저장소 준비

```bash
git clone <repo-url>
cd sc2-ai-bot
python3.12 -m pip install -r requirements.txt
```

### 2. 호스트가 방 열기

이 명령을 실행하면 호스트 PC에서 보이는 SC2 창 2개로 실시간 1:1 경기가 열립니다.

```bash
python3.12 strategy_room.py server --map AcropolisLE
```

출력 예시:

```json
{
  "join_url": "http://127.0.0.1:8765/join",
  "join_urls": [
    "http://127.0.0.1:8765/join",
    "http://192.168.0.10:8765/join"
  ]
}
```

친구에게는 `join_urls` 안의 LAN 주소를 주면 됩니다. 예: `192.168.0.10:8765`

### 3. 호스트도 자기 봇 등록

호스트도 참가자이므로 자기 `bot.py`를 한 번 등록해야 합니다.

```bash
python3.12 join_client.py \
  --server 127.0.0.1:8765 \
  --name hostbot \
  --race protoss \
  --bot-file bot.py
```

### 4. 친구가 저장소 클론 후 봇 업로드

친구 PC는 SC2가 없어도 됩니다. `join_client.py`는 표준 라이브러리만 써서 업로드만 합니다.

```bash
git clone <repo-url>
cd sc2-ai-bot
python3 join_client.py \
  --server <호스트IP>:8765 \
  --name friendbot \
  --race protoss \
  --bot-file bot.py
```

예:

```bash
python3 join_client.py \
  --server 192.168.0.10:8765 \
  --name friendbot \
  --race protoss \
  --bot-file bot.py
```

두 명이 모두 등록되면 경기가 자동으로 시작됩니다.

### 5. 상태 확인

호스트는 아래 명령으로 현재 방 상태와 경기 결과를 확인할 수 있습니다.

```bash
python3.12 strategy_room.py status --server 127.0.0.1:8765
```

## Friend Setup Notes

친구 `bot.py`가 다른 로컬 파일을 import하면 그 파일은 서버로 같이 안 올라갑니다. 현재 업로드 방식은 `bot.py` 단일 파일 기준입니다.

가장 안전한 구조는:

- `bot.py` 한 파일 안에 전략 로직이 모두 들어있음
- 표준 라이브러리 또는 호스트에 이미 설치된 라이브러리만 사용

## Local 1v1 On One PC

업로드 없이 같은 PC에서 `bot.py` 두 개를 바로 붙이고 싶으면:

```bash
python3.12 local_duel.py \
  --bot1-file bot.py \
  --bot2-file bot.py \
  --bot1-name player1 \
  --bot2-name player2 \
  --map AcropolisLE
```

이 경로는 원래 `bot.py` 단독 실행과 같은 `run_game(...)` 방식이라 macOS에서 보이는 경기 실행에 가장 잘 맞습니다.

## Single Bot Test

봇 하나를 컴퓨터 상대로 테스트할 때:

```bash
python3.12 bot.py
python3.12 bot.py --realtime
python3.12 bot.py --map AcropolisLE
python3.12 bot.py --difficulty hard
python3.12 bot.py --race zerg
python3.12 bot.py --save-replay
```

## Ladder / External Runner

래더 스타일 엔트리포인트가 필요하면:

```bash
python3.12 run.py
```

`run.py`는 `--LadderServer`, `--GamePort`, `--StartPort` 같은 인자를 받아 외부 매니저와 연결할 수 있습니다.

## Visible vs Headless

`strategy_room.py server` 기본값:

- visible
- realtime
- 2 players

즉, 별도 옵션 없이 바로 사람이 보는 경기로 뜹니다.

필요하면 아래 옵션을 사용할 수 있습니다.

- `--headless`: 창 없이 실행
- `--step-mode`: 실시간 대신 일반 step 모드

예:

```bash
python3.12 strategy_room.py server --map AcropolisLE --headless --step-mode
```

## Troubleshooting

### macOS: `ws://127.0.0.1:None/sc2api` error

최근 `yarl` 버전 문제일 수 있습니다.

```bash
python3.12 -m pip install "aiohttp>=3.11.10" "yarl<1.18" --break-system-packages
```

### macOS: SC2 crashes when launched via SSH/Termius

SC2는 가능하면 `Terminal.app`에서 직접 실행하세요. macOS 보안(TCC) 때문에 SSH 클라이언트/원격 터미널에서 GUI 권한이 꼬일 수 있습니다.

### Map not found

```bash
ls "/Applications/StarCraft II/Maps/"

cd "/Applications/StarCraft II/Maps"
curl -LO https://github.com/BurnySc2/python-sc2/releases/download/maps/maps.zip
unzip maps.zip && rm maps.zip
```

### Rosetta errors on Apple Silicon

```bash
sudo rm -rf /var/db/oah
# reboot
```

## Bot Summary

### `bot.py`

- 프로토스 운영형 봇
- 4인 시작 위치 정찰 대응
- Blink / Immortal / Colossus 운영

### `strategy_room.py`

- 호스트가 `bot.py` 업로드 방을 열 수 있음
- 1:1 업로드 대전 전용
- visible 모드에서는 호스트 PC에서 보이는 실시간 경기로 실행

### `join_client.py`

- 친구가 `bot.py`만 업로드하는 경량 클라이언트
- BurnySc2 설치 없이 사용 가능

### `local_duel.py`

- 로컬 파일 2개를 직접 1:1로 실행
- 빠르게 미러전/테스트할 때 가장 단순함

### `run.py`

- 래더/외부 매니저용 엔트리포인트

## Project Structure

```text
bot.py
join_client.py
ladder.py
local_duel.py
run.py
strategy_loader.py
strategy_room.py
uploaded_bot_runner.py
requirements.txt
README.md
```
