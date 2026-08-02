import os
import random
import string
import time
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template_string, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kahoot-secret-key-2024')
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')

# ─── Quiz Data ────────────────────────────────────────────────────────────────

QUIZ_DATA = {
    "MTK Easy": [
        {"q": "Berapa hasil dari 15 × 8?", "opts": ["100", "120", "130", "110"], "ans": 1},
        {"q": "Jika x + 7 = 15, berapa nilai x?", "opts": ["6", "7", "8", "9"], "ans": 2},
        {"q": "Berapa luas persegi dengan sisi 9 cm?", "opts": ["72 cm²", "81 cm²", "90 cm²", "63 cm²"], "ans": 1},
        {"q": "Berapa hasil dari 144 ÷ 12?", "opts": ["10", "11", "12", "13"], "ans": 2},
        {"q": "Berapa nilai dari 2³ + 3²?", "opts": ["15", "16", "17", "18"], "ans": 2},
        {"q": "Keliling lingkaran dengan jari-jari 7 cm adalah... (π = 22/7)", "opts": ["42 cm", "44 cm", "46 cm", "48 cm"], "ans": 1},
        {"q": "Berapa hasil dari 25% × 200?", "opts": ["40", "45", "50", "55"], "ans": 2},
        {"q": "Jika 3y = 27, berapa nilai y?", "opts": ["7", "8", "9", "10"], "ans": 2},
        {"q": "Berapa volume kubus dengan sisi 4 cm?", "opts": ["48 cm³", "56 cm³", "64 cm³", "72 cm³"], "ans": 2},
        {"q": "Berapa hasil dari √169?", "opts": ["11", "12", "13", "14"], "ans": 2},
    ],
    "MTK Hard": [
        {"q": "Turunan dari f(x) = 3x⁴ - 2x² + 5 adalah...", "opts": ["12x³ - 4x", "12x³ - 2x", "3x³ - 4x", "12x³ - 4"], "ans": 0},
        {"q": "Nilai dari lim(x→2) (x² - 4)/(x - 2) adalah...", "opts": ["2", "4", "0", "∞"], "ans": 1},
        {"q": "∫(2x + 3)dx = ...", "opts": ["x² + 3x + C", "2x² + 3x + C", "x² + 3 + C", "2x + C"], "ans": 0},
        {"q": "Turunan dari f(x) = sin(x)·cos(x) adalah...", "opts": ["cos²(x) - sin²(x)", "sin²(x) - cos²(x)", "-sin(2x)", "2sin(x)cos(x)"], "ans": 0},
        {"q": "Nilai dari ∫₀¹ x² dx adalah...", "opts": ["1/2", "1/3", "1/4", "2/3"], "ans": 1},
        {"q": "Lim(x→0) sin(x)/x = ...", "opts": ["0", "∞", "1", "-1"], "ans": 2},
        {"q": "Turunan kedua dari f(x) = x⁵ adalah...", "opts": ["5x⁴", "20x³", "20x²", "5x³"], "ans": 1},
        {"q": "∫ eˣ dx = ...", "opts": ["eˣ + C", "xeˣ + C", "eˣ/x + C", "e + C"], "ans": 0},
        {"q": "Titik kritis f(x) = x³ - 3x ada di x = ...", "opts": ["x = 0", "x = ±1", "x = ±2", "x = ±3"], "ans": 1},
        {"q": "Nilai lim(x→∞) (2x² + 1)/(x² - 3) = ...", "opts": ["0", "1", "2", "∞"], "ans": 2},
    ],
    "IPA Easy": [
        {"q": "Organel sel yang berperan sebagai 'pabrik energi' adalah...", "opts": ["Nukleus", "Ribosom", "Mitokondria", "Vakuola"], "ans": 2},
        {"q": "Rumus kimia air adalah...", "opts": ["H₂O₂", "HO", "H₂O", "H₃O"], "ans": 2},
        {"q": "Hewan yang berkembang biak dengan cara ovipar adalah...", "opts": ["Paus", "Lumba-lumba", "Ayam", "Kuda"], "ans": 2},
        {"q": "Gaya yang bekerja pada benda yang jatuh bebas disebut...", "opts": ["Gaya gesek", "Gaya gravitasi", "Gaya magnet", "Gaya pegas"], "ans": 1},
        {"q": "Proses tumbuhan membuat makanan sendiri disebut...", "opts": ["Respirasi", "Transpirasi", "Fotosintesis", "Fermentasi"], "ans": 2},
        {"q": "Perubahan es menjadi air disebut...", "opts": ["Membeku", "Mencair", "Menguap", "Menyublim"], "ans": 1},
        {"q": "Planet terdekat dari Matahari adalah...", "opts": ["Venus", "Bumi", "Mars", "Merkurius"], "ans": 3},
        {"q": "Bagian darah yang berfungsi membawa oksigen adalah...", "opts": ["Plasma darah", "Trombosit", "Sel darah putih", "Sel darah merah"], "ans": 3},
        {"q": "Benda yang dapat ditarik magnet disebut benda...", "opts": ["Isolator", "Konduktor", "Feromagnetik", "Diamagnetik"], "ans": 2},
        {"q": "Gas yang dihasilkan tumbuhan saat fotosintesis adalah...", "opts": ["CO₂", "N₂", "O₂", "H₂"], "ans": 2},
    ],
    "IPA Hard": [
        {"q": "Hukum Termodinamika I menyatakan bahwa...", "opts": ["Entropi selalu meningkat", "Energi tidak dapat diciptakan atau dimusnahkan", "Kalor mengalir dari panas ke dingin", "Tekanan dan volume berbanding terbalik"], "ans": 1},
        {"q": "Pasangan basa nitrogen yang benar pada DNA adalah...", "opts": ["Adenin-Sitosin", "Guanin-Timin", "Adenin-Timin dan Guanin-Sitosin", "Adenin-Urasil"], "ans": 2},
        {"q": "Stoikiometri: Berapa mol O₂ diperlukan untuk membakar 2 mol C₃H₈? (C₃H₈ + 5O₂ → 3CO₂ + 4H₂O)", "opts": ["5 mol", "10 mol", "15 mol", "20 mol"], "ans": 1},
        {"q": "Dalam proses meiosis, sel anak yang dihasilkan bersifat...", "opts": ["Diploid (2n)", "Haploid (n)", "Poliploid", "Tetraploid"], "ans": 1},
        {"q": "Persamaan gas ideal adalah...", "opts": ["PV = nT", "PV = nRT", "P = nRT/V²", "PV² = nRT"], "ans": 1},
        {"q": "Reaksi eksoterm adalah reaksi yang...", "opts": ["Menyerap kalor dari lingkungan", "Melepaskan kalor ke lingkungan", "Tidak melibatkan perubahan energi", "Terjadi pada suhu tinggi"], "ans": 1},
        {"q": "Genotip AaBb disilangkan dengan AaBb menghasilkan berapa macam fenotip?", "opts": ["2", "3", "4", "9"], "ans": 2},
        {"q": "Massa molar NaCl adalah... (Na=23, Cl=35,5)", "opts": ["55,5 g/mol", "58,5 g/mol", "60,5 g/mol", "62,5 g/mol"], "ans": 1},
        {"q": "Efek fotolistrik pertama kali dijelaskan oleh...", "opts": ["Newton", "Bohr", "Einstein", "Planck"], "ans": 2},
        {"q": "Larutan buffer berfungsi untuk...", "opts": ["Meningkatkan pH", "Menurunkan pH", "Mempertahankan pH", "Mengukur pH"], "ans": 2},
    ],
    "IPS Easy": [
        {"q": "Ibu kota negara Indonesia adalah...", "opts": ["Surabaya", "Bandung", "Jakarta", "Medan"], "ans": 2},
        {"q": "Proklamasi kemerdekaan Indonesia dibacakan pada tanggal...", "opts": ["17 Agustus 1945", "17 Agustus 1944", "18 Agustus 1945", "17 Juli 1945"], "ans": 0},
        {"q": "Sungai terpanjang di Indonesia adalah...", "opts": ["Sungai Musi", "Sungai Mahakam", "Sungai Kapuas", "Sungai Brantas"], "ans": 2},
        {"q": "Pancasila terdiri dari berapa sila?", "opts": ["3", "4", "5", "6"], "ans": 2},
        {"q": "Benua terluas di dunia adalah...", "opts": ["Amerika", "Afrika", "Eropa", "Asia"], "ans": 3},
        {"q": "Pahlawan yang dijuluki 'Bapak Proklamator' Indonesia adalah...", "opts": ["Soekarno dan Hatta", "Sudirman dan Nasution", "Diponegoro dan Imam Bonjol", "Cut Nyak Dien dan Kartini"], "ans": 0},
        {"q": "Lambang negara Indonesia adalah...", "opts": ["Garuda Pancasila", "Banteng", "Pohon Beringin", "Padi dan Kapas"], "ans": 0},
        {"q": "Gunung tertinggi di Indonesia adalah...", "opts": ["Gunung Rinjani", "Gunung Semeru", "Puncak Jaya", "Gunung Kerinci"], "ans": 2},
        {"q": "Sidang BPUPKI pertama membahas tentang...", "opts": ["Wilayah Indonesia", "Dasar negara", "Bentuk pemerintahan", "Undang-undang dasar"], "ans": 1},
        {"q": "Negara yang berbatasan langsung dengan Indonesia di bagian utara adalah...", "opts": ["Australia", "Papua Nugini", "Malaysia", "Filipina"], "ans": 2},
    ],
    "English Easy": [
        {"q": "Choose the correct sentence:", "opts": ["She go to school every day.", "She goes to school every day.", "She going to school every day.", "She gone to school every day."], "ans": 1},
        {"q": "What is the plural of 'child'?", "opts": ["Childs", "Childes", "Children", "Childrens"], "ans": 2},
        {"q": "The opposite of 'hot' is...", "opts": ["Warm", "Cool", "Cold", "Freeze"], "ans": 2},
        {"q": "Choose the correct past tense: 'I ___ a book yesterday.'", "opts": ["read", "reads", "reading", "readed"], "ans": 0},
        {"q": "What does 'beautiful' mean in Indonesian?", "opts": ["Pintar", "Cantik/Indah", "Kuat", "Cepat"], "ans": 1},
        {"q": "Choose the correct article: '___ elephant is a large animal.'", "opts": ["A", "An", "The", "—"], "ans": 1},
        {"q": "Which word is a verb?", "opts": ["Quickly", "Happy", "Run", "Beautiful"], "ans": 2},
        {"q": "Complete: 'There ___ many students in the classroom.'", "opts": ["is", "are", "am", "be"], "ans": 1},
        {"q": "What is the synonym of 'big'?", "opts": ["Small", "Tiny", "Large", "Short"], "ans": 2},
        {"q": "Choose the correct question: 'Where ___ you from?'", "opts": ["is", "am", "are", "be"], "ans": 2},
    ],
    "English Hard": [
        {"q": "Which sentence uses the subjunctive mood correctly?", "opts": ["I wish I was taller.", "I wish I were taller.", "I wish I am taller.", "I wish I be taller."], "ans": 1},
        {"q": "The word 'ephemeral' most closely means:", "opts": ["Eternal", "Mysterious", "Short-lived", "Significant"], "ans": 2},
        {"q": "Identify the error: 'The data shows that climate change effects is accelerating.'", "opts": ["'data' should be 'datum'", "'shows' should be 'show'", "'effects' should be 'affects'", "Both A and B"], "ans": 3},
        {"q": "Which best describes a 'red herring' in argumentation?", "opts": ["A factual error", "An irrelevant distraction from the main issue", "An emotional appeal", "A circular argument"], "ans": 1},
        {"q": "In IELTS Writing Task 2, a 'discursive essay' requires:", "opts": ["Only one viewpoint", "Presenting both sides before giving an opinion", "Only factual information", "A narrative structure"], "ans": 1},
        {"q": "The passage implies: 'Despite unprecedented economic growth, the Gini coefficient worsened.' This means:", "opts": ["Growth caused poverty", "Wealth distribution became more unequal", "The economy failed overall", "The Gini coefficient measures growth"], "ans": 1},
        {"q": "Choose the correct conditional: 'If she ___ harder, she would have passed.'", "opts": ["studied", "had studied", "would study", "studies"], "ans": 1},
        {"q": "The word 'ubiquitous' means:", "opts": ["Unique", "Present everywhere", "Harmful", "Temporary"], "ans": 1},
        {"q": "'The government's policy, along with several new initiatives, ___ been implemented.'", "opts": ["have", "has", "had", "having"], "ans": 1},
        {"q": "Which word has a negative connotation?", "opts": ["Confident", "Assertive", "Arrogant", "Decisive"], "ans": 2},
    ],
    "Analogi Logika": [
        {"q": "\"Mobil listrik lebih aman dari mobil bensin karena tidak ada knalpot.\" Apakah ini False Analogy?", "opts": ["Bukan False Analogy", "False Analogy"], "ans": 1},
        {"q": "\"Jika pisau bisa melukai orang, maka dokter yang menggunakan pisau bedah juga berbahaya.\" Apakah ini False Analogy?", "opts": ["Bukan False Analogy", "False Analogy"], "ans": 1},
        {"q": "\"Belajar seperti menanam pohon: semakin sering disiram (diulang), semakin kuat akarnya (pemahamannya).\" Apakah ini False Analogy?", "opts": ["Bukan False Analogy", "False Analogy"], "ans": 0},
        {"q": "\"Negara seperti kapal: butuh kapten (presiden) yang tegas untuk mengarungi badai (krisis).\" Analogi ini valid karena kedua sistem memiliki hierarki dan tujuan. Apakah ini False Analogy?", "opts": ["Bukan False Analogy", "False Analogy"], "ans": 0},
        {"q": "\"Vaksin seperti helm: melindungi diri sendiri. Jadi tidak memakai vaksin hanya merugikan diri sendiri, tidak orang lain.\" Apakah ini False Analogy?", "opts": ["Bukan False Analogy", "False Analogy"], "ans": 1},
    ],
}

