"""
    pystockfish
    ~~~~~~~~~~~~~~~

    Wraps the Stockfish chess engine.  Assumes stockfish is
    executable at the root level.

    Built on Ubuntu 12.1 tested with Stockfish 120212.
    
    :copyright: (c) 2013 by Jarret Petrillo.
    :license: GNU General Public License, see LICENSE for more details.
"""

from __future__ import print_function

import subprocess, re
from random import randint

class Match:
    '''
    The Match class setups a chess match between two specified engines.  The white player
    is randomly chosen.

    deep_engine = Engine(depth=20)
    shallow_engine = Engine(depth=10)
    engines = {
        'shallow': shallow_engine,
        'deep': deep_engine,
        }

    m = Match(engines=engines)

    m.move() advances the game by one move.
    
    m.run() plays the game until completion or 200 moves have been played,
    returning the winning engine name.
    '''
    def __init__(self, engines):
        random_bin = randint(0,1)
        self.white = engines.keys()[random_bin]
        self.black = engines.keys()[not random_bin]
        self.white_engine = engines.get(self.white)
        self.black_engine = engines.get(self.black)
        self.moves = []
        self.white_engine.newgame()
        self.black_engine.newgame()
        self.winner = None
        self.winner_name = None

    def move(self):
        if len(self.moves)>200:
            return False
        elif len(self.moves) % 2:
            active_engine = self.black_engine
            active_engine_name = self.black
            inactive_engine = self.white_engine
            inactive_engine_name = self.white
        else:
            active_engine = self.white_engine
            active_engine_name = self.white
            inactive_engine = self.black_engine
            inactive_engine_name = self.black
        active_engine.setposition(self.moves)
        movedict=active_engine.bestmove()
        bestmove = movedict.get('move')
        info = movedict.get('info')
        ponder = movedict.get('ponder')
        self.moves.append(bestmove)
        
        if ponder != '(none)': return True
        else:
            mateloc = info.find('mate')
            if mateloc>=0:
                matenum = int(info[mateloc+5])
                if matenum>0:
                    self.winner_engine = active_engine
                    self.winner=active_engine_name
                elif matenum<0: 
                    self.winner_engine=inactive_engine
                    self.winner=inactive_engine_name
            return False

    def run(self):
        '''
        Returns the winning chess engine or "None" if there is a draw.
        '''
        while self.move(): pass
        return self.winner

