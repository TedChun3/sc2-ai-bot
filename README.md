# SC2 AI Bot 🎮

StarCraft II AI Bot using [BurnySc2](https://github.com/BurnySc2/python-sc2) (python-sc2 fork).

## Requirements

- **StarCraft II** (Free Starter Edition works)
- **Python 3.10+**
- **Maps** downloaded to SC2 Maps folder

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# macOS - set SC2 path (default)
export SC2PATH="/Applications/StarCraft II"

# Linux
export SC2PATH="$HOME/StarCraftII"

# (Optional) Download extra ladder maps - basic maps are included with SC2
# python download_maps.py
```

## Run

```bash
# Basic bot vs Computer (Easy)
python bot.py

# Change difficulty
python bot.py --difficulty hard

# Change race
python bot.py --race zerg

# Watch replay after game
python bot.py --save-replay
```

## Bot Strategies

### `bot.py` - Protoss Timing Attack
- 2-Gate Zealot rush → Stalker transition
- Auto worker management
- Basic army micro (focus fire, retreat)

### `zerg_bot.py` - Zerg Macro
- Hatchery-first expand
- Zergling/Roach composition
- Inject larvae macro

### `terran_bot.py` - Terran Bio
- Reaper opening → Marine/Marauder
- Stim timing push
- Medivac pickup micro

## Project Structure

```
├── bot.py              # Protoss bot (main)
├── zerg_bot.py         # Zerg bot
├── terran_bot.py       # Terran bot
├── download_maps.py    # Map downloader
├── requirements.txt    # Dependencies
└── README.md
```

## Adding LLM Strategy (TODO)

Future: Use Claude/GPT to make strategic decisions based on game state.

```python
# Concept
game_state = observe_game()
strategy = llm.decide(game_state)  # "expand" / "attack" / "defend"
execute(strategy)
```