MODES = list(QUIZ_DATA.keys())
GAME_MODES = ['Classic', 'Steal']
PLAY_MODES = ['Solo', 'Team']
TEAM_SIZES = [1, 2, 3]
TEAM_SIZE_LABELS = {1: '1v1', 2: '2v2', 3: '3v3'}
TIMER_OPTIONS = [15, 30, 60]
MAX_PLAYERS = 6
TEAM_NAMES = ['Tim Alpha', 'Tim Bravo']
TEAM_COLORS = {'A': '#2980b9', 'B': '#e67e22'}

# ─── Room State ───────────────────────────────────────────────────────────────

rooms = {}
player_sessions = {}


def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))


def new_player(name, player_id, team=None):
    return {
        'name': name, 'score': 0, 'answered': False,
        'answer': None, 'id': player_id, 'team': team,
        'card_picked': False, 'card_idx': None,
        'card_effect': None, 'card_value': 0,
        'card_label': '', 'card_icon': '',
        'q_index': 0, 'my_correct_idx': None,
        'my_questions': None, 'finished': False,
        'timer_greenlet': None,
    }


def room_summary(code, room):
    players = room['players']
    p_list = [
        {'name': v['name'], 'score': v['score'], 'id': v['id'],
         'team': v.get('team'), 'is_host': k == room['host'], 'sid': k,
         'finished': v.get('finished', False)}
        for k, v in players.items()
    ]
    return {
        'code': code,
        'mode': room['mode'],
        'game_mode': room.get('game_mode', 'Classic'),
        'play_mode': room.get('play_mode', 'Solo'),
        'team_size': room.get('team_size', 1),
        'players': p_list,
        'state': room['state'],
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
        'max_players': room.get('max_players', MAX_PLAYERS),
    }


def broadcast_scoreboard(code):
    room = rooms.get(code)
    if not room:
        return
    p_list = [
        {'name': v['name'], 'score': v['score'], 'id': v['id'],
         'team': v.get('team'), 'finished': v.get('finished', False)}
        for v in room['players'].values()
    ]
    socketio.emit('score_update', {'players': p_list}, room=code)


def cancel_room_timer(room):
    if room.get('timer_greenlet'):
        try:
            room['timer_greenlet'].kill()
        except Exception:
            pass
        room['timer_greenlet'] = None


def cancel_player_timer(p):
    if p.get('timer_greenlet'):
        try:
            p['timer_greenlet'].kill()
        except Exception:
            pass
        p['timer_greenlet'] = None


def cancel_all_player_timers(room):
    for p in room['players'].values():
        cancel_player_timer(p)


def generate_card_deck():
    cards = [
        {'type': 'minus', 'value': -90, 'label': '-90 Poin', 'icon': '💥'},
        {'type': 'minus', 'value': -90, 'label': '-90 Poin', 'icon': '💥'},
        {'type': 'plus', 'value': 50, 'label': '+50 Poin', 'icon': '⭐'},
        {'type': 'plus', 'value': 50, 'label': '+50 Poin', 'icon': '⭐'},
        {'type': 'swap', 'value': 0, 'label': 'Swap Poin!', 'icon': '🔄'},
    ]
    random.shuffle(cards)
    return cards


def assign_team(room, sid):
    """Auto-assign team balancing A/B based on team_size."""
    team_size = room.get('team_size', 1)
    count_a = sum(1 for p in room['players'].values() if p.get('team') == 'A')
    count_b = sum(1 for p in room['players'].values() if p.get('team') == 'B')
    if count_a <= count_b and count_a < team_size:
        return 'A'
    return 'B'


# ─── Classic / Team Mode ──────────────────────────────────────────────────────