class Engine(subprocess.Popen):
    '''
    This initiates the Stockfish chess engine with Ponder set to False.
    'param' allows parameters to be specified by a dictionary object with 'Name' and 'value'
    with value as an integer.

    i.e. the following explicitely sets the default parameters
    {
        "Contempt Factor": 0,
        "Min Split Depth": 0,
        "Threads": 1,
        "Hash": 16,
        "MultiPV": 1,
        "Skill Level": 20,
        "Move Overhead": 30,
        "Minimum Thinking Time": 20,
        "Slow Mover": 80,
    }

    If 'rand' is set to False, any options not explicitely set will be set to the default 
    value.

    -----
    USING RANDOM PARAMETERS
    -----
    If you set 'rand' to True, the 'Contempt' parameter will be set to a random value between
    'rand_min' and 'rand_max' so that you may run automated matches against slightly different
    engines.
    '''
    def __init__(self, depth=2, ponder=False, param={}, rand=False, rand_min=-10, rand_max=10):
        subprocess.Popen.__init__(self, 
            'stockfish',
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,)
        self.depth = str(depth)
        self.ponder = ponder
        self.put('uci')
        if not ponder:
            self.setoption('Ponder', False)

        base_param = {
        "Write Debug Log": "false",
        "Contempt Factor": 0, # There are some stockfish versions with Contempt Factor
        "Contempt": 0,        # and others with Contempt. Just try both.
        "Min Split Depth": 0,
        "Threads": 1,
        "Hash": 16,
        "MultiPV": 1,
        "Skill Level": 20,
        "Move Overhead": 30,
        "Minimum Thinking Time": 20,
        "Slow Mover": 80,
        "UCI_Chess960": "false",
        }

        if rand:
            base_param['Contempt'] = randint(rand_min, rand_max),
            base_param['Contempt Factor'] = randint(rand_min, rand_max),

        base_param.update(param)
        self.param = base_param
        for name,value in base_param.items():
            self.setoption(name,value)

    def newgame(self):
        '''
        Calls 'ucinewgame' - this should be run before a new game
        '''
        self.put('ucinewgame')
        self.isready()

    def put(self, command):
        self.stdin.write(command+'\n')
        self.stdin.flush()

    def flush(self):
        self.stdout.flush()

    def setoption(self,optionname, value):
        self.put('setoption name %s value %s'%(optionname,str(value)))
        stdout = self.isready()
        if stdout.find('No such')>=0:
            print("stockfish was unable to set option %s"%optionname)

    def setposition(self, moves=[]):
        '''
        Move list is a list of moves (i.e. ['e2e4', 'e7e5', ...]) each entry as a string.  Moves must be in full algebraic notation.
        '''
        self.put('position startpos moves %s'%self._movelisttostr(moves))
        self.isready()

    def setfenposition(self, fen):
        '''
        set position in fen notation.  Input is a FEN string i.e. "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        '''
        self.put('position fen %s' % fen)
        self.isready()

    def go(self):
        self.put('go depth %s'%self.depth)

    def go_nodes(self, num_nodes):
        self.put('go nodes %i' % num_nodes)

    def _movelisttostr(self,moves):
        '''
        Concatenates a list of strings
        '''
        movestr = ''
        for h in moves:
            movestr += h + ' '
        return movestr.strip()

    def bestmove(self):
        last_line = ""
        self.go()
        while True:
            text = self.stdout.readline().strip()
            split_text = text.split(' ')
            if split_text[0]=='bestmove':
                return {'move': split_text[1],
                        'ponder': split_text[3],
                        'info': last_line
                        }
            last_line = text

    def parse_info(self, info):
        '''
        Given an info string, returns [depth, seldepth, score, nodes, bestmoves, pv_num, comptime]

        score is from the perspective of the player making the move.
        where mate-in-1 is equity 2^15 - 1 for white and 1 - 2^15 for black,
        mate-in-2 is equity 2^15 - 2 or 2 - 2^15.

        bestmoves is the list of the engine-expected moves in UCI notation.

        pv_num is the rank number of the player-move being analyzed, 1 being the best player
        move, 2 the 2nd best, and so on.

        comptime is how many milliseconds had been spent on computation up to that point.
        '''
        multiplier = 1

        the_match = re.search('info depth ([0-9]+) seldepth ([0-9]+) multipv ([0-9]) score (cp|mate) ([-0-9]+) nodes ([0-9]+) .* time ([0-9]+) pv ([a-z0-9 ]+)$', info)
        if the_match:
            groups = the_match.groups()
            depth = int(groups[0])
            seldepth = int(groups[1])
            multipv = int(groups[2])
            score = int(groups[4])
            if groups[3] == 'mate':
                mate_count = score
                if score > 0:
                    score = 32768 - mate_count
                else:
                    score = mate_count - 32768
            nodes = int(groups[5])
            comptime = int(groups[6])
            bestmoves = groups[7]
            
            return {'depth':depth,
                    'seldepth':seldepth,
                    'score':score,
                    'nodes':nodes,
                    'bestmoves':bestmoves,
                    'multipv':multipv,
                    'comptime':comptime}
        else:
            # not a standard info line, ignore it
            return None
            
    def go_infos(self):
        '''returns the best move, the ponder move, and a list
        of parsed engine 'info' from each search depth'''
        infos = []
        self.go()
        
        while True:
            text = self.stdout.readline().strip()
            split_text = text.split(' ')
            if split_text[0]=='bestmove':
                ponder = split_text[3] if len(split_text) >= 3 else None
                return {'move': split_text[1],
                        'ponder': ponder,
                        'infos': infos
                }
            if 'score' in text:
                info = self.parse_info(text)
                if info:
                    infos.append(info)

    def capture_fulltext(self):
        '''returns the full text result of an evaluation. call this function after you've told the engine to go.'''
        result = []

        while True:
            text = self.stdout.readline().strip()
            result.append(text)
            split_text = text.split(' ')
            if split_text[0]=='bestmove':
                return result
            
    def isready(self):
        '''
        Used to synchronize the python engine object with the back-end engine.  Sends 'isready' and waits for 'readyok.'
        '''
        self.put('isready')
        lastline = ''
        while True:
            text = self.stdout.readline().strip()
            if text == 'readyok':
                return lastline
            lastline = text

