# Humine Chess Learning Engine v3.0

An intelligent chess analysis engine that combines reinforcement learning with tactical awareness to find optimal moves through simulation-based learning.

## Overview

Humine is a Python-based chess engine that learns from experience. Unlike traditional engines that rely solely on evaluation functions, Humine plays out thousands of simulated games against Stockfish, remembers what works, and improves its recommendations over time through persistent memory storage.

## Key Features

### 🧠 Reinforcement Learning Core
- **Experience-Based Learning**: Learns from simulated game outcomes rather than static evaluation
- **Persistent Memory**: Stores move results in JSON format for continuous improvement across sessions
- **Adaptive Scoring**: Prioritizes moves based on win rates, speed of victory, and material gains

### ⚔️ Tactical Awareness
- **King Safety Analysis**: Detects immediate threats to the king and calculates defensive responses
- **Attack/Defense Sequences**: Evaluates forcing moves like checks, captures, and checkmates
- **Material Tracking**: Monitors material balance changes throughout simulations
- **Threat Detection**: Identifies which opponent pieces are attacking your king

### 🎯 Smart Move Selection
- **Strategy-Based Prioritization**: Automatically prioritizes defensive moves when in danger, attacking moves when safe
- **Capture Evaluation**: Recognizes and prioritizes profitable captures
- **Checkmate Detection**: Immediately identifies and plays checkmate-in-one opportunities
- **Draw Optimization**: When winning isn't possible, seeks draws with material advantage

### 📊 Comprehensive Analytics
- **Detailed Statistics**: Win/draw/loss rates, fastest wins, material gains
- **Move Sequence Display**: Shows the variety of game outcomes each move produces
- **Tactical Reporting**: Tracks captures, checks given/received, and material changes
- **Simulation Tracking**: Records every simulated game for analysis

## How It Works

### 1. Position Analysis
When given a position, Humine first analyzes:
- Is the king in check?
- What threats exist?
- What's the material balance?
- Are there immediate tactical opportunities (checks, captures, checkmates)?

### 2. Memory Consultation
Checks if this exact position has been seen before:
- If a winning move is known → plays it immediately
- If drawing moves exist → uses them as fallback
- Otherwise → proceeds to exploration

### 3. Simulation Phase
Plays out multiple games against Stockfish:
- Tests untried moves first
- Prioritizes moves based on current tactical needs
- Tracks not just results but *how* games were won (captures, material gains)
- Uses Stockfish (skill level 5) as opponent for realistic resistance

### 4. Learning & Storage
Records detailed results:
- Win/Draw/Loss outcomes
- Number of moves to victory
- Material gained or lost
- Captures made during the game
- Tactical patterns (checks, threats)

### 5. Recommendation
Returns the best move found with full statistical backing and move sequence analysis.

## Installation

### Prerequisites
- Python 3.7+
- `python-chess` library
- Stockfish chess engine

### Setup

```bash
# Install dependencies
pip install python-chess

# Install Stockfish
# macOS: brew install stockfish
# Ubuntu: sudo apt-get install stockfish
# Windows: Download from https://stockfishchess.org/download/

# Clone or download humine.py
```

## Usage

### Basic Usage

```bash
# Analyze starting position as White
python humine.py --pos "start" --strength 50

# Analyze specific FEN position as Black
python humine.py --pos "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4" --as black

# Quick analysis (30 iterations)
python humine.py --pos "start" --strength 30

# Deep analysis (200 iterations, 300 max moves)
python humine.py --pos "start" --strength 200 --depth 300
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--pos` | FEN string or "start" for initial position | None (required) |
| `--as` | Play as "white"/"w" or "black"/"b" | white |
| `--strength` | Maximum simulation iterations | 50 |
| `--depth` | Maximum moves per simulation | 200 |
| `--stockfish` | Path to Stockfish executable | "stockfish" |
| `--memory` | Path to memory JSON file | "chess_memory.json" |

### Example Output

```
╔══════════════════════════════════════════════════════════════════╗
║         Enhanced Chess Learning Engine v3.0                      ║
║   With Tactical Awareness & Threat Detection                     ║
╚══════════════════════════════════════════════════════════════════╝

📊 ANALYZING POSITION...
→ No immediate tactical opportunities

🔍 SEARCHING FOR OPTIMAL MOVE...

Attempt 1/50: e2e4 (UNTRIED) 
  Result: WIN in 45 moves | Captures: 3 | Material: +400

✓ SUCCESS! FOUND WINNING MOVE: e4
```

## How It Helps Chess Players

### For Beginners
- **Learn Winning Patterns**: See which moves lead to victories in your favorite openings
- **Understand Threats**: Visual detection shows when your king is in danger
- **Material Awareness**: Tracks captures and material balance automatically

### For Intermediate Players
- **Tactical Training**: Identifies checks, captures, and threats in any position
- **Opening Preparation**: Build a memory database of favorable lines in your repertoire
- **Defense Practice**: Calculates defensive sequences when under attack

### For Advanced Players
- **Position Analysis**: Deep simulation reveals hidden resources in complex positions
- **Novelty Detection**: Finds untested moves that may surprise opponents
- **Endgame Technique**: Learns precise winning methods through repetition

### For Engine Developers
- **Reinforcement Learning Example**: Clean implementation of experience-based move selection
- **Modular Design**: Easy to extend with new tactical features or evaluation criteria
- **Simulation Framework**: Reusable game-playing infrastructure for experiments

## Technical Architecture

### Core Classes

**`ChessLearner`**: Main engine class
- `analyze_position_before_move()`: Tactical analysis
- `simulate_tactical_game()`: Self-play simulation
- `find_winning_move()`: Main search algorithm
- `record_move_result()`: Learning/memory update

### Data Structures

**Memory Format (JSON)**:
```json
{
  "position_fen|playing_as_white": {
    "e2e4": {
      "san": "e4",
      "wins": 15,
      "draws": 3,
      "losses": 2,
      "min_moves_to_win": 12,
      "total_captures": 45,
      "results": [...]
    }
  }
}
```

### Scoring Algorithm

Moves are scored by:
1. **Win Bonus**: +10,000 base (plus speed bonus: 1000/min_moves)
2. **Draw Bonus**: +5,000 base (plus speed bonus)
3. **Tactical Bonus**: +10 per capture, +material_gained/10
4. **Loss Penalty**: Reduced score based on loss rate

## Advanced Features

### Threat-Aware Search
When in check or under attack:
- Prioritizes defensive moves that remove check
- Evaluates material cost of defenses
- Considers counter-attacks if defense fails

### Capture Preference
During simulations:
- 30% chance to prefer capturing moves when available
- Tracks capture values to learn profitable exchanges
- Avoids losing material unnecessarily

### Persistent Learning
- Memory saved to JSON after every simulation
- Accumulates knowledge across multiple runs
- Position-specific learning (same FEN, different "play as" color = different entries)

## Limitations & Notes

- **Speed**: Simulation-based learning is slower than traditional evaluation (seconds to minutes depending on strength)
- **Opponent Model**: Currently uses Stockfish level 5; stronger opponents may require more iterations
- **Memory Growth**: JSON file grows with each new position; manual cleanup may be needed for long-term use
- **No Opening Book**: Relies entirely on learned experience rather than theoretical knowledge

## Future Enhancements

Potential improvements for contributors:
- Parallel simulation processing
- Neural network value function
- UCI protocol compatibility
- Web interface for interactive analysis
- Opening book integration
- Endgame tablebase support

## License

Open source - modify and extend as needed for your chess projects.

---

**Humine**: *Learning chess one simulation at a time.*
