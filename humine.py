#!/usr/bin/env python3
"""
Features:
- King safety analysis (threat detection)
- Capture evaluation and material counting
- Attack/Defense sequence calculation
- Full move sequence display for recommended moves
- Tactical considerations (sacrifices, piece captures)
"""

import chess
import chess.engine
import json
import random
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict


class ChessLearner:
    """
    Enhanced chess learning engine with tactical awareness and threat detection.
    """
    
    # Piece values for material evaluation
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0  # King is priceless
    }
    
    def __init__(self, stockfish_path: str = "stockfish", memory_file: str = "chess_memory.json", 
                 max_depth: int = 200):
        """
        Initialize the chess learner.
        
        Args:
            stockfish_path: Path to the Stockfish executable
            memory_file: Path to the JSON file for persistent memory
            max_depth: Maximum depth (moves) for game simulations
        """
        self.board = chess.Board()
        self.stockfish_path = stockfish_path
        self.memory_file = Path(memory_file)
        self.engine = None
        self.memory = self._load_memory()
        self.play_as_white = True
        self.max_depth = max_depth
        
        # Initialize Stockfish engine
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
            # Set a low skill level and time limit for faster games
            self.engine.configure({"Skill Level": 5})
        except Exception as e:
            print(f"Warning: Could not initialize Stockfish engine: {e}")
            print("Continuing without engine (testing mode)")
    
    def __del__(self):
        """Clean up the engine on deletion."""
        if self.engine:
            self.engine.quit()
    
    def _load_memory(self) -> Dict:
        """Load persistent memory from JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    print(f"✓ Loaded memory from {self.memory_file}")
                    print(f"  Positions in memory: {len(data)}")
                    return data
            except Exception as e:
                print(f"Warning: Could not load memory file: {e}")
                return {}
        else:
            print(f"No existing memory file found. Starting fresh.")
            return {}
    
    def _save_memory(self):
        """Save current memory state to JSON file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def _get_position_key(self) -> str:
        """Generate a unique key for the current board position."""
        fen_parts = self.board.fen().split(' ')
        position_fen = ' '.join(fen_parts[:4])
        color = "white" if self.play_as_white else "black"
        key = f"{position_fen}|playing_as_{color}"
        return key
    
    def set_position(self, fen: str, play_as_white: bool = True):
        """Set the board position for learning."""
        self.board.set_fen(fen)
        self.play_as_white = play_as_white
        position_key = self._get_position_key()
        
        print(f"\n{'='*70}")
        print(f"Position set: Playing as {'WHITE' if play_as_white else 'BLACK'}")
        print(f"FEN: {fen}")
        print(f"Position Key: {position_key}")
        
        if position_key in self.memory:
            print(f"Memory found: {len(self.memory[position_key])} moves previously tested")
        else:
            print("No previous memory for this position")
        
        print(f"{'='*70}\n")
        print(self.board)
        print()
    
    # ========================================================================
    # TACTICAL ANALYSIS METHODS
    # ========================================================================
    
    def get_material_count(self, board: chess.Board, color: chess.Color) -> int:
        """
        Calculate total material value for a given color.
        
        Args:
            board: Chess board to analyze
            color: Color to count material for (True=White, False=Black)
            
        Returns:
            Total material value in centipawns
        """
        total = 0
        for piece_type in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            pieces = board.pieces(piece_type, color)
            total += len(pieces) * self.PIECE_VALUES[piece_type]
        return total
    
    def get_material_balance(self, board: chess.Board) -> int:
        """
        Get material balance from our perspective.
        Positive = we're ahead, Negative = we're behind.
        """
        our_color = chess.WHITE if self.play_as_white else chess.BLACK
        opponent_color = not our_color
        
        our_material = self.get_material_count(board, our_color)
        opponent_material = self.get_material_count(board, opponent_color)
        
        return our_material - opponent_material
    
    def is_capture_move(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if a move captures a piece."""
        return board.is_capture(move)
    
    def get_captured_piece_value(self, board: chess.Board, move: chess.Move) -> int:
        """Get the value of the piece being captured."""
        if not board.is_capture(move):
            return 0
        
        captured_piece = board.piece_at(move.to_square)
        if captured_piece is None:
            # En passant capture
            return self.PIECE_VALUES[chess.PAWN]
        
        return self.PIECE_VALUES[captured_piece.piece_type]
    
    def is_king_in_check(self, board: chess.Board) -> bool:
        """Check if our king is in check."""
        return board.is_check()
    
    def detect_immediate_threats(self, board: chess.Board) -> List[Dict]:
        """
        Detect immediate threats to our king.
        
        Returns:
            List of threat dictionaries with attacking pieces and squares
        """
        our_color = chess.WHITE if self.play_as_white else chess.BLACK
        our_king_square = board.king(our_color)
        
        if our_king_square is None:
            return []
        
        threats = []
        
        # Check all opponent's pieces
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color != our_color:
                # Check if this piece attacks our king
                if our_king_square in board.attacks(square):
                    threats.append({
                        'piece': piece.piece_type,
                        'square': chess.square_name(square),
                        'target': chess.square_name(our_king_square)
                    })
        
        return threats
    
    def calculate_attack_sequences(self, board: chess.Board, depth: int = 3) -> List[Dict]:
        """
        Calculate possible attacking sequences.
        
        Args:
            board: Current board position
            depth: How many moves ahead to look
            
        Returns:
            List of attack sequence dictionaries
        """
        our_color = chess.WHITE if self.play_as_white else chess.BLACK
        sequences = []
        
        for move in board.legal_moves:
            test_board = board.copy()
            test_board.push(move)
            
            # Check if this leads to checkmate
            if test_board.is_checkmate():
                sequences.append({
                    'moves': [move],
                    'result': 'checkmate',
                    'depth': 1,
                    'material_gain': self.get_captured_piece_value(board, move)
                })
                continue
            
            # Check if this leads to check
            if test_board.is_check():
                sequences.append({
                    'moves': [move],
                    'result': 'check',
                    'depth': 1,
                    'material_gain': self.get_captured_piece_value(board, move)
                })
            
            # Check for material gain
            if self.is_capture_move(board, move):
                gain = self.get_captured_piece_value(board, move)
                if gain > 0:
                    sequences.append({
                        'moves': [move],
                        'result': 'capture',
                        'depth': 1,
                        'material_gain': gain
                    })
        
        # Sort by priority: checkmate > check > high-value captures
        def sequence_priority(seq):
            if seq['result'] == 'checkmate':
                return 10000
            elif seq['result'] == 'check':
                return 5000 + seq.get('material_gain', 0)
            else:
                return seq.get('material_gain', 0)
        
        sequences.sort(key=sequence_priority, reverse=True)
        return sequences
    
    def calculate_defense_sequences(self, board: chess.Board) -> List[Dict]:
        """
        Calculate defensive moves to protect the king.
        
        Returns:
            List of defensive sequence dictionaries with cost analysis
        """
        defenses = []
        
        for move in board.legal_moves:
            test_board = board.copy()
            test_board.push(move)
            
            # Calculate material cost
            piece_moved = board.piece_at(move.from_square)
            piece_value = self.PIECE_VALUES.get(piece_moved.piece_type, 0) if piece_moved else 0
            
            # Check if move removes check
            removes_check = not test_board.is_check() if board.is_check() else False
            
            # Check if king is safe after move
            threats_before = len(self.detect_immediate_threats(board))
            threats_after = len(self.detect_immediate_threats(test_board))
            
            material_lost = 0
            if test_board.is_capture(move):
                # If we're making a capture while defending, that's good
                material_lost = -self.get_captured_piece_value(board, move)
            
            # Check if we're hanging a piece
            if not test_board.is_game_over():
                # Simple check: is the piece we moved now undefended?
                if piece_moved and test_board.is_attacked_by(not board.turn, move.to_square):
                    if not test_board.is_attacked_by(board.turn, move.to_square):
                        material_lost += piece_value
            
            defenses.append({
                'move': move,
                'removes_check': removes_check,
                'threats_reduced': threats_before - threats_after,
                'material_cost': material_lost,
                'king_safer': threats_after < threats_before
            })
        
        # Sort by effectiveness: removes check > reduces threats > low material cost
        def defense_priority(d):
            score = 0
            if d['removes_check']:
                score += 10000
            score += d['threats_reduced'] * 1000
            score -= d['material_cost']
            return score
        
        defenses.sort(key=defense_priority, reverse=True)
        return defenses
    
    def analyze_position_before_move(self, board: chess.Board) -> Dict:
        """
        Comprehensive position analysis before making a move.
        
        Returns:
            Dictionary with king safety, attack opportunities, and recommended strategy
        """
        analysis = {
            'king_in_check': self.is_king_in_check(board),
            'immediate_threats': self.detect_immediate_threats(board),
            'material_balance': self.get_material_balance(board),
            'attack_sequences': self.calculate_attack_sequences(board),
            'defense_sequences': [],
            'recommended_strategy': None
        }
        
        # Analyze threats
        if analysis['king_in_check'] or len(analysis['immediate_threats']) > 0:
            print("\n⚠️  KING IN DANGER!")
            print(f"   Threats detected: {len(analysis['immediate_threats'])}")
            analysis['defense_sequences'] = self.calculate_defense_sequences(board)
            
            # Compare attack vs defense speed
            fastest_attack = analysis['attack_sequences'][0] if analysis['attack_sequences'] else None
            fastest_defense = analysis['defense_sequences'][0] if analysis['defense_sequences'] else None
            
            if fastest_attack and fastest_attack['result'] == 'checkmate':
                print("   ✓ WE CAN CHECKMATE FIRST!")
                analysis['recommended_strategy'] = 'attack'
            elif fastest_defense:
                print(f"   → Defending (best defense: {board.san(fastest_defense['move'])})")
                analysis['recommended_strategy'] = 'defend'
            else:
                print("   → No clear defense found, looking for counter-attack")
                analysis['recommended_strategy'] = 'counter_attack'
        
        else:
            # No immediate danger
            if analysis['attack_sequences']:
                best_attack = analysis['attack_sequences'][0]
                if best_attack['result'] == 'checkmate':
                    print("\n✓ CHECKMATE AVAILABLE!")
                    analysis['recommended_strategy'] = 'checkmate'
                elif best_attack['result'] == 'check':
                    print(f"\n→ Check available with material gain: {best_attack['material_gain']}")
                    analysis['recommended_strategy'] = 'attack'
                elif best_attack['material_gain'] >= 300:  # At least a minor piece
                    print(f"\n→ Good capture available: {best_attack['material_gain']} centipawns")
                    analysis['recommended_strategy'] = 'capture'
                else:
                    print("\n→ No immediate tactical opportunities")
                    analysis['recommended_strategy'] = 'positional'
            else:
                analysis['recommended_strategy'] = 'positional'
        
        return analysis
    
    # ========================================================================
    # ENHANCED SIMULATION WITH CAPTURE AWARENESS
    # ========================================================================
    
    def simulate_tactical_game(self, first_move: chess.Move) -> Tuple[str, int, Dict]:
        """
        Enhanced simulation that tracks captures and material.
        
        Returns:
            Tuple of (result, move_count, tactical_info)
        """
        sim_board = self.board.copy()
        sim_board.push(first_move)
        move_count = 1
        
        # Track tactical info
        tactical_info = {
            'captures_by_us': [],
            'captures_by_opponent': [],
            'material_balance_change': 0,
            'checks_given': 0,
            'checks_received': 0
        }
        
        # Initial material balance
        initial_balance = self.get_material_balance(sim_board)
        
        while not sim_board.is_game_over() and move_count < self.max_depth:
            is_learner_turn = (sim_board.turn == chess.WHITE) == self.play_as_white
            
            if is_learner_turn:
                # Learner plays - prefer captures when possible
                legal_moves = list(sim_board.legal_moves)
                if not legal_moves:
                    break
                
                # Separate captures from non-captures
                captures = [m for m in legal_moves if sim_board.is_capture(m)]
                
                if captures and random.random() < 0.3:  # 30% chance to prefer captures
                    move = random.choice(captures)
                    value = self.get_captured_piece_value(sim_board, move)
                    tactical_info['captures_by_us'].append({
                        'move': sim_board.san(move),
                        'value': value
                    })
                else:
                    move = random.choice(legal_moves)
                    if sim_board.is_capture(move):
                        value = self.get_captured_piece_value(sim_board, move)
                        tactical_info['captures_by_us'].append({
                            'move': sim_board.san(move),
                            'value': value
                        })
                
                sim_board.push(move)
                
                if sim_board.is_check():
                    tactical_info['checks_given'] += 1
            else:
                # Stockfish plays
                if self.engine:
                    try:
                        result = self.engine.play(sim_board, chess.engine.Limit(time=0.05))
                        move = result.move
                        
                        if sim_board.is_capture(move):
                            value = self.get_captured_piece_value(sim_board, move)
                            tactical_info['captures_by_opponent'].append({
                                'move': sim_board.san(move),
                                'value': value
                            })
                        
                        sim_board.push(move)
                        
                        if sim_board.is_check():
                            tactical_info['checks_received'] += 1
                    except:
                        legal_moves = list(sim_board.legal_moves)
                        if not legal_moves:
                            break
                        sim_board.push(random.choice(legal_moves))
                else:
                    # Testing mode
                    legal_moves = list(sim_board.legal_moves)
                    if not legal_moves:
                        break
                    sim_board.push(random.choice(legal_moves))
            
            move_count += 1
        
        # Final material balance
        final_balance = self.get_material_balance(sim_board)
        tactical_info['material_balance_change'] = final_balance - initial_balance
        
        # Determine result
        if sim_board.is_checkmate():
            winner_is_white = not sim_board.turn
            if winner_is_white == self.play_as_white:
                return "WIN", move_count, tactical_info
            else:
                return "LOSS", move_count, tactical_info
        elif sim_board.is_stalemate() or sim_board.is_insufficient_material() or \
             sim_board.is_fifty_moves() or sim_board.is_repetition():
            return "DRAW", move_count, tactical_info
        else:
            return "DRAW", move_count, tactical_info
    
    def record_move_result(self, move_uci: str, move_san: str, result: str, move_count: int, tactical_info: Dict = None):
        """Record move result with enhanced tactical information."""
        position_key = self._get_position_key()
        
        if position_key not in self.memory:
            self.memory[position_key] = {}
        
        if move_uci not in self.memory[position_key]:
            self.memory[position_key][move_uci] = {
                "san": move_san,
                "results": [],
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "min_moves_to_win": float('inf'),
                "min_moves_to_draw": float('inf'),
                "total_captures": 0,
                "total_material_gained": 0
            }
        
        move_data = self.memory[position_key][move_uci]
        
        # Record result with tactical info
        result_entry = {
            "result": result,
            "move_count": move_count,
            "timestamp": datetime.now().isoformat()
        }
        
        if tactical_info:
            result_entry["tactical_info"] = tactical_info
            move_data["total_captures"] += len(tactical_info.get('captures_by_us', []))
            move_data["total_material_gained"] += tactical_info.get('material_balance_change', 0)
        
        move_data["results"].append(result_entry)
        
        # Update statistics
        if result == "WIN":
            move_data["wins"] += 1
            move_data["min_moves_to_win"] = min(move_data["min_moves_to_win"], move_count)
        elif result == "DRAW":
            move_data["draws"] += 1
            move_data["min_moves_to_draw"] = min(move_data["min_moves_to_draw"], move_count)
        else:
            move_data["losses"] += 1
        
        self._save_memory()
    
    def get_move_score(self, move_data: Dict) -> float:
        """Enhanced scoring that considers captures and material."""
        wins = move_data["wins"]
        draws = move_data["draws"]
        losses = move_data["losses"]
        total = wins + draws + losses
        
        if total == 0:
            return 0
        
        base_score = 0
        
        # Prioritize wins
        if wins > 0:
            min_win_moves = move_data["min_moves_to_win"]
            speed_bonus = 1000 / min_win_moves if min_win_moves < float('inf') else 0
            base_score = 10000 + speed_bonus + (wins / total) * 500
        # Then draws
        elif draws > 0:
            min_draw_moves = move_data["min_moves_to_draw"]
            speed_bonus = 1000 / min_draw_moves if min_draw_moves < float('inf') else 0
            base_score = 5000 + speed_bonus + (draws / total) * 500
        # Losing moves
        else:
            loss_rate = losses / total
            base_score = 100 / (1 + loss_rate * 10)
        
        # Add tactical bonuses
        capture_bonus = move_data.get("total_captures", 0) * 10
        material_bonus = move_data.get("total_material_gained", 0) / 10
        
        return base_score + capture_bonus + material_bonus
    
    def get_best_move_from_memory(self) -> Optional[Tuple[str, str, Dict]]:
        """Get best move from memory with tactical considerations."""
        position_key = self._get_position_key()
        
        if position_key not in self.memory or not self.memory[position_key]:
            return None
        
        best_move = None
        best_score = -1
        
        for move_uci, move_data in self.memory[position_key].items():
            score = self.get_move_score(move_data)
            if score > best_score:
                best_score = score
                best_move = (move_uci, move_data["san"], move_data)
        
        return best_move
    
    def get_untried_moves(self) -> List[chess.Move]:
        """Get untried moves."""
        position_key = self._get_position_key()
        tried_moves = set()
        
        if position_key in self.memory:
            tried_moves = set(self.memory[position_key].keys())
        
        legal_moves = list(self.board.legal_moves)
        untried = [move for move in legal_moves if move.uci() not in tried_moves]
        
        return untried
    
    def should_retry_move(self, move_data: Dict) -> bool:
        """Determine if a move should be retried."""
        wins = move_data["wins"]
        draws = move_data["draws"]
        losses = move_data["losses"]
        total = wins + draws + losses
        
        if wins > 0 or draws > 0:
            return True
        
        if total < 3:
            return True
        
        return False
    
    def display_move_sequences(self, move_san: str, move_data: Dict):
        """
        Display all possible move sequences for the recommended move.
        Shows the variety of outcomes this move has produced.
        """
        print(f"\n{'='*70}")
        print(f"MOVE SEQUENCES FOR: {move_san}")
        print(f"{'='*70}")
        
        results = move_data.get("results", [])
        if not results:
            print("No sequence data available yet.")
            return
        
        # Group by result type
        wins = [r for r in results if r["result"] == "WIN"]
        draws = [r for r in results if r["result"] == "DRAW"]
        losses = [r for r in results if r["result"] == "LOSS"]
        
        # Show winning sequences
        if wins:
            print(f"\n✓ WINNING SEQUENCES ({len(wins)}):")
            print("-" * 70)
            for i, w in enumerate(wins[:5], 1):  # Show top 5
                tactical = w.get("tactical_info", {})
                captures = len(tactical.get("captures_by_us", []))
                material = tactical.get("material_balance_change", 0)
                print(f"  {i}. Win in {w['move_count']} moves | "
                      f"Captures: {captures} | Material: +{material}")
                
                if tactical.get("captures_by_us"):
                    cap_list = ", ".join([f"{c['move']}({c['value']})" 
                                         for c in tactical["captures_by_us"][:3]])
                    print(f"     Key captures: {cap_list}")
        
        # Show drawing sequences with captures
        if draws:
            print(f"\n→ DRAWING SEQUENCES ({len(draws)}):")
            print("-" * 70)
            # Sort draws by material gained
            draws_sorted = sorted(draws, 
                                 key=lambda x: x.get("tactical_info", {}).get("material_balance_change", 0),
                                 reverse=True)
            
            for i, d in enumerate(draws_sorted[:5], 1):
                tactical = d.get("tactical_info", {})
                captures = len(tactical.get("captures_by_us", []))
                material = tactical.get("material_balance_change", 0)
                print(f"  {i}. Draw in {d['move_count']} moves | "
                      f"Captures: {captures} | Material: {material:+d}")
                
                if tactical.get("captures_by_us"):
                    cap_list = ", ".join([f"{c['move']}({c['value']})" 
                                         for c in tactical["captures_by_us"][:3]])
                    print(f"     Captures: {cap_list}")
        
        # Show losing sequences (brief)
        if losses:
            print(f"\n✗ LOSING SEQUENCES ({len(losses)}):")
            print("-" * 70)
            avg_loss_moves = sum(l["move_count"] for l in losses) / len(losses)
            print(f"  Average loss in {avg_loss_moves:.1f} moves")
        
        print("=" * 70)
    
    def print_detailed_statistics(self):
        """Print detailed statistics for all moves tried."""
        position_key = self._get_position_key()
        
        if position_key not in self.memory or not self.memory[position_key]:
            print("\n" + "="*70)
            print("DETAILED STATISTICS")
            print("="*70)
            print("No moves have been tested yet for this position.")
            print("="*70)
            return
        
        moves_data = self.memory[position_key]
        
        total_moves_tested = len(moves_data)
        total_simulations = 0
        
        winning_moves = []
        drawing_moves = []
        losing_moves = []
        
        for move_uci, data in moves_data.items():
            wins = data["wins"]
            draws = data["draws"]
            losses = data["losses"]
            total_attempts = wins + draws + losses
            total_simulations += total_attempts
            
            move_san = data["san"]
            captures = data.get("total_captures", 0)
            material = data.get("total_material_gained", 0)
            
            if wins > 0:
                min_moves = data["min_moves_to_win"]
                winning_moves.append({
                    "san": move_san,
                    "wins": wins,
                    "total": total_attempts,
                    "min_moves": min_moves,
                    "win_rate": (wins / total_attempts * 100),
                    "captures": captures,
                    "material": material
                })
            
            if draws > 0:
                min_moves = data["min_moves_to_draw"]
                drawing_moves.append({
                    "san": move_san,
                    "draws": draws,
                    "total": total_attempts,
                    "min_moves": min_moves,
                    "draw_rate": (draws / total_attempts * 100),
                    "captures": captures,
                    "material": material
                })
            
            if losses > 0:
                losing_moves.append({
                    "san": move_san,
                    "losses": losses,
                    "total": total_attempts,
                    "loss_rate": (losses / total_attempts * 100)
                })
        
        winning_moves.sort(key=lambda x: (x["wins"], -x["min_moves"], x["material"]), reverse=True)
        # Sort draws by material gained
        drawing_moves.sort(key=lambda x: (x["material"], x["draws"]), reverse=True)
        losing_moves.sort(key=lambda x: x["loss_rate"], reverse=True)
        
        print("\n" + "="*70)
        print("DETAILED STATISTICS")
        print("="*70)
        print(f"Moves tested: {total_moves_tested}/{len(list(self.board.legal_moves))}")
        print(f"Total simulations run: {total_simulations}")
        print(f"Winning moves: {len(winning_moves)}/{total_moves_tested}")
        print(f"Drawing moves: {len(drawing_moves)}/{total_moves_tested}")
        print(f"Losing moves: {len(losing_moves)}/{total_moves_tested}")
        print("="*70)
        
        if winning_moves:
            print("\n" + "-"*70)
            print("WINNING MOVES:")
            print("-"*70)
            for i, move in enumerate(winning_moves, 1):
                print(f"{i}. Move: {move['san']:<6} | "
                      f"Wins: {move['wins']}/{move['total']} ({move['win_rate']:.1f}%) | "
                      f"Fastest: {move['min_moves']} moves | "
                      f"Captures: {move['captures']} | Material: {move['material']:+d}")
        
        if drawing_moves:
            print("\n" + "-"*70)
            print("DRAWING MOVES (sorted by material advantage):")
            print("-"*70)
            for i, move in enumerate(drawing_moves, 1):
                print(f"{i}. Move: {move['san']:<6} | "
                      f"Draws: {move['draws']}/{move['total']} ({move['draw_rate']:.1f}%) | "
                      f"Fastest: {move['min_moves']} moves | "
                      f"Captures: {move['captures']} | Material: {move['material']:+d}")
        
        if losing_moves:
            print("\n" + "-"*70)
            print("LOSING MOVES:")
            print("-"*70)
            for i, move in enumerate(losing_moves, 1):
                print(f"{i}. Move: {move['san']:<6} | "
                      f"Losses: {move['losses']}/{move['total']} ({move['loss_rate']:.1f}%)")
        
        print("="*70 + "\n")
    
    def find_winning_move(self, max_strength: int = 50) -> Optional[str]:
        """
        Enhanced move finding with tactical awareness.
        """
        print(f"\n{'='*70}")
        print("TACTICAL ANALYSIS & MOVE SEARCH")
        print(f"Max Strength: {max_strength} | Max Depth: {self.max_depth}")
        print(f"{'='*70}")
        
        # STEP 1: Analyze position for threats and opportunities
        print("\n📊 ANALYZING POSITION...")
        analysis = self.analyze_position_before_move(self.board)
        
        # STEP 2: Check memory for known good moves
        best_from_memory = self.get_best_move_from_memory()
        
        if best_from_memory:
            move_uci, move_san, move_data = best_from_memory
            
            # If we're in danger, only use memory if it's a winning move
            if analysis['recommended_strategy'] in ['defend', 'counter_attack']:
                if move_data["wins"] > 0:
                    print(f"\n✓ FOUND WINNING MOVE IN MEMORY (escapes danger): {move_san}")
                    self.display_move_sequences(move_san, move_data)
                    self.print_detailed_statistics()
                    return move_san
                else:
                    print(f"\n⚠️  Best memory move ({move_san}) doesn't guarantee win - searching for better...")
            
            # Not in danger - use best memory move if it's good
            elif move_data["wins"] > 0:
                print(f"\n✓ FOUND WINNING MOVE IN MEMORY: {move_san}")
                self.display_move_sequences(move_san, move_data)
                self.print_detailed_statistics()
                return move_san
            
            elif move_data["draws"] > 0:
                print(f"\n→ Found drawing move in memory: {move_san}")
                print(f"  Continuing search for winning moves...")
                best_draw = (move_san, move_data)
        else:
            best_draw = None
        
        # STEP 3: Search for moves
        print(f"\n🔍 SEARCHING FOR OPTIMAL MOVE...")
        
        attempts = 0
        position_key = self._get_position_key()
        
        # Prioritize moves based on strategy
        if analysis['recommended_strategy'] == 'defend':
            # Try defensive moves first
            print("→ Prioritizing defensive moves...")
            move_priority = analysis['defense_sequences']
            if move_priority:
                priority_moves = [d['move'] for d in move_priority[:5]]
            else:
                priority_moves = []
        elif analysis['recommended_strategy'] in ['attack', 'checkmate', 'capture']:
            # Try attacking moves first
            print("→ Prioritizing attacking moves...")
            attack_seqs = analysis['attack_sequences']
            if attack_seqs:
                priority_moves = [s['moves'][0] for s in attack_seqs[:5]]
            else:
                priority_moves = []
        else:
            priority_moves = []
        
        while attempts < max_strength:
            attempts += 1
            
            # Get untried moves
            untried = self.get_untried_moves()
            
            # Choose move
            if priority_moves and untried:
                # Try priority moves first if they're untried
                priority_untried = [m for m in priority_moves if m in untried]
                if priority_untried:
                    move = priority_untried[0]
                    priority_moves.remove(move)
                    move_source = "PRIORITY"
                else:
                    move = random.choice(untried)
                    move_source = "UNTRIED"
            elif untried:
                move = random.choice(untried)
                move_source = "UNTRIED"
            else:
                # Retry based on memory
                if position_key in self.memory:
                    retry_candidates = [
                        (move_uci, data) 
                        for move_uci, data in self.memory[position_key].items()
                        if self.should_retry_move(data)
                    ]
                    
                    if retry_candidates:
                        retry_candidates.sort(key=lambda x: self.get_move_score(x[1]), reverse=True)
                        move_uci, _ = retry_candidates[0]
                        move = chess.Move.from_uci(move_uci)
                        move_source = "RETRY"
                    else:
                        print(f"\n✗ No more moves worth trying after {attempts-1} attempts.")
                        break
                else:
                    print(f"\n✗ No legal moves available.")
                    break
            
            move_uci = move.uci()
            move_san = self.board.san(move)
            
            # Show move being tested
            memory_info = ""
            is_capture = "📦 CAPTURE" if self.is_capture_move(self.board, move) else ""
            
            if position_key in self.memory and move_uci in self.memory[position_key]:
                md = self.memory[position_key][move_uci]
                memory_info = f" [History: W:{md['wins']} D:{md['draws']} L:{md['losses']}]"
            
            print(f"\nAttempt {attempts}/{max_strength}: {move_san} ({move_source}) {is_capture}{memory_info}")
            
            # Simulate game
            result, move_count, tactical_info = self.simulate_tactical_game(move)
            
            # Record result
            self.record_move_result(move_uci, move_san, result, move_count, tactical_info)
            
            # Show result
            mat_change = tactical_info.get('material_balance_change', 0)
            captures = len(tactical_info.get('captures_by_us', []))
            print(f"  Result: {result} in {move_count} moves | "
                  f"Captures: {captures} | Material: {mat_change:+d}")
            
            # Check for win
            if result == "WIN":
                print(f"\n{'='*70}")
                print(f"✓ SUCCESS! FOUND WINNING MOVE: {move_san}")
                print(f"{'='*70}")
                print(f"Result: WIN in {move_count} moves")
                
                move_data = self.memory[position_key][move_uci]
                self.display_move_sequences(move_san, move_data)
                self.print_detailed_statistics()
                return move_san
            
            # Track best draw (prefer draws with material gain)
            if result == "DRAW":
                if not best_draw:
                    best_draw = (move_san, self.memory[position_key][move_uci])
                    print(f"  → New best draw: {move_san} (Material: {mat_change:+d})")
                else:
                    current_data = self.memory[position_key][move_uci]
                    current_material = current_data.get("total_material_gained", 0)
                    best_material = best_draw[1].get("total_material_gained", 0)
                    
                    if current_material > best_material:
                        best_draw = (move_san, current_data)
                        print(f"  → New best draw: {move_san} (Better material: {current_material:+d})")
        
        # Return best result found
        if best_draw:
            move_san, move_data = best_draw
            print(f"\n{'='*70}")
            print(f"✓ BEST MOVE FOUND: {move_san} (DRAW)")
            print(f"{'='*70}")
            print(f"Result: DRAW | Material advantage: {move_data.get('total_material_gained', 0):+d}")
            self.display_move_sequences(move_san, move_data)
            self.print_detailed_statistics()
            return move_san
        
        print(f"\n{'='*70}")
        print(f"✗ NO WINNING OR DRAWING MOVE FOUND")
        print(f"{'='*70}")
        self.print_detailed_statistics()
        return None


def main():
    """Main function with command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Enhanced Chess Learning Engine with Tactical Awareness',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--pos', type=str, default=None,
                       help='Chess position in FEN notation or "start"')
    parser.add_argument('--as', dest='play_as', type=str,
                       choices=['w', 'b', 'white', 'black'], default='w',
                       help='Play as white or black')
    parser.add_argument('--depth', type=int, default=200,
                       help='Maximum depth for simulations')
    parser.add_argument('--strength', type=int, default=50,
                       help='Maximum thinking iterations')
    parser.add_argument('--stockfish', type=str, default='stockfish',
                       help='Path to Stockfish executable')
    parser.add_argument('--memory', type=str, default='chess_memory.json',
                       help='Memory file path')
    
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         Enhanced Chess Learning Engine v3.0                      ║
║   With Tactical Awareness & Threat Detection                     ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    play_as_white = args.play_as.lower() in ['w', 'white']
    
    learner = ChessLearner(
        stockfish_path=args.stockfish,
        memory_file=args.memory,
        max_depth=args.depth
    )
    
    if args.pos:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" if args.pos.lower() == "start" else args.pos
        
        print(f"\nConfiguration:")
        print(f"  Position: {fen}")
        print(f"  Play as: {'WHITE' if play_as_white else 'BLACK'}")
        print(f"  Strength: {args.strength} iterations")
        print(f"  Depth: {args.depth} moves")
        
        try:
            learner.set_position(fen, play_as_white=play_as_white)
        except Exception as e:
            print(f"✗ Error: {e}")
            return
        
        best_move = learner.find_winning_move(max_strength=args.strength)
        
        if best_move:
            print(f"\n{'='*70}")
            print(f"🎯 FINAL RECOMMENDATION: {best_move}")
            print(f"{'='*70}\n")
    else:
        print("No position specified. Use --pos to specify a position.")
        print('Example: python chess_learner_enhanced.py --pos "start" --strength 30')


if __name__ == "__main__":
    main()