def start_room_timer(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_room_timer(room)
    duration = room.get('timer_duration', 30)
    g = eventlet.spawn(room_timer_worker, code, duration)
    room['timer_greenlet'] = g


def room_timer_worker(code, duration):
    eventlet.sleep(duration)
    room = rooms.get(code)
    if not room or room['state'] != 'question':
        return
    for p in room['players'].values():
        if not p['answered']:
            p['answered'] = True
            p['answer'] = -1
    end_round_classic(code)


def send_question_classic(code):
    room = rooms.get(code)
    if not room:
        return
    room['state'] = 'question'
    room['q_start_time'] = time.time()
    q = room['questions'][room['current_q']]
    for p in room['players'].values():
        p['answered'] = False
        p['answer'] = None
        p['my_correct_idx'] = q['ans']

    socketio.emit('new_question', {
        'question': q['q'],
        'opts': q['opts'],
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
        'num_opts': len(q['opts']),
        'game_mode': room.get('game_mode', 'Classic'),
        'my_correct_idx': q['ans'],
    }, room=code)
    start_room_timer(code)


def end_round_classic(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_room_timer(room)
    room['state'] = 'result'
    q = room['questions'][room['current_q']]
    correct_idx = q['ans']

    score_changes = {}
    for sid, p in room['players'].items():
        if p['answer'] == correct_idx:
            delta = 10
        elif p['answer'] == -1:
            delta = -10
        else:
            delta = -5
        p['score'] += delta
        score_changes[sid] = delta

    p_list = [
        {
            'name': v['name'], 'score': v['score'],
            'answer': v['answer'], 'delta': score_changes[k],
            'id': v['id'], 'sid': k, 'team': v.get('team'),
        }
        for k, v in room['players'].items()
    ]

    socketio.emit('round_result', {
        'correct_idx': correct_idx,
        'players': p_list,
        'question': q['q'],
        'opts': q['opts'],
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
        'game_mode': room.get('game_mode', 'Classic'),
    }, room=code)

    broadcast_scoreboard(code)
    eventlet.spawn(advance_classic_after_delay, code)


def advance_classic_after_delay(code):
    eventlet.sleep(4.5)
    room = rooms.get(code)
    if not room:
        return
    room['current_q'] += 1
    if room['current_q'] >= len(room['questions']):
        finish_game(code)
    else:
        send_question_classic(code)


# ─── Steal Mode (Independent Progression) ─────────────────────────────────────

def start_player_timer(code, sid):
    room = rooms.get(code)
    if not room:
        return
    p = room['players'].get(sid)
    if not p:
        return
    cancel_player_timer(p)
    duration = room.get('timer_duration', 30)
    g = eventlet.spawn(player_timer_worker, code, sid, duration)
    p['timer_greenlet'] = g


def player_timer_worker(code, sid, duration):
    eventlet.sleep(duration)
    room = rooms.get(code)
    if not room:
        return
    p = room['players'].get(sid)
    if not p or p['answered'] or p.get('finished'):
        return
    p['answered'] = True
    p['answer'] = -1
    socketio.emit('steal_answer_result', {
        'correct': False, 'timed_out': True,
    }, room=sid)
    eventlet.spawn(advance_player_steal_after_delay, code, sid, 2.0)


def send_player_question_steal(code, sid):
    room = rooms.get(code)
    if not room:
        return
    p = room['players'].get(sid)
    if not p or p.get('finished'):
        return
    if not p.get('my_questions'):
        p['my_questions'] = list(room['questions'])
        random.shuffle(p['my_questions'])

    qi = p['q_index']
    if qi >= len(p['my_questions']):
        p['finished'] = True
        socketio.emit('player_finished', {}, room=sid)
        check_all_finished_steal(code)
        return

    q = p['my_questions'][qi]
    p['answered'] = False
    p['answer'] = None
    p['card_picked'] = False
    p['card_effect'] = None
    p['card_idx'] = None
    p['my_correct_idx'] = q['ans']

    socketio.emit('new_question', {
        'question': q['q'],
        'opts': q['opts'],
        'current_q': qi,
        'total_q': len(p['my_questions']),
        'num_opts': len(q['opts']),
        'game_mode': 'Steal',
        'my_correct_idx': q['ans'],
    }, room=sid)
    start_player_timer(code, sid)


def advance_player_steal_after_delay(code, sid, delay=2.0):
    eventlet.sleep(delay)
    room = rooms.get(code)
    if not room:
        return
    p = room['players'].get(sid)
    if not p or p.get('finished'):
        return
    p['q_index'] += 1
    send_player_question_steal(code, sid)


def handle_steal_answer(code, sid, answer):
    room = rooms.get(code)
    if not room:
        return
    p = room['players'].get(sid)
    if not p or p['answered']:
        return
    cancel_player_timer(p)
    p['answered'] = True
    p['answer'] = answer

    was_correct = (answer == p.get('my_correct_idx'))
    if was_correct:
        cards = generate_card_deck()
        p['card_deck'] = cards
        socketio.emit('card_pick', {
            'cards': [{'label': c['label'], 'icon': c['icon'], 'type': c['type']} for c in cards],
        }, room=sid)
    else:
        socketio.emit('steal_answer_result', {
            'correct': False, 'timed_out': False,
        }, room=sid)
        eventlet.spawn(advance_player_steal_after_delay, code, sid, 2.0)


def handle_steal_pick_card(code, sid, card_idx):
    room = rooms.get(code)
    if not room:
        return
    p = room['players'].get(sid)
    if not p or p.get('card_picked'):
        return

    cards = p.get('card_deck', [])
    if card_idx is None or card_idx < 0 or card_idx >= len(cards):
        card_idx = 0

    card = cards[card_idx]
    p['card_picked'] = True
    p['card_idx'] = card_idx
    p['card_effect'] = card['type']
    p['card_value'] = card['value']
    p['card_label'] = card['label']
    p['card_icon'] = card['icon']

    # Apply card effect
    if card['type'] == 'plus':
        p['score'] += card['value']
    elif card['type'] == 'minus':
        p['score'] += card['value']
    elif card['type'] == 'swap':
        # Swap with a random other player
        others = [s for s in room['players'] if s != sid and not room['players'][s].get('finished')]
        if others:
            target_sid = random.choice(others)
            target = room['players'][target_sid]
            p['score'], target['score'] = target['score'], p['score']

    socketio.emit('card_revealed', {
        'card_idx': card_idx,
        'card': {'label': card['label'], 'icon': card['icon'], 'type': card['type']},
    }, room=sid)

    broadcast_scoreboard(code)
    eventlet.spawn(advance_player_steal_after_delay, code, sid, 3.0)


def check_all_finished_steal(code):
    room = rooms.get(code)
    if not room:
        return
    all_done = all(p.get('finished', False) for p in room['players'].values())
    if all_done:
        finish_game(code)


def start_steal_game(code):
    room = rooms.get(code)
    if not room:
        return
    room['state'] = 'question'
    for sid in room['players']:
        send_player_question_steal(code, sid)


# ─── Finish Game ──────────────────────────────────────────────────────────────

def finish_game(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_room_timer(room)
    cancel_all_player_timers(room)
    room['state'] = 'finished'
    players = room['players']
    game_mode = room.get('game_mode', 'Classic')

    p_list = sorted(
        [{'name': v['name'], 'score': v['score'], 'id': v['id'], 'team': v.get('team')} for v in players.values()],
        key=lambda x: x['score'], reverse=True
    )

    result = {'rankings': p_list, 'game_mode': game_mode, 'play_mode': room.get('play_mode', 'Solo')}

    if room.get('play_mode') == 'Team':
        teams = {}
        for p in p_list:
            t = p.get('team')
            if t:
                tn = TEAM_NAMES[0] if t == 'A' else TEAM_NAMES[1]
                if tn not in teams:
                    teams[tn] = {'team': t, 'name': tn, 'score': 0, 'members': []}
                teams[tn]['score'] += p['score']
                teams[tn]['members'].append(p)
        result['team_rankings'] = sorted(teams.values(), key=lambda x: x['score'], reverse=True)

    socketio.emit('game_over', result, room=code)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, modes=MODES, game_modes=GAME_MODES, play_modes=PLAY_MODES, team_sizes=TEAM_SIZES, team_size_labels=TEAM_SIZE_LABELS, timer_options=TIMER_OPTIONS, max_players=MAX_PLAYERS)


# ─── Socket.IO Handlers ───────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    pass


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    _remove_player(sid)


@socketio.on('restore_session')
def on_restore_session(data):
    player_id = data.get('player_id')
    room_code = data.get('room_code')
    sid = request.sid

    if not player_id or not room_code:
        emit('restore_failed', {'reason': 'missing_data'})
        return

    room = rooms.get(room_code)
    if not room:
        emit('restore_failed', {'reason': 'room_not_found'})
        return

    old_sid = None
    player_data = None
    for s, p in list(room['players'].items()):
        if p['id'] == player_id:
            old_sid = s
            player_data = p
            break

    if not player_data:
        emit('restore_failed', {'reason': 'player_not_found'})
        return

    if old_sid and old_sid != sid:
        room['players'][sid] = room['players'].pop(old_sid)
        if room['host'] == old_sid:
            room['host'] = sid
        cancel_player_timer(player_data)
        player_data['answered'] = True

    player_sessions[player_id] = {'room_code': room_code, 'sid': sid}
    join_room(room_code)

    state = room['state']
    restore_data = {
        'room_code': room_code,
        'player_id': player_id,
        'name': player_data['name'],
        'state': state,
        'is_host': room['host'] == sid,
        'room_info': room_summary(room_code, room),
    }

    if state == 'question':
        game_mode = room.get('game_mode', 'Classic')
        if game_mode == 'Steal':
            qi = player_data.get('q_index', 0)
            mq = player_data.get('my_questions') or room['questions']
            q = mq[qi % len(mq)]
            elapsed = time.time() - room.get('q_start_time', time.time())
            remaining_time = max(0, room.get('timer_duration', 30) - int(elapsed))
            restore_data['question_data'] = {
                'question': q['q'], 'opts': q['opts'],
                'current_q': qi, 'total_q': len(mq),
                'num_opts': len(q['opts']), 'remaining_time': remaining_time,
                'already_answered': player_data.get('answered', False),
                'my_answer': player_data.get('answer'),
                'game_mode': 'Steal', 'my_correct_idx': q['ans'],
            }
        else:
            q = room['questions'][room['current_q']]
            elapsed = time.time() - room.get('q_start_time', time.time())
            remaining_time = max(0, room.get('timer_duration', 30) - int(elapsed))
            restore_data['question_data'] = {
                'question': q['q'], 'opts': q['opts'],
                'current_q': room['current_q'], 'total_q': len(room['questions']),
                'num_opts': len(q['opts']), 'remaining_time': remaining_time,
                'already_answered': player_data.get('answered', False),
                'my_answer': player_data.get('answer'),
                'game_mode': game_mode,
            }
    elif state == 'finished':
        p_sorted = sorted(
            [{'name': v['name'], 'score': v['score'], 'id': v['id'], 'team': v.get('team')} for v in room['players'].values()],
            key=lambda x: x['score'], reverse=True
        )
        restore_data['rankings'] = p_sorted
        restore_data['play_mode'] = room.get('play_mode', 'Solo')
        if room.get('play_mode') == 'Team':
            teams = {}
            for p in p_sorted:
                t = p.get('team')
                if t:
                    tn = TEAM_NAMES[0] if t == 'A' else TEAM_NAMES[1]
                    if tn not in teams:
                        teams[tn] = {'team': t, 'name': tn, 'score': 0, 'members': []}
                    teams[tn]['score'] += p['score']
                    teams[tn]['members'].append(p)
            restore_data['team_rankings'] = sorted(teams.values(), key=lambda x: x['score'], reverse=True)

    emit('session_restored', restore_data)


@socketio.on('create_room')
def on_create_room(data):
    name = data.get('name', 'Player').strip() or 'Player'
    mode = data.get('mode', MODES[0])
    game_mode = data.get('game_mode', 'Classic')
    play_mode = data.get('play_mode', 'Solo')
    team_size = data.get('team_size', 1)
    timer_duration = data.get('timer_duration', 30)
    player_id = data.get('player_id', gen_code() + gen_code())
    sid = request.sid

    if mode not in QUIZ_DATA:
        mode = MODES[0]
    if game_mode not in GAME_MODES:
        game_mode = 'Classic'
    if play_mode not in PLAY_MODES:
        play_mode = 'Solo'
    if team_size not in TEAM_SIZES:
        team_size = 1
    if timer_duration not in TIMER_OPTIONS:
        timer_duration = 30

    if play_mode == 'Team':
        max_players = team_size * 2
    else:
        max_players = MAX_PLAYERS

    code = gen_code()
    while code in rooms:
        code = gen_code()

    questions = list(QUIZ_DATA[mode])
    random.shuffle(questions)

    team = 'A' if play_mode == 'Team' else None
    rooms[code] = {
        'players': {sid: new_player(name, player_id, team)},
        'host': sid,
        'mode': mode,
        'game_mode': game_mode,
        'play_mode': play_mode,
        'team_size': team_size,
        'max_players': max_players,
        'timer_duration': timer_duration,
        'questions': questions,
        'current_q': 0,
        'state': 'lobby',
        'timer_greenlet': None,
        'q_start_time': 0,
        'chat': [],
    }
    player_sessions[player_id] = {'room_code': code, 'sid': sid}
    join_room(code)

    emit('room_created', {
        'code': code,
        'player_id': player_id,
        'name': name,
        'is_host': True,
        'room_info': room_summary(code, rooms[code]),
    })


@socketio.on('join_room_req')
def on_join_room(data):
    name = data.get('name', 'Player').strip() or 'Player'
    code = data.get('code', '').strip().upper()
    player_id = data.get('player_id', gen_code() + gen_code())
    sid = request.sid

    if code not in rooms:
        emit('join_error', {'message': 'Room tidak ditemukan!'})
        return

    room = rooms[code]
    if len(room['players']) >= room.get('max_players', MAX_PLAYERS):
        emit('join_error', {'message': 'Room sudah penuh!'})
        return
    if room['state'] != 'lobby':
        emit('join_error', {'message': 'Permainan sudah dimulai!'})
        return

    team = assign_team(room, sid) if room.get('play_mode') == 'Team' else None
    room['players'][sid] = new_player(name, player_id, team)
    player_sessions[player_id] = {'room_code': code, 'sid': sid}
    join_room(code)

    summary = room_summary(code, room)
    socketio.emit('room_update', summary, room=code)
    emit('room_joined', {
        'code': code,
        'player_id': player_id,
        'name': name,
        'is_host': False,
        'room_info': summary,
    })


@socketio.on('start_game')
def on_start_game(data):
    sid = request.sid
    code = data.get('code')
    room = rooms.get(code)
    if not room:
        return
    if room['host'] != sid:
        emit('error_msg', {'message': 'Hanya host yang bisa memulai!'})
        return
    if room.get('play_mode') == 'Team':
        max_p = room.get('max_players', 6)
        if len(room['players']) < max_p:
            emit('error_msg', {'message': f'Team mode butuh {max_p} pemain (penuhi room dulu)!'})
            return
    elif len(room['players']) < 2:
        emit('error_msg', {'message': 'Butuh minimal 2 pemain untuk memulai!'})
        return

    game_mode = room.get('game_mode', 'Classic')
    if game_mode == 'Steal':
        start_steal_game(code)
    else:
        send_question_classic(code)


@socketio.on('submit_answer')
def on_submit_answer(data):
    sid = request.sid
    code = data.get('code')
    answer = data.get('answer')
    room = rooms.get(code)

    if not room or room['state'] != 'question':
        return
    player = room['players'].get(sid)
    if not player or player['answered']:
        return

    game_mode = room.get('game_mode', 'Classic')

    if game_mode == 'Steal':
        handle_steal_answer(code, sid, answer)
    else:
        player['answered'] = True
        player['answer'] = answer
        for other_sid in room['players']:
            if other_sid != sid:
                socketio.emit('opponent_answered', {}, room=other_sid)
        all_answered = all(p['answered'] for p in room['players'].values())
        if all_answered:
            end_round_classic(code)


@socketio.on('pick_card')
def on_pick_card(data):
    sid = request.sid
    code = data.get('code')
    card_idx = data.get('card_idx')
    room = rooms.get(code)
    if not room:
        return
    game_mode = room.get('game_mode', 'Classic')
    if game_mode != 'Steal':
        return
    handle_steal_pick_card(code, sid, card_idx)


@socketio.on('leave_room')
def on_leave_room(data):
    sid = request.sid
    code = data.get('code')
    room = rooms.get(code)
    if not room:
        return
    player = room['players'].get(sid)
    if not player:
        return
    pid = player['id']
    leave_room(code)
    _remove_player(sid, code)


def _remove_player(sid, code=None):
    found_code = code
    room = None
    if found_code:
        room = rooms.get(found_code)
    if not room:
        for c, r in list(rooms.items()):
            if sid in r['players']:
                found_code = c
                room = r
                break
    if not room or not found_code:
        return

    player = room['players'].get(sid)
    if not player:
        return

    pid = player['id']
    cancel_player_timer(player)

    if pid in player_sessions:
        del player_sessions[pid]

    if room['state'] == 'lobby':
        del room['players'][sid]
        if len(room['players']) == 0:
            del rooms[found_code]
        else:
            if room['host'] == sid:
                room['host'] = next(iter(room['players']))
            socketio.emit('room_update', room_summary(found_code, room), room=found_code)
    else:
        game_mode = room.get('game_mode', 'Classic')
        del room['players'][sid]
        if len(room['players']) == 0:
            cancel_room_timer(room)
            del rooms[found_code]
        elif game_mode == 'Steal':
            remaining = [
                {'name': v['name'], 'score': v['score'], 'id': v['id'], 'finished': v.get('finished', False)}
                for v in room['players'].values()
            ]
            socketio.emit('player_left', {
                'left_name': player['name'],
                'remaining_players': remaining,
            }, room=found_code)
            check_all_finished_steal(found_code)
        else:
            cancel_room_timer(room)
            remaining = [
                {'name': v['name'], 'score': v['score'], 'id': v['id']}
                for v in room['players'].values()
            ]
            socketio.emit('opponent_disconnected', {
                'disconnected_name': player['name'],
                'remaining_players': remaining,
            }, room=found_code)
            del rooms[found_code]


# ─── Chat Handler ────────────────────────────────────────────────────────────

@socketio.on('send_chat')
def on_send_chat(data):
    sid = request.sid
    code = data.get('code')
    msg = data.get('msg', '').strip()
    room = rooms.get(code)
    if not room or not msg:
        return
    player = room['players'].get(sid)
    if not player:
        return
    if len(msg) > 200:
        msg = msg[:200]

    chat_msg = {
        'name': player['name'],
        'msg': msg,
        'ts': time.time(),
        'id': player['id'],
    }
    room['chat'].append(chat_msg)
    if len(room['chat']) > 50:
        room['chat'] = room['chat'][-50:]

    socketio.emit('chat_message', chat_msg, room=code)


# ─── WebRTC Voice Signaling ───────────────────────────────────────────────────

@socketio.on('voice_offer')
def on_voice_offer(data):
    sid = request.sid
    code = data.get('code')
    room = rooms.get(code)
    if not room:
        return
    for other_sid in room['players']:
        if other_sid != sid:
            socketio.emit('voice_offer', {
                'sdp': data.get('sdp'),
                'from_id': room['players'][sid]['id'],
            }, room=other_sid)


@socketio.on('voice_answer')
def on_voice_answer(data):
    sid = request.sid
    code = data.get('code')
    room = rooms.get(code)
    if not room:
        return
    for other_sid in room['players']:
        if other_sid != sid:
            socketio.emit('voice_answer', {
                'sdp': data.get('sdp'),
                'from_id': room['players'][sid]['id'],
            }, room=other_sid)


@socketio.on('voice_ice')
def on_voice_ice(data):
    sid = request.sid
    code = data.get('code')
    room = rooms.get(code)
    if not room:
        return
    for other_sid in room['players']:
        if other_sid != sid:
            socketio.emit('voice_ice', {
                'candidate': data.get('candidate'),
                'from_id': room['players'][sid]['id'],
            }, room=other_sid)


@socketio.on('voice_start')
def on_voice_start(data):
    sid = request.sid
    code = data.get('code')
    room = rooms.get(code)
    if not room:
        return
    for other_sid in room['players']:
        if other_sid != sid:
            socketio.emit('voice_start', {
                'from_id': room['players'][sid]['id'],
            }, room=other_sid)


# ─── HTML Template ────────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QuizBattle!</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.1/socket.io.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'Montserrat',sans-serif;background:linear-gradient(135deg,#1a0533 0%,#2d0a5e 40%,#1a0040 100%);min-height:100vh;color:#fff;overflow-x:hidden;}
  .screen{display:none;min-height:100vh;}
  .screen.active{display:flex;flex-direction:column;}

  @keyframes popIn{0%{transform:scale(0.5);opacity:0;}70%{transform:scale(1.1);}100%{transform:scale(1);opacity:1;}}
  @keyframes shake{0%,100%{transform:translateX(0);}20%,60%{transform:translateX(-8px);}40%,80%{transform:translateX(8px);}}
  @keyframes slideUp{from{transform:translateY(40px);opacity:0;}to{transform:translateY(0);opacity:1;}}
  @keyframes pulse{0%,100%{transform:scale(1);}50%{transform:scale(1.08);}}
  @keyframes floatUp{0%{transform:translateY(0);opacity:1;}100%{transform:translateY(-80px);opacity:0;}}
  @keyframes timerPulse{0%,100%{transform:scale(1);}50%{transform:scale(1.05);}}
  @keyframes fadeIn{from{opacity:0;}to{opacity:1;}}
  @keyframes bounceIn{0%{transform:scale(0.3);opacity:0;}50%{transform:scale(1.05);}70%{transform:scale(0.95);}100%{transform:scale(1);opacity:1;}}
  @keyframes cardFlip{0%{transform:rotateY(0deg) scale(0.8);opacity:0;}50%{transform:rotateY(180deg) scale(1.1);}100%{transform:rotateY(360deg) scale(1);opacity:1;}}
  @keyframes glow{0%,100%{box-shadow:0 0 20px rgba(243,156,18,0.5);}50%{box-shadow:0 0 40px rgba(243,156,18,0.8);}}

  .anim-popIn{animation:popIn 0.4s ease forwards;}
  .anim-shake{animation:shake 0.5s ease;}
  .anim-slideUp{animation:slideUp 0.4s ease forwards;}
  .anim-pulse{animation:pulse 1.5s ease infinite;}
  .anim-bounceIn{animation:bounceIn 0.6s ease forwards;}
  .anim-fadeIn{animation:fadeIn 0.3s ease forwards;}
  .anim-cardFlip{animation:cardFlip 0.6s ease forwards;}

  .btn-answer{
    position:relative;overflow:hidden;cursor:pointer;border:none;
    border-radius:12px;padding:18px 12px;font-family:'Montserrat',sans-serif;
    font-size:1.1rem;font-weight:800;color:#fff;text-shadow:0 2px 4px rgba(0,0,0,0.4);
    transition:transform 0.1s,filter 0.1s;box-shadow:0 6px 0 rgba(0,0,0,0.35);
    width:100%;text-align:center;display:flex;align-items:center;gap:10px;
    min-height:72px;word-break:break-word;
  }
  .btn-answer:hover:not(:disabled){transform:translateY(-2px);filter:brightness(1.1);}
  .btn-answer:active:not(:disabled){transform:translateY(4px);box-shadow:0 2px 0 rgba(0,0,0,0.35);}
  .btn-answer:disabled{cursor:default;opacity:0.75;}
  .btn-answer.correct{background:#27ae60 !important;animation:popIn 0.3s ease;}
  .btn-answer.wrong{background:#c0392b !important;}
  .btn-a{background:#e74c3c;}
  .btn-b{background:#2980b9;}
  .btn-c{background:#f39c12;}
  .btn-d{background:#27ae60;}

  .btn-primary{
    background:linear-gradient(135deg,#f39c12,#e67e22);border:none;border-radius:12px;
    padding:14px 32px;font-family:'Montserrat',sans-serif;font-size:1.1rem;
    font-weight:800;color:#fff;cursor:pointer;box-shadow:0 4px 0 #b7770d;
    transition:transform 0.1s,box-shadow 0.1s;text-transform:uppercase;letter-spacing:1px;
  }
  .btn-primary:hover{transform:translateY(-2px);box-shadow:0 6px 0 #b7770d;}
  .btn-primary:active{transform:translateY(2px);box-shadow:0 2px 0 #b7770d;}
  .btn-primary:disabled{opacity:0.5;cursor:not-allowed;}

  .btn-secondary{
    background:rgba(255,255,255,0.15);border:2px solid rgba(255,255,255,0.4);
    border-radius:12px;padding:12px 28px;font-family:'Montserrat',sans-serif;
    font-size:1rem;font-weight:700;color:#fff;cursor:pointer;
    transition:background 0.2s,transform 0.1s;
  }
  .btn-secondary:hover{background:rgba(255,255,255,0.25);transform:translateY(-1px);}

  .timer-bar-container{width:100%;height:14px;background:rgba(0,0,0,0.3);border-radius:7px;overflow:hidden;margin-bottom:8px;}
  .timer-bar{height:100%;border-radius:7px;transition:width 1s linear,background-color 1s linear;background:#27ae60;}

  .score-float{
    position:absolute;font-size:1.4rem;font-weight:900;pointer-events:none;
    animation:floatUp 1.2s ease forwards;z-index:100;
  }

  .card{background:rgba(255,255,255,0.08);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.15);border-radius:20px;}

  .room-code{
    font-size:3.5rem;font-weight:900;letter-spacing:10px;
    background:linear-gradient(135deg,#f39c12,#e74c3c);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
  }

  .input-field{
    width:100%;padding:14px 18px;border-radius:12px;border:2px solid rgba(255,255,255,0.3);
    background:rgba(255,255,255,0.1);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:1rem;font-weight:600;outline:none;transition:border-color 0.2s;
  }
  .input-field:focus{border-color:#f39c12;}
  .input-field::placeholder{color:rgba(255,255,255,0.5);}
  .select-field{
    width:100%;padding:14px 18px;border-radius:12px;border:2px solid rgba(255,255,255,0.3);
    background:rgba(30,0,60,0.8);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:1rem;font-weight:600;outline:none;cursor:pointer;
  }
  .select-field option{background:#2d0a5e;}

  /* Multi-player scoreboard */
  .scoreboard{
    background:rgba(0,0,0,0.4);backdrop-filter:blur(8px);
    border-bottom:2px solid rgba(255,255,255,0.1);
    padding:8px 16px;display:flex;align-items:center;gap:8px;
    overflow-x:auto;position:relative;
  }
  .sb-player{
    text-align:center;min-width:80px;padding:4px 10px;border-radius:10px;
    background:rgba(255,255,255,0.08);position:relative;flex-shrink:0;
    border:2px solid transparent;
  }
  .sb-player.me{border-color:#f39c12;}
  .sb-player.team-A{border-color:#2980b9;}
  .sb-player.team-B{border-color:#e67e22;}
  .sb-name{font-size:0.7rem;font-weight:700;opacity:0.8;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .sb-val{font-size:1.3rem;font-weight:900;}
  .sb-team-tag{font-size:0.6rem;font-weight:800;padding:1px 6px;border-radius:8px;display:inline-block;margin-top:2px;}
  .sb-team-tag.A{background:#2980b9;color:#fff;}
  .sb-team-tag.B{background:#e67e22;color:#fff;}
  .sb-finished{font-size:0.55rem;font-weight:800;color:#2ecc71;}

  .top-points-badge{
    background:linear-gradient(135deg,#f39c12,#e67e22);
    padding:3px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;
    color:#1a0533;white-space:nowrap;box-shadow:0 2px 10px rgba(243,156,18,0.4);
    flex-shrink:0;
  }

  .question-card{
    background:#fff;color:#1a0533;border-radius:20px;padding:28px 24px;
    box-shadow:0 8px 32px rgba(0,0,0,0.4);position:relative;
  }
  .q-number-pill{
    display:inline-block;background:linear-gradient(135deg,#9b59b6,#6c3483);
    color:#fff;font-size:0.8rem;font-weight:800;padding:4px 14px;
    border-radius:20px;margin-bottom:12px;letter-spacing:1px;
  }
  .q-text{font-size:1.15rem;font-weight:700;line-height:1.5;color:#1a0533;}

  .circular-timer{position:relative;width:72px;height:72px;flex-shrink:0;}
  .circular-timer svg{transform:rotate(-90deg);}
  .circular-timer-num{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    font-size:1.5rem;font-weight:900;color:#1a0533;
    animation:timerPulse 1s ease infinite;
  }

  .opponent-badge{
    background:linear-gradient(135deg,#8e44ad,#6c3483);border-radius:8px;
    padding:6px 14px;font-size:0.85rem;font-weight:700;
    animation:slideUp 0.3s ease;display:inline-flex;align-items:center;gap:6px;
  }

  .result-feedback{
    background:linear-gradient(135deg,rgba(0,0,0,0.85),rgba(0,0,0,0.7));
    backdrop-filter:blur(4px);border-radius:16px;padding:20px;text-align:center;
  }

  .player-slot{
    background:rgba(255,255,255,0.08);border:2px dashed rgba(255,255,255,0.3);
    border-radius:14px;padding:12px;display:flex;align-items:center;gap:12px;
  }
  .player-slot.filled{border-style:solid;border-color:rgba(255,255,255,0.5);background:rgba(255,255,255,0.12);}
  .player-slot.team-A{border-color:#2980b9;}
  .player-slot.team-B{border-color:#e67e22;}
  .player-avatar{
    width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#9b59b6,#e74c3c);
    display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:900;flex-shrink:0;
  }

  .card-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:16px 0;}
  .pick-card{
    aspect-ratio:3/4;border-radius:14px;cursor:pointer;
    background:linear-gradient(135deg,#9b59b6,#6c3483);
    display:flex;align-items:center;justify-content:center;
    font-size:2.5rem;color:#fff;box-shadow:0 4px 12px rgba(0,0,0,0.4);
    transition:transform 0.2s,box-shadow 0.2s;position:relative;overflow:hidden;
    border:2px solid rgba(255,255,255,0.2);
  }
  .pick-card:hover:not(.revealed):not(.disabled){transform:translateY(-6px) scale(1.05);box-shadow:0 8px 24px rgba(155,89,182,0.6);border-color:#f39c12;}
  .pick-card.disabled{cursor:default;opacity:0.4;}
  .pick-card.revealed{cursor:default;animation:cardFlip 0.6s ease forwards;}
  .pick-card.minus{background:linear-gradient(135deg,#c0392b,#e74c3c);}
  .pick-card.plus{background:linear-gradient(135deg,#27ae60,#2ecc71);}
  .pick-card.swap{background:linear-gradient(135deg,#f39c12,#e67e22);}
  .card-back{font-size:2rem;}
  .card-front{display:none;flex-direction:column;align-items:center;gap:4px;}
  .pick-card.revealed .card-back{display:none;}
  .pick-card.revealed .card-front{display:flex;}
  .card-front-label{font-size:0.7rem;font-weight:800;text-align:center;}

  .chat-panel{
    position:fixed;right:0;top:0;height:100vh;width:320px;
    background:rgba(20,0,40,0.95);backdrop-filter:blur(20px);
    border-left:1px solid rgba(255,255,255,0.15);
    transform:translateX(100%);transition:transform 0.3s ease;
    z-index:200;display:flex;flex-direction:column;
  }
  .chat-panel.open{transform:translateX(0);}
  .chat-messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px;}
  .chat-bubble{
    max-width:80%;padding:8px 14px;border-radius:14px;font-size:0.85rem;font-weight:600;
    word-break:break-word;
  }
  .chat-bubble.me{background:linear-gradient(135deg,#f39c12,#e67e22);color:#1a0533;align-self:flex-end;border-bottom-right-radius:4px;}
  .chat-bubble.opp{background:rgba(255,255,255,0.12);color:#fff;align-self:flex-start;border-bottom-left-radius:4px;}
  .chat-name{font-size:0.7rem;font-weight:800;opacity:0.7;margin-bottom:2px;}
  .chat-input-row{padding:10px;display:flex;gap:8px;border-top:1px solid rgba(255,255,255,0.1);}
  .chat-input{
    flex:1;padding:10px 14px;border-radius:10px;border:1px solid rgba(255,255,255,0.2);
    background:rgba(255,255,255,0.1);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:0.85rem;outline:none;
  }
  .chat-input:focus{border-color:#f39c12;}
  .chat-send-btn{
    background:#f39c12;border:none;border-radius:10px;padding:0 16px;
    color:#1a0533;font-weight:900;cursor:pointer;font-size:1rem;
  }

  .chat-toggle-btn{
    position:fixed;right:16px;bottom:16px;width:52px;height:52px;border-radius:50%;
    background:linear-gradient(135deg,#9b59b6,#6c3483);border:none;color:#fff;
    font-size:1.5rem;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,0.4);
    z-index:201;display:none;align-items:center;justify-content:center;
    transition:transform 0.2s;
  }
  .chat-toggle-btn:hover{transform:scale(1.1);}
  .chat-toggle-btn.show{display:flex;}
  .chat-badge{
    position:absolute;top:-4px;right:-4px;background:#e74c3c;color:#fff;
    font-size:0.65rem;font-weight:900;border-radius:50%;width:20px;height:20px;
    display:none;align-items:center;justify-content:center;
  }
  .chat-badge.show{display:flex;}

  .voice-btn{
    position:fixed;right:80px;bottom:16px;width:52px;height:52px;border-radius:50%;
    background:rgba(255,255,255,0.15);border:2px solid rgba(255,255,255,0.3);
    color:#fff;font-size:1.4rem;cursor:pointer;
    z-index:201;display:none;align-items:center;justify-content:center;
    transition:all 0.2s;
  }
  .voice-btn:hover{transform:scale(1.1);}
  .voice-btn.show{display:flex;}
  .voice-btn.active{background:#27ae60;border-color:#2ecc71;box-shadow:0 0 16px rgba(39,174,96,0.5);}
  .voice-btn.muted{background:rgba(231,76,60,0.3);border-color:#e74c3c;}

  .mode-btn{
    padding:10px 16px;border-radius:10px;border:2px solid rgba(255,255,255,0.3);
    background:rgba(255,255,255,0.08);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:0.85rem;font-weight:700;cursor:pointer;transition:all 0.2s;
  }
  .mode-btn.active{background:linear-gradient(135deg,#f39c12,#e67e22);border-color:#f39c12;color:#1a0533;}
  .timer-btn{
    padding:8px 16px;border-radius:8px;border:2px solid rgba(255,255,255,0.3);
    background:rgba(255,255,255,0.08);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:0.85rem;font-weight:700;cursor:pointer;transition:all 0.2s;
  }
  .timer-btn.active{background:#27ae60;border-color:#2ecc71;}

  .steal-result{
    background:linear-gradient(135deg,rgba(0,0,0,0.85),rgba(0,0,0,0.7));
    backdrop-filter:blur(4px);border-radius:16px;padding:24px;text-align:center;
    margin-bottom:16px;
  }
</style>
</head>
<body>

<!-- ═══════════════════════ SCREEN: MENU ═══════════════════════ -->
<div id="screen-menu" class="screen active items-center justify-center p-6">
  <div style="max-width:440px;width:100%;" class="anim-slideUp">
    <div class="text-center mb-8">
      <div style="font-size:3.5rem;font-weight:900;background:linear-gradient(135deg,#f39c12,#e74c3c,#9b59b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-1px;">QuizBattle!</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;font-weight:600;margin-top:4px;">Quiz Multiplayer • Kahoot Style</div>
    </div>

    <div class="card p-6 mb-4">
      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Nama Pemain</div>
      <input id="menu-name" class="input-field" placeholder="Masukkan nama kamu..." maxlength="20"/>
    </div>

    <div class="card p-6 mb-4">
      <div style="font-size:1rem;font-weight:800;margin-bottom:16px;">🎮 Buat Room Baru</div>

      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Game Mode</div>
      <div id="game-mode-buttons" style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
        {% for gm in game_modes %}
        <button class="mode-btn {% if loop.first %}active{% endif %}" data-gm="{{ gm }}" onclick="selectGameMode('{{ gm }}')">
          {% if gm == 'Classic' %}🎯 Classic{% elif gm == 'Steal' %}🃏 Steal{% endif %}
        </button>
        {% endfor %}
      </div>

      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Mode Bermain</div>
      <div id="play-mode-buttons" style="display:flex;gap:8px;margin-bottom:16px;">
        <button class="mode-btn active" data-pm="Solo" onclick="selectPlayMode('Solo')">👤 Solo</button>
        <button class="mode-btn" data-pm="Team" onclick="selectPlayMode('Team')">👥 Team</button>
      </div>

      <div id="team-size-section" style="display:none;margin-bottom:16px;">
        <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Ukuran Tim</div>
        <div id="team-size-buttons" style="display:flex;gap:8px;">
          {% for ts in team_sizes %}
          <button class="mode-btn {% if loop.first %}active{% endif %}" data-ts="{{ ts }}" onclick="selectTeamSize({{ ts }})">{{ team_size_labels[ts] }}</button>
          {% endfor %}
        </div>
      </div>

      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Timer Per Soal</div>
      <div id="timer-buttons" style="display:flex;gap:8px;margin-bottom:16px;">
        {% for t in timer_options %}
        <button class="timer-btn {% if t == 30 %}active{% endif %}" data-timer="{{ t }}" onclick="selectTimer({{ t }})">{{ t }}s</button>
        {% endfor %}
      </div>

      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Pilih Kategori</div>
      <select id="menu-mode" class="select-field mb-4">
        {% for mode in modes %}
        <option value="{{ mode }}">{{ mode }}</option>
        {% endfor %}
      </select>
      <button class="btn-primary w-full" onclick="createRoom()">✨ Buat Room</button>
    </div>

    <div class="card p-6">
      <div style="font-size:1rem;font-weight:800;margin-bottom:16px;">🔗 Gabung Room</div>
      <input id="menu-code" class="input-field mb-3" placeholder="Masukkan kode room (5 karakter)..." maxlength="5" style="text-transform:uppercase;"/>
      <button class="btn-secondary w-full" onclick="joinRoom()" style="display:block;">🚀 Gabung Room</button>
    </div>

    <div id="menu-error" style="display:none;background:rgba(231,76,60,0.3);border:1px solid #e74c3c;border-radius:10px;padding:12px;margin-top:12px;text-align:center;font-weight:700;font-size:0.9rem;" class="anim-shake"></div>

    <div style="margin-top:16px;padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;font-size:0.8rem;color:rgba(255,255,255,0.5);line-height:1.5;">
      <b style="color:#f39c12;">🎯 Classic:</b> Soal sama untuk semua, siapa cepat dia dapat.<br/>
      <b style="color:#9b59b6;">🃏 Steal:</b> Soal sendiri-sendiri, jawab benar = ambil kartu (2x -90, 2x +50, 1x swap). Tidak perlu nunggu lawan!<br/>
      <b style="color:#2980b9;">👤 Solo:</b> Setiap pemain untuk diri sendiri. Maks {{ max_players }} pemain.<br/>
      <b style="color:#e67e22;">👥 Team:</b> Dibagi 2 tim (1v1, 2v2, 3v3), skor tim digabung!</b>
    </div>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: LOBBY ═══════════════════════ -->
<div id="screen-lobby" class="screen items-center justify-center p-6">
  <div style="max-width:480px;width:100%;" class="anim-slideUp">
    <div class="text-center mb-6">
      <div style="font-size:1.5rem;font-weight:900;margin-bottom:4px;">🎮 Ruang Tunggu</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.85rem;" id="lobby-mode-display"></div>
    </div>

    <div class="card p-6 mb-5 text-center">
      <div style="font-size:0.85rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">Kode Room</div>
      <div class="room-code anim-pulse" id="lobby-code">-----</div>
      <div style="font-size:0.8rem;color:rgba(255,255,255,0.5);margin-top:8px;">Bagikan kode ini ke temanmu!</div>
      <button onclick="copyCode()" class="btn-secondary mt-3" style="font-size:0.85rem;padding:8px 20px;">📋 Salin Kode</button>
    </div>

    <div class="mb-5">
      <div style="font-size:0.85rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;" id="lobby-player-count">Pemain (0/6)</div>
      <div id="lobby-players" style="display:flex;flex-direction:column;gap:10px;"></div>
    </div>

    <div id="lobby-waiting" class="text-center mb-4" style="color:rgba(255,255,255,0.6);font-size:0.9rem;font-weight:600;">
      <div class="anim-pulse">⏳ Menunggu pemain lain bergabung...</div>
    </div>

    <div id="lobby-start-section" style="display:none;">
      <button class="btn-primary w-full" onclick="startGame()" id="btn-start">⚡ MULAI PERMAINAN!</button>
    </div>

    <button onclick="leaveRoom()" class="btn-secondary w-full mt-3" style="font-size:0.85rem;">← Keluar Room</button>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: GAME ═══════════════════════ -->
<div id="screen-game" class="screen" style="flex-direction:column;">
  <div class="scoreboard" id="scoreboard"></div>

  <div style="flex:1;overflow-y:auto;padding:16px;" id="game-content">
    <div class="timer-bar-container mb-3">
      <div class="timer-bar" id="timer-bar" style="width:100%;"></div>
    </div>

    <div class="question-card mb-4 anim-popIn" id="question-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
        <div style="flex:1;">
          <div class="q-number-pill" id="q-number">Soal 1/10</div>
          <div class="q-text" id="q-text">Loading...</div>
        </div>
        <div class="circular-timer" id="circular-timer">
          <svg width="72" height="72" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(0,0,0,0.1)" stroke-width="8"/>
            <circle id="timer-circle" cx="50" cy="50" r="45" fill="none" stroke="#27ae60"
              stroke-width="8" stroke-linecap="round"
              stroke-dasharray="283" stroke-dashoffset="0"
              style="transition:stroke-dashoffset 1s linear,stroke 1s linear;"/>
          </svg>
          <div class="circular-timer-num" id="timer-num">30</div>
        </div>
      </div>
    </div>

    <div id="opponent-answered-badge" style="display:none;margin-bottom:10px;">
      <span class="opponent-badge">Lawan sudah menjawab! ⚡</span>
    </div>

    <div id="answer-buttons" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"></div>

    <!-- Steal mode result (personal) -->
    <div id="steal-result-section" style="display:none;">
      <div class="steal-result anim-bounceIn" id="steal-result-box">
        <div id="steal-result-icon" style="font-size:3rem;margin-bottom:8px;"></div>
        <div id="steal-result-text" style="font-size:1.3rem;font-weight:900;margin-bottom:4px;"></div>
        <div id="steal-result-detail" style="font-size:1rem;font-weight:700;"></div>
      </div>
    </div>

    <!-- Card pick section (Steal mode) -->
    <div id="card-pick-section" style="display:none;">
      <div class="card p-4 mb-4 anim-bounceIn" style="text-align:center;">
        <div style="font-size:1.3rem;font-weight:900;margin-bottom:4px;">🃏 Pilih 1 Kartu!</div>
        <div style="font-size:0.85rem;color:rgba(255,255,255,0.6);">Kamu jawab benar! Ambil 1 dari 5 kartu.</div>
      </div>
      <div class="card-grid" id="card-grid"></div>
      <div id="card-reveal" style="display:none;text-align:center;padding:16px 0;">
        <div id="card-reveal-icon" style="font-size:4rem;" class="anim-bounceIn"></div>
        <div id="card-reveal-label" style="font-size:1.5rem;font-weight:900;margin-top:8px;" class="anim-bounceIn"></div>
      </div>
    </div>

    <div id="waiting-opponent" style="display:none;text-align:center;padding:16px 0;color:rgba(255,255,255,0.7);font-weight:700;">
      <div class="anim-pulse">⏳ Menunggu lawan...</div>
    </div>

    <div id="player-finished-section" style="display:none;text-align:center;padding:32px 16px;">
      <div style="font-size:4rem;margin-bottom:12px;">✅</div>
      <div style="font-size:1.5rem;font-weight:900;margin-bottom:8px;">Kamu Selesai!</div>
      <div style="color:rgba(255,255,255,0.7);font-size:0.95rem;" class="anim-pulse" id="finished-waiting-text">Menunggu pemain lain selesai...</div>
    </div>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: RESULT ═══════════════════════ -->
<div id="screen-result" class="screen" style="flex-direction:column;">
  <div class="scoreboard" id="scoreboard-result"></div>

  <div style="flex:1;overflow-y:auto;padding:16px;" id="result-content">
    <div class="result-feedback mb-4 anim-popIn" id="round-feedback">
      <div id="result-icon" style="font-size:3rem;margin-bottom:8px;"></div>
      <div id="result-text" style="font-size:1.3rem;font-weight:900;margin-bottom:4px;"></div>
      <div id="result-delta" style="font-size:1.1rem;font-weight:700;"></div>
    </div>

    <div id="result-answers" style="display:flex;flex-direction:column;gap:8px;"></div>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: FINAL ═══════════════════════ -->
<div id="screen-final" class="screen items-center justify-center p-6">
  <div style="max-width:500px;width:100%;text-align:center;" class="anim-bounceIn">
    <div id="final-title" style="font-size:2.5rem;font-weight:900;margin-bottom:6px;"></div>
    <div id="final-subtitle" style="font-size:1rem;color:rgba(255,255,255,0.7);margin-bottom:24px;"></div>

    <div id="final-team-rankings" style="display:none;margin-bottom:20px;"></div>

    <div style="font-size:0.85rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;text-align:left;">Individual Rankings</div>
    <div id="final-rankings" style="display:flex;flex-direction:column;gap:10px;margin-bottom:24px;"></div>

    <button class="btn-primary" onclick="goHome()" style="font-size:1rem;">🏠 Kembali ke Menu</button>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: DISCONNECTED ═══════════════════════ -->
<div id="screen-disconnected" class="screen items-center justify-center p-6">
  <div style="max-width:400px;width:100%;text-align:center;" class="anim-bounceIn">
    <div style="font-size:5rem;margin-bottom:16px;">🏳️</div>
    <div style="font-size:2rem;font-weight:900;margin-bottom:8px;">Permainan Berakhir</div>
    <div style="font-size:1.1rem;color:rgba(255,255,255,0.7);margin-bottom:24px;" id="disconnected-reason">Seorang pemain keluar dari pertandingan</div>

    <div id="disconnected-scores" class="card p-4 mb-6" style="display:flex;justify-content:space-around;flex-wrap:wrap;gap:12px;"></div>

    <button class="btn-primary" onclick="goHome()">🏠 Kembali ke Menu</button>
  </div>
</div>

<!-- ═══════════════════════ CHAT PANEL ═══════════════════════ -->
<div id="chat-panel" class="chat-panel">
  <div style="padding:14px 16px;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;">
    <div style="font-weight:800;font-size:1rem;">💬 Chat</div>
    <button onclick="toggleChat()" style="background:none;border:none;color:#fff;font-size:1.5rem;cursor:pointer;">×</button>
  </div>
  <div class="chat-messages" id="chat-messages"></div>
  <div class="chat-input-row">
    <input id="chat-input" class="chat-input" placeholder="Ketik pesan..." maxlength="200" onkeydown="if(event.key==='Enter')sendChat()"/>
    <button class="chat-send-btn" onclick="sendChat()">➤</button>
  </div>
</div>

<button class="chat-toggle-btn" id="chat-toggle-btn" onclick="toggleChat()">
  💬<span class="chat-badge" id="chat-badge">0</span>
</button>

<button class="voice-btn" id="voice-btn" onclick="toggleVoice()" title="Voice Chat">
  🎤
</button>

<script>
// ═══════════════════════ GLOBALS ═══════════════════════
const socket = io();
let myPlayerId = localStorage.getItem('playerId') || null;
let myName = '';
let myRoomCode = localStorage.getItem('roomCode') || null;
let isHost = false;
let currentRoom = null;
let timerInterval = null;
let timerSeconds = 30;
let timerDuration = 30;
let myAnswerThisRound = null;
let gameState = 'menu';
let answeredThisRound = false;
let selectedGameMode = 'Classic';
let selectedPlayMode = 'Solo';
let selectedTeamSize = 1;
let selectedTimer = 30;
let myCorrectIdx = null;
let currentGameMode = 'Classic';
let chatOpen = false;
let unreadChat = 0;
let cardDeck = [];
let cardPicked = false;
let currentPlayers = [];
let myTeam = null;

const TEAM_NAMES = {'A': 'Tim Alpha', 'B': 'Tim Bravo'};
const TEAM_COLORS = {'A': '#2980b9', 'B': '#e67e22'};

// Voice
let localStream = null;
let peerConnection = null;
let voiceActive = false;
let voiceMuted = false;
const rtcConfig = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// ═══════════════════════ UTIL ═══════════════════════
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  gameState = id.replace('screen-', '');
  updateFloatingButtons();
}

function updateFloatingButtons() {
  const chatBtn = document.getElementById('chat-toggle-btn');
  const voiceBtn = document.getElementById('voice-btn');
  const showBtns = ['lobby', 'game', 'result', 'finished'].includes(gameState);
  if (showBtns) {
    chatBtn.classList.add('show');
    voiceBtn.classList.add('show');
  } else {
    chatBtn.classList.remove('show');
    voiceBtn.classList.remove('show');
  }
}

function showMenuError(msg) {
  const el = document.getElementById('menu-error');
  el.textContent = msg;
  el.style.display = 'block';
  el.classList.remove('anim-shake');
  void el.offsetWidth;
  el.classList.add('anim-shake');
  setTimeout(() => { el.style.display = 'none'; }, 4000);
}

function generatePlayerId() {
  return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
}

function getOrCreatePlayerId() {
  if (!myPlayerId) {
    myPlayerId = generatePlayerId();
    localStorage.setItem('playerId', myPlayerId);
  }
  return myPlayerId;
}

function copyCode() {
  const code = document.getElementById('lobby-code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = event.target;
    btn.textContent = '✅ Tersalin!';
    setTimeout(() => { btn.textContent = '📋 Salin Kode'; }, 2000);
  });
}

function selectGameMode(gm) {
  selectedGameMode = gm;
  document.querySelectorAll('#game-mode-buttons .mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.gm === gm);
  });
}

function selectPlayMode(pm) {
  selectedPlayMode = pm;
  document.querySelectorAll('#play-mode-buttons .mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.pm === pm);
  });
  document.getElementById('team-size-section').style.display = (pm === 'Team') ? 'block' : 'none';
}

function selectTeamSize(ts) {
  selectedTeamSize = ts;
  document.querySelectorAll('#team-size-buttons .mode-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.ts) === ts);
  });
}

function selectTimer(t) {
  selectedTimer = t;
  document.querySelectorAll('.timer-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.timer) === t);
  });
}

// ═══════════════════════ TIMER ═══════════════════════
function startTimer(seconds) {
  clearInterval(timerInterval);
  timerSeconds = seconds;
  timerDuration = seconds;
  updateTimerDisplay(timerSeconds);
  timerInterval = setInterval(() => {
    timerSeconds--;
    if (timerSeconds <= 0) {
      timerSeconds = 0;
      clearInterval(timerInterval);
    }
    updateTimerDisplay(timerSeconds);
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
}

function updateTimerDisplay(secs) {
  const pct = timerDuration > 0 ? secs / timerDuration : 0;
  const bar = document.getElementById('timer-bar');
  const numEl = document.getElementById('timer-num');
  const circle = document.getElementById('timer-circle');

  if (bar) {
    bar.style.width = (pct * 100) + '%';
    if (pct > 0.6) bar.style.background = '#27ae60';
    else if (pct > 0.3) bar.style.background = '#f39c12';
    else bar.style.background = '#e74c3c';
  }
  if (numEl) numEl.textContent = secs;
  if (circle) {
    const dashOffset = (1 - pct) * 283;
    circle.style.strokeDashoffset = dashOffset;
    if (pct > 0.6) circle.style.stroke = '#27ae60';
    else if (pct > 0.3) circle.style.stroke = '#f39c12';
    else circle.style.stroke = '#e74c3c';
  }
}

// ═══════════════════════ SCOREBOARD ═══════════════════════
function renderScoreboard(containerId, players) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  // Top points badge
  if (players.length >= 2) {
    const topPlayer = players.reduce((a, b) => a.score >= b.score ? a : b);
    const badge = document.createElement('div');
    badge.className = 'top-points-badge';
    badge.textContent = '👑 ' + topPlayer.score + ' (' + topPlayer.name + ')';
    container.appendChild(badge);
  }

  players.forEach(p => {
    const div = document.createElement('div');
    const isMe = p.id === myPlayerId;
    const teamClass = p.team ? 'team-' + p.team : '';
    div.className = 'sb-player ' + teamClass + (isMe ? ' me' : '');
    let html = '<div class="sb-name">' + escapeHtml(p.name) + '</div>';
    html += '<div class="sb-val">' + p.score + '</div>';
    if (p.team) {
      html += '<div class="sb-team-tag ' + p.team + '">' + (p.team === 'A' ? 'Alpha' : 'Bravo') + '</div>';
    }
    if (p.finished) {
      html += '<div class="sb-finished">✅ Selesai</div>';
    }
    div.innerHTML = html;
    container.appendChild(div);
  });
}

function updateScoreboardFromPlayers(players) {
  currentPlayers = players;
  renderScoreboard('scoreboard', players);
  renderScoreboard('scoreboard-result', players);
}

// ═══════════════════════ LOBBY ═══════════════════════
function updateLobbyUI(roomInfo) {
  document.getElementById('lobby-code').textContent = roomInfo.code;
  let modeText = '📚 ' + roomInfo.mode + ' • ' + roomInfo.game_mode;
  if (roomInfo.play_mode === 'Team') {
    modeText += ' • 👥 Team (' + (roomInfo.team_size || 1) + 'v' + (roomInfo.team_size || 1) + ')';
  } else {
    modeText += ' • 👤 Solo';
  }
  document.getElementById('lobby-mode-display').textContent = modeText;
  const maxP = roomInfo.max_players || 6;
  const container = document.getElementById('lobby-players');
  container.innerHTML = '';

  const slots = [];
  for (let i = 0; i < maxP; i++) slots.push({});
  roomInfo.players.forEach((p, i) => { slots[i] = p; });

  slots.forEach((p, i) => {
    const div = document.createElement('div');
    const teamClass = p.team ? 'team-' + p.team : '';
    div.className = 'player-slot ' + teamClass + (p.name ? ' filled' : '');
    if (p.name) {
      const initials = p.name.substr(0, 2).toUpperCase();
      const isMe = p.id === myPlayerId;
      const hostBadge = p.is_host ? '<span style="background:#f39c12;color:#000;font-size:0.65rem;font-weight:800;padding:2px 6px;border-radius:8px;margin-left:4px;">HOST</span>' : '';
      const meBadge = isMe ? '<span style="background:rgba(255,255,255,0.2);font-size:0.65rem;font-weight:800;padding:2px 6px;border-radius:8px;margin-left:4px;">KAMU</span>' : '';
      const teamBadge = p.team ? '<span style="font-size:0.65rem;font-weight:800;padding:2px 6px;border-radius:8px;margin-left:4px;background:' + TEAM_COLORS[p.team] + ';">' + (p.team === 'A' ? 'Alpha' : 'Bravo') + '</span>' : '';
      div.innerHTML = `
        <div class="player-avatar">${initials}</div>
        <div>
          <div style="font-weight:800;font-size:0.95rem;">${escapeHtml(p.name)}${hostBadge}${meBadge}${teamBadge}</div>
          <div style="font-size:0.75rem;color:rgba(255,255,255,0.5);">Siap bermain</div>
        </div>`;
    } else {
      div.innerHTML = `
        <div class="player-avatar" style="background:rgba(255,255,255,0.1);">?</div>
        <div style="color:rgba(255,255,255,0.4);font-weight:700;font-size:0.9rem;">Menunggu pemain ${i+1}...</div>`;
    }
    container.appendChild(div);
  });

  const count = roomInfo.players.length;
  document.getElementById('lobby-player-count').textContent = `Pemain (${count}/${maxP})`;

  const startSection = document.getElementById('lobby-start-section');
  const waitingEl = document.getElementById('lobby-waiting');
  if (count >= 2 && isHost) {
    startSection.style.display = 'block';
    waitingEl.style.display = 'none';
  } else if (count >= 2 && !isHost) {
    waitingEl.innerHTML = '<div class="anim-pulse">✅ Menunggu host memulai permainan...</div>';
    startSection.style.display = 'none';
    waitingEl.style.display = 'block';
  } else {
    startSection.style.display = 'none';
    waitingEl.style.display = 'block';
    waitingEl.innerHTML = '<div class="anim-pulse">⏳ Menunggu pemain lain bergabug...</div>';
  }

  // Store my team
  const me = roomInfo.players.find(p => p.id === myPlayerId);
  if (me) myTeam = me.team;
}

// ═══════════════════════ QUESTION ═══════════════════════
function renderQuestion(data, remainingTime) {
  showScreen('screen-game');
  answeredThisRound = false;
  myAnswerThisRound = null;
  cardPicked = false;
  currentGameMode = data.game_mode || 'Classic';
  myCorrectIdx = data.my_correct_idx !== undefined ? data.my_correct_idx : null;

  document.getElementById('card-pick-section').style.display = 'none';
  document.getElementById('card-reveal').style.display = 'none';
  document.getElementById('opponent-answered-badge').style.display = 'none';
  document.getElementById('waiting-opponent').style.display = 'none';
  document.getElementById('steal-result-section').style.display = 'none';
  document.getElementById('player-finished-section').style.display = 'none';

  document.getElementById('q-number').textContent = `Soal ${data.current_q + 1}/${data.total_q}`;
  document.getElementById('q-text').textContent = data.question;

  const numOpts = data.num_opts || data.opts.length;
  const colors = ['btn-a', 'btn-b', 'btn-c', 'btn-d'];
  const shapes = ['▲', '◆', '●', '■'];

  const container = document.getElementById('answer-buttons');
  container.innerHTML = '';
  container.style.display = 'grid';
  container.style.gridTemplateColumns = numOpts === 2 ? '1fr' : '1fr 1fr';

  for (let i = 0; i < numOpts; i++) {
    const btn = document.createElement('button');
    btn.className = `btn-answer ${colors[i]} anim-popIn`;
    btn.style.animationDelay = (i * 0.08) + 's';
    btn.dataset.idx = i;
    btn.innerHTML = `<span style="font-size:1.3rem;opacity:0.8;">${shapes[i]}</span><span style="flex:1;">${escapeHtml(data.opts[i])}</span>`;
    btn.onclick = () => submitAnswer(i);
    container.appendChild(btn);
  }

  const qcard = document.getElementById('question-card');
  qcard.classList.remove('anim-popIn');
  void qcard.offsetWidth;
  qcard.classList.add('anim-popIn');

  startTimer(remainingTime !== undefined ? remainingTime : (data.timer_duration || 30));
}

function submitAnswer(idx) {
  if (answeredThisRound) return;
  answeredThisRound = true;
  myAnswerThisRound = idx;

  const btns = document.querySelectorAll('.btn-answer');
  btns.forEach((b, i) => {
    b.disabled = true;
    if (i === idx) {
      b.style.transform = 'scale(0.95)';
      b.style.filter = 'brightness(1.3)';
      b.style.boxShadow = '0 0 20px rgba(255,255,255,0.5)';
    } else {
      b.style.opacity = '0.4';
    }
  });

  stopTimer();

  if (currentGameMode === 'Steal') {
    // In steal mode, don't show waiting - server will respond with result or card_pick
  } else {
    document.getElementById('waiting-opponent').style.display = 'block';
  }

  socket.emit('submit_answer', {
    code: myRoomCode,
    answer: idx,
  });
}

// ═══════════════════════ CARD PICK (Steal Mode) ═══════════════════════
function showCardPick(cards) {
  cardDeck = cards;
  cardPicked = false;
  document.getElementById('answer-buttons').style.display = 'none';
  document.getElementById('waiting-opponent').style.display = 'none';
  document.getElementById('steal-result-section').style.display = 'none';
  document.getElementById('card-reveal').style.display = 'none';

  const section = document.getElementById('card-pick-section');
  section.style.display = 'block';

  const grid = document.getElementById('card-grid');
  grid.innerHTML = '';
  grid.style.display = 'grid';

  cards.forEach((card, i) => {
    const div = document.createElement('div');
    div.className = 'pick-card anim-popIn';
    div.style.animationDelay = (i * 0.1) + 's';
    div.dataset.idx = i;
    div.innerHTML = `
      <div class="card-back">❓</div>
      <div class="card-front">
        <div style="font-size:2.5rem;">${card.icon}</div>
        <div class="card-front-label">${card.label}</div>
      </div>`;
    div.onclick = () => pickCard(i);
    grid.appendChild(div);
  });
}

function pickCard(idx) {
  if (cardPicked) return;
  cardPicked = true;

  socket.emit('pick_card', {
    code: myRoomCode,
    card_idx: idx,
  });
}

function showStealResult(correct, timedOut) {
  document.getElementById('answer-buttons').style.display = 'none';
  document.getElementById('card-pick-section').style.display = 'none';
  const section = document.getElementById('steal-result-section');
  section.style.display = 'block';

  if (timedOut) {
    document.getElementById('steal-result-icon').textContent = '⏰';
    document.getElementById('steal-result-text').textContent = 'Waktu Habis!';
    document.getElementById('steal-result-text').style.color = '#e74c3c';
    document.getElementById('steal-result-detail').textContent = 'Tidak dapat kartu. Lanjut ke soal berikutnya...';
    document.getElementById('steal-result-detail').style.color = '#e74c3c';
  } else {
    document.getElementById('steal-result-icon').textContent = '😔';
    document.getElementById('steal-result-text').textContent = 'Salah!';
    document.getElementById('steal-result-text').style.color = '#e74c3c';
    document.getElementById('steal-result-detail').textContent = 'Tidak dapat kartu. Lanjut ke soal berikutnya...';
    document.getElementById('steal-result-detail').style.color = '#e74c3c';
  }
}

// ═══════════════════════ ROUND RESULT (Classic/Team) ═══════════════════════
function showRoundResult(data) {
  showScreen('screen-result');
  stopTimer();

  const myPl = data.players.find(p => p.id === myPlayerId);

  if (myPl) {
    if (myPl.delta > 0) {
      document.getElementById('result-icon').textContent = '🎉';
      document.getElementById('result-text').textContent = 'Benar!';
      document.getElementById('result-text').style.color = '#2ecc71';
      document.getElementById('result-delta').textContent = '+' + myPl.delta + ' poin';
      document.getElementById('result-delta').style.color = '#2ecc71';
    } else if (myPl.answer === -1) {
      document.getElementById('result-icon').textContent = '⏰';
      document.getElementById('result-text').textContent = 'Waktu Habis!';
      document.getElementById('result-text').style.color = '#e74c3c';
      document.getElementById('result-delta').textContent = myPl.delta + ' poin';
      document.getElementById('result-delta').style.color = '#e74c3c';
    } else {
      document.getElementById('result-icon').textContent = '😔';
      document.getElementById('result-text').textContent = 'Salah!';
      document.getElementById('result-text').style.color = '#e74c3c';
      document.getElementById('result-delta').textContent = myPl.delta + ' poin';
      document.getElementById('result-delta').style.color = '#e74c3c';
    }
  }

  // Show answer options
  if (data.opts) {
    const container = document.getElementById('result-answers');
    container.innerHTML = '';
    container.style.gridTemplateColumns = data.opts.length === 2 ? '1fr' : '1fr 1fr';
    container.style.display = 'grid';
    container.style.gap = '8px';

    const colors = ['btn-a', 'btn-b', 'btn-c', 'btn-d'];
    const shapes = ['▲', '◆', '●', '■'];

    data.opts.forEach((opt, i) => {
      const div = document.createElement('div');
      div.className = `btn-answer ${colors[i]}`;
      div.style.cursor = 'default';
      div.innerHTML = `<span style="font-size:1.3rem;opacity:0.8;">${shapes[i]}</span><span style="flex:1;">${escapeHtml(opt)}</span>`;

      if (i === data.correct_idx) {
        div.classList.add('correct');
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:absolute;top:6px;right:10px;font-size:1.3rem;';
        overlay.textContent = '✓';
        div.appendChild(overlay);
      }
      if (myPl && myPl.answer === i && i !== data.correct_idx) {
        div.classList.add('wrong');
        div.style.opacity = '0.75';
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:absolute;top:6px;right:10px;font-size:1.3rem;';
        overlay.textContent = '✗';
        div.appendChild(overlay);
      }
      container.appendChild(div);
    });
  } else {
    document.getElementById('result-answers').innerHTML = '';
  }
}

// ═══════════════════════ FINAL RESULT ═══════════════════════
function showFinalResult(data) {
  showScreen('screen-final');
  stopTimer();

  const rankings = data.rankings || [];
  const gameMode = data.game_mode || 'Classic';
  const playMode = data.play_mode || 'Solo';
  const me = rankings.find(p => p.id === myPlayerId);
  const myRank = rankings.findIndex(p => p.id === myPlayerId);

  let title, subtitle;
  if (rankings.length === 1) {
    title = '🏆 Selesai!';
    subtitle = 'Permainan berakhir';
  } else if (rankings[0].score === rankings[1].score) {
    title = '🤝 SERI!';
    subtitle = 'Pertandingan berakhir imbang!';
  } else if (playMode === 'Team' && data.team_rankings) {
    const myTeam = me ? me.team : null;
    const winningTeam = data.team_rankings[0];
    if (myTeam === winningTeam.team) {
      title = '🏆 TIM KAMU MENANG!';
      subtitle = winningTeam.name + ' memenangkan pertandingan!';
    } else {
      title = '😔 TIM KAMU KALAH';
      subtitle = winningTeam.name + ' memenangkan pertandingan.';
    }
  } else if (myRank === 0) {
    title = '🏆 MENANG!';
    subtitle = 'Kamu adalah pemenang!';
  } else {
    title = '😔 KALAH';
    subtitle = 'Lebih semangat lain kali!';
  }

  document.getElementById('final-title').textContent = title;
  document.getElementById('final-subtitle').textContent = subtitle;

  // Team rankings
  const teamContainer = document.getElementById('final-team-rankings');
  if (playMode === 'Team' && data.team_rankings) {
    teamContainer.style.display = 'block';
    teamContainer.innerHTML = '';
    data.team_rankings.forEach((t, i) => {
      const isMyTeam = me && me.team === t.team;
      const div = document.createElement('div');
      div.className = 'card anim-slideUp';
      div.style.cssText = `padding:16px 20px;margin-bottom:10px;border:2px solid ${TEAM_COLORS[t.team]};${isMyTeam ? 'box-shadow:0 0 20px ' + TEAM_COLORS[t.team] + '44;' : ''}`;
      div.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-size:1.2rem;font-weight:900;color:${TEAM_COLORS[t.team]};">${i === 0 ? '👑' : '🥈'} ${t.name}</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.6);">${t.members.map(m => m.name).join(', ')}</div>
          </div>
          <div style="font-size:2rem;font-weight:900;color:${i === 0 ? '#f39c12' : 'rgba(255,255,255,0.7)'};">${t.score}</div>
        </div>`;
      teamContainer.appendChild(div);
    });
  } else {
    teamContainer.style.display = 'none';
  }

  // Individual rankings
  const container = document.getElementById('final-rankings');
  container.innerHTML = '';
  const medals = ['👑', '🥈', '🥉'];

  rankings.forEach((p, i) => {
    const isMe = p.id === myPlayerId;
    const div = document.createElement('div');
    div.className = 'card anim-slideUp';
    div.style.cssText = `padding:14px 20px;display:flex;align-items:center;gap:14px;animation-delay:${i*0.1}s;${isMe ? 'border:2px solid #f39c12;' : ''}`;
    const teamTag = p.team ? ` <span style="font-size:0.7rem;background:${TEAM_COLORS[p.team]};padding:2px 8px;border-radius:8px;font-weight:800;">${p.team === 'A' ? 'Alpha' : 'Bravo'}</span>` : '';
    div.innerHTML = `
      <div style="font-size:2rem;">${medals[i] || '🎖️'}</div>
      <div style="flex:1;">
        <div style="font-weight:800;font-size:1rem;">${escapeHtml(p.name)}${isMe ? ' <span style="font-size:0.7rem;background:#f39c12;color:#000;padding:2px 8px;border-radius:8px;font-weight:800;">KAMU</span>' : ''}${teamTag}</div>
      </div>
      <div style="font-size:1.6rem;font-weight:900;color:${i===0?'#f39c12':'rgba(255,255,255,0.7)'};">${p.score}</div>`;
    container.appendChild(div);
  });
}

// ═══════════════════════ NAVIGATION ═══════════════════════
function createRoom() {
  const name = document.getElementById('menu-name').value.trim();
  if (!name) { showMenuError('Masukkan nama kamu dulu!'); return; }
  const mode = document.getElementById('menu-mode').value;
  myName = name;
  socket.emit('create_room', {
    name: name,
    mode: mode,
    game_mode: selectedGameMode,
    play_mode: selectedPlayMode,
    team_size: selectedTeamSize,
    timer_duration: selectedTimer,
    player_id: getOrCreatePlayerId(),
  });
}

function joinRoom() {
  const name = document.getElementById('menu-name').value.trim();
  const code = document.getElementById('menu-code').value.trim().toUpperCase();
  if (!name) { showMenuError('Masukkan nama kamu dulu!'); return; }
  if (!code || code.length !== 5) { showMenuError('Masukkan kode room yang valid (5 karakter)!'); return; }
  myName = name;
  socket.emit('join_room_req', {
    name: name,
    code: code,
    player_id: getOrCreatePlayerId(),
  });
}

function startGame() {
  document.getElementById('btn-start').disabled = true;
  socket.emit('start_game', { code: myRoomCode });
}

function leaveRoom() {
  socket.emit('leave_room', { code: myRoomCode });
  myRoomCode = null;
  localStorage.removeItem('roomCode');
  cleanupVoice();
  showScreen('screen-menu');
}

function goHome() {
  myRoomCode = null;
  localStorage.removeItem('roomCode');
  cleanupVoice();
  showScreen('screen-menu');
  if (myName) document.getElementById('menu-name').value = myName;
}

// ═══════════════════════ CHAT ═══════════════════════
function toggleChat() {
  const panel = document.getElementById('chat-panel');
  chatOpen = !chatOpen;
  if (chatOpen) {
    panel.classList.add('open');
    unreadChat = 0;
    updateChatBadge();
  } else {
    panel.classList.remove('open');
  }
}

function updateChatBadge() {
  const badge = document.getElementById('chat-badge');
  if (unreadChat > 0) {
    badge.textContent = unreadChat;
    badge.classList.add('show');
  } else {
    badge.classList.remove('show');
  }
}

function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  socket.emit('send_chat', { code: myRoomCode, msg: msg });
  input.value = '';
}

function addChatMessage(data) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  const isMe = data.id === myPlayerId;
  div.className = 'chat-bubble ' + (isMe ? 'me' : 'opp');
  div.innerHTML = `<div class="chat-name">${escapeHtml(data.name)}</div>${escapeHtml(data.msg)}`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;

  if (!chatOpen && !isMe) {
    unreadChat++;
    updateChatBadge();
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ═══════════════════════ VOICE CHAT (WebRTC) ═══════════════════════
async function toggleVoice() {
  if (!voiceActive) {
    await startVoice();
  } else {
    if (voiceMuted) {
      unmuteVoice();
    } else {
      muteVoice();
    }
  }
}

async function startVoice() {
  try {
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    voiceActive = true;
    voiceMuted = false;
    updateVoiceButton();
    socket.emit('voice_start', { code: myRoomCode });
    await createPeerConnection(true);
  } catch (err) {
    console.error('Voice error:', err);
    alert('Tidak bisa mengakses mikrofon. Pastikan izin diberikan.');
    voiceActive = false;
    updateVoiceButton();
  }
}

async function createPeerConnection(isInitiator) {
  if (peerConnection) {
    try { peerConnection.close(); } catch(e) {}
    peerConnection = null;
  }

  peerConnection = new RTCPeerConnection(rtcConfig);

  if (localStream) {
    localStream.getTracks().forEach(track => {
      peerConnection.addTrack(track, localStream);
    });
  }

  peerConnection.ontrack = (event) => {
    const audio = document.getElementById('remote-audio') || createRemoteAudio();
    audio.srcObject = event.streams[0];
    audio.play().catch(() => {});
  };

  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      socket.emit('voice_ice', { code: myRoomCode, candidate: event.candidate });
    }
  };

  if (isInitiator) {
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    socket.emit('voice_offer', { code: myRoomCode, sdp: offer });
  }
}

function createRemoteAudio() {
  const audio = document.createElement('audio');
  audio.id = 'remote-audio';
  audio.autoplay = true;
  audio.style.display = 'none';
  document.body.appendChild(audio);
  return audio;
}

function muteVoice() {
  voiceMuted = true;
  if (localStream) {
    localStream.getAudioTracks().forEach(track => track.enabled = false);
  }
  updateVoiceButton();
}

function unmuteVoice() {
  voiceMuted = false;
  if (localStream) {
    localStream.getAudioTracks().forEach(track => track.enabled = true);
  }
  updateVoiceButton();
}

function updateVoiceButton() {
  const btn = document.getElementById('voice-btn');
  btn.classList.remove('active', 'muted');
  if (voiceActive) {
    btn.classList.add('active');
    if (voiceMuted) {
      btn.classList.add('muted');
      btn.textContent = '🔇';
    } else {
      btn.textContent = '🎤';
    }
  } else {
    btn.textContent = '🎤';
  }
}

function cleanupVoice() {
  if (localStream) {
    localStream.getTracks().forEach(track => track.stop());
    localStream = null;
  }
  if (peerConnection) {
    try { peerConnection.close(); } catch(e) {}
    peerConnection = null;
  }
  voiceActive = false;
  voiceMuted = false;
  updateVoiceButton();
}

// ═══════════════════════ SOCKET EVENTS ═══════════════════════
socket.on('connect', () => {
  if (myPlayerId && myRoomCode) {
    socket.emit('restore_session', {
      player_id: myPlayerId,
      room_code: myRoomCode,
    });
  }
});

socket.on('restore_failed', (data) => {
  myRoomCode = null;
  localStorage.removeItem('roomCode');
});

socket.on('session_restored', (data) => {
  myPlayerId = data.player_id;
  myName = data.name;
  myRoomCode = data.room_code;
  isHost = data.is_host;
  localStorage.setItem('playerId', myPlayerId);
  localStorage.setItem('roomCode', myRoomCode);

  if (data.room_info) {
    updateScoreboardFromPlayers(data.room_info.players);
  }

  const state = data.state;
  if (state === 'lobby') {
    showScreen('screen-lobby');
    updateLobbyUI(data.room_info);
  } else if (state === 'question' && data.question_data) {
    const qd = data.question_data;
    currentGameMode = qd.game_mode || 'Classic';
    myCorrectIdx = qd.my_correct_idx !== undefined ? qd.my_correct_idx : null;
    renderQuestion(qd, qd.remaining_time);
    if (qd.already_answered) {
      answeredThisRound = true;
      if (currentGameMode !== 'Steal') {
        document.getElementById('waiting-opponent').style.display = 'block';
      }
      const btns = document.querySelectorAll('.btn-answer');
      btns.forEach(b => { b.disabled = true; b.style.opacity = '0.5'; });
      stopTimer();
    }
  } else if (state === 'finished' && data.rankings) {
    showFinalResult({rankings: data.rankings, game_mode: (data.room_info || {}).game_mode || 'Classic', play_mode: data.play_mode || 'Solo', team_rankings: data.team_rankings});
  }
});

socket.on('room_created', (data) => {
  myPlayerId = data.player_id;
  myName = data.name;
  myRoomCode = data.code;
  isHost = data.is_host;
  localStorage.setItem('playerId', myPlayerId);
  localStorage.setItem('roomCode', myRoomCode);
  showScreen('screen-lobby');
  updateLobbyUI(data.room_info);
});

socket.on('room_joined', (data) => {
  myPlayerId = data.player_id;
  myName = data.name;
  myRoomCode = data.code;
  isHost = data.is_host;
  localStorage.setItem('playerId', myPlayerId);
  localStorage.setItem('roomCode', myRoomCode);
  showScreen('screen-lobby');
  updateLobbyUI(data.room_info);
});

socket.on('room_update', (data) => {
  if (gameState === 'lobby') updateLobbyUI(data);
});

socket.on('join_error', (data) => { showMenuError(data.message); });

socket.on('error_msg', (data) => {
  alert(data.message);
  const btn = document.getElementById('btn-start');
  if (btn) btn.disabled = false;
});

socket.on('new_question', (data) => {
  renderQuestion(data);
});

socket.on('opponent_answered', () => {
  if (!answeredThisRound && currentGameMode !== 'Steal') {
    document.getElementById('opponent-answered-badge').style.display = 'block';
  }
});

socket.on('card_pick', (data) => {
  showCardPick(data.cards);
});

socket.on('card_revealed', (data) => {
  const cards = document.querySelectorAll('.pick-card');
  cards.forEach((c, i) => {
    if (i === data.card_idx) {
      c.classList.add('revealed', data.card.type);
    } else {
      c.classList.add('disabled');
    }
  });
  const reveal = document.getElementById('card-reveal');
  reveal.style.display = 'block';
  document.getElementById('card-reveal-icon').textContent = data.card.icon;
  document.getElementById('card-reveal-label').textContent = data.card.label;
  document.getElementById('card-reveal-label').style.color = data.card.type === 'minus' ? '#e74c3c' : (data.card.type === 'plus' ? '#2ecc71' : '#f39c12');
  document.getElementById('card-grid').style.display = 'none';
});

socket.on('steal_answer_result', (data) => {
  showStealResult(data.correct, data.timed_out);
});

socket.on('score_update', (data) => {
  updateScoreboardFromPlayers(data.players);
});

socket.on('player_finished', (data) => {
  document.getElementById('answer-buttons').style.display = 'none';
  document.getElementById('card-pick-section').style.display = 'none';
  document.getElementById('steal-result-section').style.display = 'none';
  document.getElementById('question-card').style.display = 'none';
  document.getElementById('timer-bar').parentElement.style.display = 'none';
  document.getElementById('player-finished-section').style.display = 'block';
});

socket.on('round_result', (data) => {
  stopTimer();
  updateScoreboardFromPlayers(data.players);
  setTimeout(() => { showRoundResult(data); }, 400);
});

socket.on('game_over', (data) => {
  showFinalResult(data);
  myRoomCode = null;
  localStorage.removeItem('roomCode');
});

socket.on('opponent_disconnected', (data) => {
  stopTimer();
  myRoomCode = null;
  localStorage.removeItem('roomCode');
  cleanupVoice();
  showScreen('screen-disconnected');

  const container = document.getElementById('disconnected-scores');
  container.innerHTML = '';
  data.remaining_players.forEach(p => {
    const div = document.createElement('div');
    div.style.textAlign = 'center';
    div.innerHTML = `<div style="font-size:0.85rem;font-weight:700;opacity:0.7;">${escapeHtml(p.name)}</div><div style="font-size:2rem;font-weight:900;color:#2ecc71;">${p.score}</div>`;
    container.appendChild(div);
  });

  const disconnectedDiv = document.createElement('div');
  disconnectedDiv.style.textAlign = 'center';
  disconnectedDiv.innerHTML = `<div style="font-size:0.85rem;font-weight:700;opacity:0.7;">${escapeHtml(data.disconnected_name)}</div><div style="font-size:2rem;font-weight:900;color:#e74c3c;">🚪</div>`;
  container.appendChild(disconnectedDiv);
});

socket.on('player_left', (data) => {
  // In steal mode, a player left but game continues
  if (data.remaining_players) {
    updateScoreboardFromPlayers(data.remaining_players.map(p => ({...p, id: p.id})));
  }
});

// Chat events
socket.on('chat_message', (data) => { addChatMessage(data); });

// Voice signaling events
socket.on('voice_start', (data) => {
  if (!voiceActive) {
    startVoice().catch(() => {});
  }
});

socket.on('voice_offer', async (data) => {
  if (!voiceActive) {
    await startVoice();
  }
  if (peerConnection) {
    await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    socket.emit('voice_answer', { code: myRoomCode, sdp: answer });
  }
});

socket.on('voice_answer', async (data) => {
  if (peerConnection && peerConnection.signalingState !== 'stable') {
    await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
  }
});

socket.on('voice_ice', async (data) => {
  if (peerConnection) {
    try {
      await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
    } catch (e) {}
  }
});

// Init
(function() {
  const savedName = localStorage.getItem('lastPlayerName');
  if (savedName) document.getElementById('menu-name').value = savedName;

  document.getElementById('menu-name').addEventListener('input', (e) => {
    localStorage.setItem('lastPlayerName', e.target.value);
  });
  document.getElementById('menu-code').addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
  });
  document.getElementById('menu-code').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') joinRoom();
  });
})();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
