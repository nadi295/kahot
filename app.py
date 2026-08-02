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
TIMER_OPTIONS = [15, 30, 60]

# ─── Room State ───────────────────────────────────────────────────────────────

rooms = {}
# rooms[code] = {
#   players: {sid: {name, score, answered, answer, id, card_picked, card_idx, question_idx}},
#   host: sid,
#   mode: str,          # quiz category
#   game_mode: str,     # 'Classic' or 'Steal'
#   timer_duration: int,# seconds per question
#   questions: [...],
#   current_q: int,
#   state: 'lobby'|'question'|'card_pick'|'result'|'finished',
#   timer_greenlet: greenlet or None,
#   q_start_time: float,
#   chat: [{name, msg, ts}],
# }

player_sessions = {}  # player_id -> {room_code, sid}


def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))


def room_summary(code, room, for_sid=None):
    players = room['players']
    p_list = [
        {'name': v['name'], 'score': v['score'], 'id': v['id'],
         'is_host': k == room['host'], 'sid': k}
        for k, v in players.items()
    ]
    return {
        'code': code,
        'mode': room['mode'],
        'game_mode': room.get('game_mode', 'Classic'),
        'players': p_list,
        'state': room['state'],
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
    }


def cancel_timer(room):
    if room.get('timer_greenlet'):
        try:
            room['timer_greenlet'].kill()
        except Exception:
            pass
        room['timer_greenlet'] = None


def start_question_timer(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_timer(room)
    duration = room.get('timer_duration', 30)
    g = eventlet.spawn(question_timer_worker, code, duration)
    room['timer_greenlet'] = g


def question_timer_worker(code, duration):
    eventlet.sleep(duration)
    room = rooms.get(code)
    if not room or room['state'] != 'question':
        return
    for sid, p in room['players'].items():
        if not p['answered']:
            p['answered'] = True
            p['answer'] = -1
    check_round_end(code)


def generate_card_deck():
    """5 cards: 2x -90, 2x +50, 1x swap"""
    cards = [
        {'type': 'minus', 'value': -90, 'label': '-90 Poin', 'icon': '💥'},
        {'type': 'minus', 'value': -90, 'label': '-90 Poin', 'icon': '💥'},
        {'type': 'plus', 'value': 50, 'label': '+50 Poin', 'icon': '⭐'},
        {'type': 'plus', 'value': 50, 'label': '+50 Poin', 'icon': '⭐'},
        {'type': 'swap', 'value': 0, 'label': 'Swap Poin!', 'icon': '🔄'},
    ]
    random.shuffle(cards)
    return cards


# ─── Classic Mode ─────────────────────────────────────────────────────────────

def end_round_classic(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_timer(room)
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

    players = room['players']
    p_list = [
        {
            'name': v['name'], 'score': v['score'],
            'answer': v['answer'], 'delta': score_changes[k],
            'id': v['id'], 'sid': k
        }
        for k, v in players.items()
    ]

    socketio.emit('round_result', {
        'correct_idx': correct_idx,
        'players': p_list,
        'question': q['q'],
        'opts': q['opts'],
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
    }, room=code)

    eventlet.spawn(advance_question_after_delay, code)


# ─── Steal Mode ───────────────────────────────────────────────────────────────

def send_question_steal(code):
    room = rooms.get(code)
    if not room:
        return
    room['state'] = 'question'
    room['q_start_time'] = time.time()

    sids = list(room['players'].keys())
    q = room['questions'][room['current_q']]

    for i, sid in enumerate(sids):
        p = room['players'][sid]
        p['answered'] = False
        p['answer'] = None
        p['card_picked'] = False
        p['card_idx'] = None
        p['card_effect'] = None

    # In steal mode, each player gets their own question
    # Player 1 gets current_q, Player 2 gets current_q+1 (wrapping)
    q1 = room['questions'][room['current_q'] % len(room['questions'])]
    q2 = room['questions'][(room['current_q'] + 1) % len(room['questions'])]

    for i, sid in enumerate(sids):
        player_q = q1 if i == 0 else q2
        room['players'][sid]['question_idx'] = room['current_q'] if i == 0 else (room['current_q'] + 1) % len(room['questions'])
        socketio.emit('new_question', {
            'question': player_q['q'],
            'opts': player_q['opts'],
            'current_q': room['current_q'],
            'total_q': len(room['questions']),
            'num_opts': len(player_q['opts']),
            'game_mode': 'Steal',
            'my_correct_idx': player_q['ans'],
        }, room=sid)

    start_question_timer(code)


def check_round_end(code):
    room = rooms.get(code)
    if not room:
        return
    game_mode = room.get('game_mode', 'Classic')

    if game_mode == 'Classic':
        all_answered = all(p['answered'] for p in room['players'].values())
        if all_answered:
            end_round_classic(code)
    else:
        # Steal mode
        all_done = True
        for sid, p in room['players'].items():
            if not p['answered']:
                all_done = False
                break
            if p['answer'] == p.get('my_correct_idx') and not p['card_picked']:
                all_done = False
                break
        if all_done:
            end_round_steal(code)


def end_round_steal(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_timer(room)
    room['state'] = 'result'

    # Apply card effects
    sids = list(room['players'].keys())
    p1 = room['players'][sids[0]]
    p2 = room['players'][sids[1]]

    # Handle swap: if both picked swap, they cancel out
    p1_swap = p1.get('card_effect') == 'swap'
    p2_swap = p2.get('card_effect') == 'swap'

    if p1_swap and not p2_swap:
        p1['score'], p2['score'] = p2['score'], p1['score']
    elif p2_swap and not p1_swap:
        p1['score'], p2['score'] = p2['score'], p1['score']
    elif p1_swap and p2_swap:
        pass  # both swap = no change

    # Apply plus/minus
    for sid in sids:
        p = room['players'][sid]
        eff = p.get('card_effect')
        if eff == 'plus':
            p['score'] += p.get('card_value', 0)
        elif eff == 'minus':
            p['score'] += p.get('card_value', 0)

    p_list = [
        {
            'name': v['name'], 'score': v['score'],
            'answer': v['answer'], 'delta': 0,
            'id': v['id'], 'sid': k,
            'card_effect': v.get('card_effect'),
            'card_label': v.get('card_label', ''),
            'card_icon': v.get('card_icon', ''),
            'was_correct': v.get('answer') == v.get('my_correct_idx'),
        }
        for k, v in room['players'].items()
    ]

    socketio.emit('round_result', {
        'players': p_list,
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
        'game_mode': 'Steal',
    }, room=code)

    eventlet.spawn(advance_question_after_delay, code)


def advance_question_after_delay(code):
    eventlet.sleep(4.5)
    room = rooms.get(code)
    if not room:
        return
    room['current_q'] += 1
    if room['current_q'] >= len(room['questions']):
        finish_game(code)
    else:
        if room.get('game_mode') == 'Steal':
            send_question_steal(code)
        else:
            send_question(code)


def send_question(code):
    room = rooms.get(code)
    if not room:
        return
    room['state'] = 'question'
    room['q_start_time'] = time.time()
    q = room['questions'][room['current_q']]
    for p in room['players'].values():
        p['answered'] = False
        p['answer'] = None

    socketio.emit('new_question', {
        'question': q['q'],
        'opts': q['opts'],
        'current_q': room['current_q'],
        'total_q': len(room['questions']),
        'num_opts': len(q['opts']),
        'game_mode': room.get('game_mode', 'Classic'),
    }, room=code)
    start_question_timer(code)


def finish_game(code):
    room = rooms.get(code)
    if not room:
        return
    cancel_timer(room)
    room['state'] = 'finished'
    players = room['players']
    p_list = sorted(
        [{'name': v['name'], 'score': v['score'], 'id': v['id']} for v in players.values()],
        key=lambda x: x['score'], reverse=True
    )
    socketio.emit('game_over', {'rankings': p_list}, room=code)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, modes=MODES, game_modes=GAME_MODES, timer_options=TIMER_OPTIONS)


# ─── Socket.IO Handlers ───────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    pass


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    code = None
    room = None
    for c, r in list(rooms.items()):
        if sid in r['players']:
            code = c
            room = r
            break
    if not code or not room:
        return

    disconnected_player = room['players'].get(sid)
    if not disconnected_player:
        return

    pid = disconnected_player['id']
    if pid in player_sessions:
        player_sessions[pid]['sid'] = None

    if room['state'] == 'lobby':
        del room['players'][sid]
        if len(room['players']) == 0:
            del rooms[code]
            if pid in player_sessions:
                del player_sessions[pid]
        else:
            if room['host'] == sid:
                room['host'] = next(iter(room['players']))
            socketio.emit('room_update', room_summary(code, room), room=code)
    else:
        cancel_timer(room)
        remaining = [
            {'name': v['name'], 'score': v['score'], 'id': v['id']}
            for k, v in room['players'].items() if k != sid
        ]
        disconnected_name = disconnected_player['name']
        socketio.emit('opponent_disconnected', {
            'disconnected_name': disconnected_name,
            'remaining_players': remaining,
        }, room=code)
        del rooms[code]
        for p_id, info in list(player_sessions.items()):
            if info.get('room_code') == code:
                del player_sessions[p_id]


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

    player_sessions[player_id] = {'room_code': room_code, 'sid': sid}
    join_room(room_code)

    state = room['state']
    restore_data = {
        'room_code': room_code,
        'player_id': player_id,
        'name': player_data['name'],
        'state': state,
        'is_host': room['host'] == sid,
        'room_info': room_summary(room_code, room, for_sid=sid),
    }

    if state == 'question':
        game_mode = room.get('game_mode', 'Classic')
        if game_mode == 'Steal':
            q_idx = player_data.get('question_idx', room['current_q'])
            q = room['questions'][q_idx % len(room['questions'])]
            elapsed = time.time() - room.get('q_start_time', time.time())
            remaining_time = max(0, room.get('timer_duration', 30) - int(elapsed))
            restore_data['question_data'] = {
                'question': q['q'],
                'opts': q['opts'],
                'current_q': room['current_q'],
                'total_q': len(room['questions']),
                'num_opts': len(q['opts']),
                'remaining_time': remaining_time,
                'already_answered': player_data.get('answered', False),
                'my_answer': player_data.get('answer'),
                'game_mode': 'Steal',
                'my_correct_idx': q['ans'],
            }
        else:
            q = room['questions'][room['current_q']]
            elapsed = time.time() - room.get('q_start_time', time.time())
            remaining_time = max(0, room.get('timer_duration', 30) - int(elapsed))
            restore_data['question_data'] = {
                'question': q['q'],
                'opts': q['opts'],
                'current_q': room['current_q'],
                'total_q': len(room['questions']),
                'num_opts': len(q['opts']),
                'remaining_time': remaining_time,
                'already_answered': player_data.get('answered', False),
                'my_answer': player_data.get('answer'),
                'game_mode': 'Classic',
            }
    elif state == 'finished':
        players = room['players']
        p_list = sorted(
            [{'name': v['name'], 'score': v['score'], 'id': v['id']} for v in players.values()],
            key=lambda x: x['score'], reverse=True
        )
        restore_data['rankings'] = p_list

    emit('session_restored', restore_data)


@socketio.on('create_room')
def on_create_room(data):
    name = data.get('name', 'Player').strip() or 'Player'
    mode = data.get('mode', MODES[0])
    game_mode = data.get('game_mode', 'Classic')
    timer_duration = data.get('timer_duration', 30)
    player_id = data.get('player_id', gen_code() + gen_code())
    sid = request.sid

    if mode not in QUIZ_DATA:
        mode = MODES[0]
    if game_mode not in GAME_MODES:
        game_mode = 'Classic'
    if timer_duration not in TIMER_OPTIONS:
        timer_duration = 30

    code = gen_code()
    while code in rooms:
        code = gen_code()

    questions = list(QUIZ_DATA[mode])
    random.shuffle(questions)

    rooms[code] = {
        'players': {
            sid: {
                'name': name, 'score': 0, 'answered': False,
                'answer': None, 'id': player_id,
                'card_picked': False, 'card_idx': None,
                'card_effect': None, 'card_value': 0,
                'card_label': '', 'card_icon': '',
                'question_idx': 0, 'my_correct_idx': None,
            }
        },
        'host': sid,
        'mode': mode,
        'game_mode': game_mode,
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
    if len(room['players']) >= 2:
        emit('join_error', {'message': 'Room sudah penuh!'})
        return
    if room['state'] != 'lobby':
        emit('join_error', {'message': 'Permainan sudah dimulai!'})
        return

    room['players'][sid] = {
        'name': name, 'score': 0, 'answered': False,
        'answer': None, 'id': player_id,
        'card_picked': False, 'card_idx': None,
        'card_effect': None, 'card_value': 0,
        'card_label': '', 'card_icon': '',
        'question_idx': 0, 'my_correct_idx': None,
    }
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
    if len(room['players']) < 2:
        emit('error_msg', {'message': 'Butuh 2 pemain untuk memulai!'})
        return
    if room.get('game_mode') == 'Steal':
        send_question_steal(code)
    else:
        send_question(code)


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

    player['answered'] = True
    player['answer'] = answer

    game_mode = room.get('game_mode', 'Classic')

    if game_mode == 'Classic':
        for other_sid in room['players']:
            if other_sid != sid:
                socketio.emit('opponent_answered', {}, room=other_sid)
        all_answered = all(p['answered'] for p in room['players'].values())
        if all_answered:
            end_round_classic(code)
    else:
        # Steal mode
        was_correct = (answer == player.get('my_correct_idx'))
        for other_sid in room['players']:
            if other_sid != sid:
                socketio.emit('opponent_answered', {}, room=other_sid)

        if was_correct:
            # Generate card deck for this player
            cards = generate_card_deck()
            player['card_deck'] = cards
            socketio.emit('card_pick', {
                'cards': [{'label': c['label'], 'icon': c['icon'], 'type': c['type']} for c in cards],
            }, room=sid)
        else:
            player['card_picked'] = True  # no card to pick

        check_round_end(code)


@socketio.on('pick_card')
def on_pick_card(data):
    sid = request.sid
    code = data.get('code')
    card_idx = data.get('card_idx')
    room = rooms.get(code)
    if not room:
        return
    player = room['players'].get(sid)
    if not player or player.get('card_picked'):
        return

    cards = player.get('card_deck', [])
    if card_idx is None or card_idx < 0 or card_idx >= len(cards):
        card_idx = 0

    card = cards[card_idx]
    player['card_picked'] = True
    player['card_idx'] = card_idx
    player['card_effect'] = card['type']
    player['card_value'] = card['value']
    player['card_label'] = card['label']
    player['card_icon'] = card['icon']

    socketio.emit('card_revealed', {
        'card_idx': card_idx,
        'card': {'label': card['label'], 'icon': card['icon'], 'type': card['type']},
    }, room=sid)

    check_round_end(code)


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

    if room['state'] != 'lobby':
        cancel_timer(room)
        remaining = [
            {'name': v['name'], 'score': v['score'], 'id': v['id']}
            for k, v in room['players'].items() if k != sid
        ]
        socketio.emit('opponent_disconnected', {
            'disconnected_name': player['name'],
            'remaining_players': remaining,
        }, room=code)
        del rooms[code]
        for p_id, info in list(player_sessions.items()):
            if info.get('room_code') == code:
                del player_sessions[p_id]
    else:
        del room['players'][sid]
        if pid in player_sessions:
            del player_sessions[pid]
        if len(room['players']) == 0:
            del rooms[code]
        else:
            if room['host'] == sid:
                room['host'] = next(iter(room['players']))
            socketio.emit('room_update', room_summary(code, room), room=code)


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
    # Tell the other peer to create an answer
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
  .anim-glow{animation:glow 1.5s ease infinite;}

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

  .scoreboard{
    background:rgba(0,0,0,0.4);backdrop-filter:blur(8px);
    border-bottom:2px solid rgba(255,255,255,0.1);
    padding:10px 20px;display:flex;justify-content:space-between;align-items:center;
    position:relative;
  }
  .score-box{text-align:center;position:relative;min-width:100px;}
  .score-name{font-size:0.85rem;font-weight:700;opacity:0.8;text-transform:uppercase;letter-spacing:1px;}
  .score-val{font-size:1.8rem;font-weight:900;}
  .vs-badge{font-size:1.2rem;font-weight:900;color:#f39c12;text-shadow:0 0 10px rgba(243,156,18,0.5);}

  .top-points-badge{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    background:linear-gradient(135deg,#f39c12,#e67e22);
    padding:4px 16px;border-radius:20px;font-size:0.75rem;font-weight:800;
    color:#1a0533;white-space:nowrap;box-shadow:0 2px 10px rgba(243,156,18,0.4);
    display:none;
  }
  .top-points-badge.show{display:block;}

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
    border-radius:14px;padding:16px;display:flex;align-items:center;gap:14px;
  }
  .player-slot.filled{border-style:solid;border-color:rgba(255,255,255,0.5);background:rgba(255,255,255,0.12);}
  .player-avatar{
    width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#9b59b6,#e74c3c);
    display:flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:900;flex-shrink:0;
  }

  /* Card pick grid */
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

  /* Chat */
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

  /* Voice */
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
    padding:10px 20px;border-radius:10px;border:2px solid rgba(255,255,255,0.3);
    background:rgba(255,255,255,0.08);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:0.9rem;font-weight:700;cursor:pointer;transition:all 0.2s;
  }
  .mode-btn.active{background:linear-gradient(135deg,#f39c12,#e67e22);border-color:#f39c12;color:#1a0533;}
  .timer-btn{
    padding:8px 16px;border-radius:8px;border:2px solid rgba(255,255,255,0.3);
    background:rgba(255,255,255,0.08);color:#fff;font-family:'Montserrat',sans-serif;
    font-size:0.85rem;font-weight:700;cursor:pointer;transition:all 0.2s;
  }
  .timer-btn.active{background:#27ae60;border-color:#2ecc71;}
</style>
</head>
<body>

<!-- ═══════════════════════ SCREEN: MENU ═══════════════════════ -->
<div id="screen-menu" class="screen active items-center justify-center p-6">
  <div style="max-width:440px;width:100%;" class="anim-slideUp">
    <div class="text-center mb-8">
      <div style="font-size:3.5rem;font-weight:900;background:linear-gradient(135deg,#f39c12,#e74c3c,#9b59b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-1px;">QuizBattle!</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;font-weight:600;margin-top:4px;">1v1 Quiz Game • Kahoot Style</div>
    </div>

    <div class="card p-6 mb-4">
      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Nama Pemain</div>
      <input id="menu-name" class="input-field" placeholder="Masukkan nama kamu..." maxlength="20"/>
    </div>

    <div class="card p-6 mb-4">
      <div style="font-size:1rem;font-weight:800;margin-bottom:16px;">🎮 Buat Room Baru</div>

      <div style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Game Mode</div>
      <div id="game-mode-buttons" style="display:flex;gap:8px;margin-bottom:16px;">
        {% for gm in game_modes %}
        <button class="mode-btn {% if loop.first %}active{% endif %}" data-gm="{{ gm }}" onclick="selectGameMode('{{ gm }}')">
          {% if gm == 'Classic' %}🎯 Classic{% else %}🃏 Steal{% endif %}
        </button>
        {% endfor %}
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
      <b style="color:#f39c12;">🎯 Classic:</b> Soal sama untuk keduanya, siapa cepat dia dapat.<br/>
      <b style="color:#9b59b6;">🃏 Steal:</b> Soal sendiri-sendiri. Jawab benar = ambil 1 kartu dari 5 (2 kartu -90 poin, 2 kartu +50 poin, 1 kartu swap poin!).
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
      <div style="font-size:0.85rem;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Pemain (0/2)</div>
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
  <div class="scoreboard" id="scoreboard">
    <div class="score-box" id="score-p1-box">
      <div class="score-name" id="score-p1-name">P1</div>
      <div class="score-val" id="score-p1-val">0</div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
      <div class="vs-badge">VS</div>
      <div class="top-points-badge" id="top-points-badge">TOP: 0</div>
    </div>
    <div class="score-box" id="score-p2-box">
      <div class="score-name" id="score-p2-name">P2</div>
      <div class="score-val" id="score-p2-val">0</div>
    </div>
  </div>

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
  </div>
</div>

<!-- ═══════════════════════ SCREEN: RESULT ═══════════════════════ -->
<div id="screen-result" class="screen" style="flex-direction:column;">
  <div class="scoreboard" id="scoreboard-result">
    <div class="score-box">
      <div class="score-name" id="res-p1-name">P1</div>
      <div class="score-val" id="res-p1-val">0</div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
      <div class="vs-badge">VS</div>
      <div class="top-points-badge" id="top-points-badge-result">TOP: 0</div>
    </div>
    <div class="score-box">
      <div class="score-name" id="res-p2-name">P2</div>
      <div class="score-val" id="res-p2-val">0</div>
    </div>
  </div>

  <div style="flex:1;overflow-y:auto;padding:16px;" id="result-content">
    <div class="result-feedback mb-4 anim-popIn" id="round-feedback">
      <div id="result-icon" style="font-size:3rem;margin-bottom:8px;"></div>
      <div id="result-text" style="font-size:1.3rem;font-weight:900;margin-bottom:4px;"></div>
      <div id="result-delta" style="font-size:1.1rem;font-weight:700;"></div>
      <div id="result-card-info" style="display:none;margin-top:8px;font-size:1rem;font-weight:800;"></div>
    </div>

    <div id="result-answers" style="display:flex;flex-direction:column;gap:8px;"></div>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: FINAL ═══════════════════════ -->
<div id="screen-final" class="screen items-center justify-center p-6">
  <div style="max-width:440px;width:100%;text-align:center;" class="anim-bounceIn">
    <div id="final-title" style="font-size:2.5rem;font-weight:900;margin-bottom:6px;"></div>
    <div id="final-subtitle" style="font-size:1rem;color:rgba(255,255,255,0.7);margin-bottom:24px;"></div>

    <div id="final-rankings" style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px;"></div>

    <button class="btn-primary" onclick="goHome()" style="font-size:1rem;">🏠 Kembali ke Menu</button>
  </div>
</div>

<!-- ═══════════════════════ SCREEN: DISCONNECTED ═══════════════════════ -->
<div id="screen-disconnected" class="screen items-center justify-center p-6">
  <div style="max-width:400px;width:100%;text-align:center;" class="anim-bounceIn">
    <div style="font-size:5rem;margin-bottom:16px;">🏳️</div>
    <div style="font-size:2rem;font-weight:900;margin-bottom:8px;">KAMU MENANG!</div>
    <div style="font-size:1.1rem;color:rgba(255,255,255,0.7);margin-bottom:24px;">Lawan menyerah dari pertandingan</div>

    <div id="disconnected-scores" class="card p-4 mb-6" style="display:flex;justify-content:space-around;"></div>

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
let selectedTimer = 30;
let myCorrectIdx = null;
let currentGameMode = 'Classic';
let chatOpen = false;
let unreadChat = 0;
let cardDeck = [];
let cardPicked = false;

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
  const showBtns = ['lobby', 'question', 'result', 'finished'].includes(gameState);
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
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.gm === gm);
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

// ═══════════════════════ TOP POINTS ═══════════════════════
function updateTopPoints(players) {
  if (!players || players.length < 2) return;
  const topPlayer = players.reduce((a, b) => a.score >= b.score ? a : b);
  const badges = ['top-points-badge', 'top-points-badge-result'];
  badges.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = '👑 TOP: ' + topPlayer.score + ' (' + topPlayer.name + ')';
      el.classList.add('show');
    }
  });
}

// ═══════════════════════ SCORE ANIMATION ═══════════════════════
function animateScoreDelta(containerId, delta) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'score-float';
  el.textContent = delta > 0 ? '+' + delta : delta;
  el.style.color = delta > 0 ? '#2ecc71' : '#e74c3c';
  el.style.top = '0';
  el.style.left = '50%';
  el.style.transform = 'translateX(-50%)';
  container.appendChild(el);
  setTimeout(() => el.remove(), 1300);
}

// ═══════════════════════ LOBBY ═══════════════════════
function updateLobbyUI(roomInfo) {
  document.getElementById('lobby-code').textContent = roomInfo.code;
  document.getElementById('lobby-mode-display').textContent = '📚 ' + roomInfo.mode + ' • ' + roomInfo.game_mode;

  const container = document.getElementById('lobby-players');
  container.innerHTML = '';

  const slots = [{}, {}];
  roomInfo.players.forEach((p, i) => { slots[i] = p; });

  slots.forEach((p, i) => {
    const div = document.createElement('div');
    div.className = 'player-slot' + (p.name ? ' filled' : '');
    if (p.name) {
      const initials = p.name.substr(0, 2).toUpperCase();
      const isMe = p.id === myPlayerId;
      const hostBadge = p.is_host ? '<span style="background:#f39c12;color:#000;font-size:0.7rem;font-weight:800;padding:2px 8px;border-radius:10px;margin-left:6px;">HOST</span>' : '';
      const meBadge = isMe ? '<span style="background:rgba(255,255,255,0.2);font-size:0.7rem;font-weight:800;padding:2px 8px;border-radius:10px;margin-left:6px;">KAMU</span>' : '';
      div.innerHTML = `
        <div class="player-avatar">${initials}</div>
        <div>
          <div style="font-weight:800;font-size:1rem;">${p.name}${hostBadge}${meBadge}</div>
          <div style="font-size:0.8rem;color:rgba(255,255,255,0.5);">Siap bermain</div>
        </div>`;
    } else {
      div.innerHTML = `
        <div class="player-avatar" style="background:rgba(255,255,255,0.1);">?</div>
        <div style="color:rgba(255,255,255,0.4);font-weight:700;">Menunggu pemain ${i+1}...</div>`;
    }
    container.appendChild(div);
  });

  const count = roomInfo.players.length;
  container.previousElementSibling.textContent = `Pemain (${count}/2)`;

  const startSection = document.getElementById('lobby-start-section');
  const waitingEl = document.getElementById('lobby-waiting');
  if (count >= 2 && isHost) {
    startSection.style.display = 'block';
    waitingEl.style.display = 'none';
  } else if (count >= 2 && !isHost) {
    waitingEl.innerHTML = '<div class="anim-pulse">✅ Menunggu host memulai permainan...</div>';
    startSection.style.display = 'none';
  } else {
    startSection.style.display = 'none';
    waitingEl.style.display = 'block';
    waitingEl.innerHTML = '<div class="anim-pulse">⏳ Menunggu pemain lain bergabung...</div>';
  }
}

// ═══════════════════════ SCOREBOARD ═══════════════════════
function updateScoreboard(players, myId, prefix) {
  prefix = prefix || '';
  const myPl = players.find(p => p.id === myId);
  const oppPl = players.find(p => p.id !== myId);
  if (!myPl || !oppPl) return;

  const n1 = prefix + 'p1-name', v1 = prefix + 'p1-val';
  const n2 = prefix + 'p2-name', v2 = prefix + 'p2-val';

  document.getElementById(n1).textContent = myPl.name;
  document.getElementById(v1).textContent = myPl.score;
  document.getElementById(n2).textContent = oppPl.name;
  document.getElementById(v2).textContent = oppPl.score;

  updateTopPoints(players);
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
    btn.innerHTML = `<span style="font-size:1.3rem;opacity:0.8;">${shapes[i]}</span><span style="flex:1;">${data.opts[i]}</span>`;
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

  document.getElementById('waiting-opponent').style.display = 'block';
  stopTimer();

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
  document.getElementById('card-reveal').style.display = 'none';

  const section = document.getElementById('card-pick-section');
  section.style.display = 'block';

  const grid = document.getElementById('card-grid');
  grid.innerHTML = '';

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

  // Reveal animation handled by card_revealed event
}

// ═══════════════════════ ROUND RESULT ═══════════════════════
function showRoundResult(data) {
  showScreen('screen-result');
  stopTimer();

  const myPl = data.players.find(p => p.id === myPlayerId);
  const oppPl = data.players.find(p => p.id !== myPlayerId);

  if (myPl && oppPl) {
    document.getElementById('res-p1-name').textContent = myPl.name;
    document.getElementById('res-p1-val').textContent = myPl.score;
    document.getElementById('res-p2-name').textContent = oppPl.name;
    document.getElementById('res-p2-val').textContent = oppPl.score;
    updateTopPoints(data.players);

    const cardInfo = document.getElementById('result-card-info');
    if (currentGameMode === 'Steal') {
      if (myPl.was_correct && myPl.card_effect) {
        document.getElementById('result-icon').textContent = myPl.card_icon || '🃏';
        document.getElementById('result-text').textContent = 'Kartu Kamu: ' + (myPl.card_label || '');
        document.getElementById('result-text').style.color = myPl.card_effect === 'minus' ? '#e74c3c' : (myPl.card_effect === 'plus' ? '#2ecc71' : '#f39c12');
        document.getElementById('result-delta').textContent = myPl.card_effect === 'swap' ? 'Poin ditukar dengan lawan!' : (myPl.card_effect === 'plus' ? '+' + myPl.card_value + ' poin' : myPl.card_value + ' poin');
        document.getElementById('result-delta').style.color = myPl.card_effect === 'minus' ? '#e74c3c' : '#2ecc71';
        cardInfo.style.display = 'block';
        cardInfo.textContent = '🃏 ' + (myPl.card_label || '');
        cardInfo.style.color = myPl.card_effect === 'minus' ? '#e74c3c' : '#2ecc71';
      } else if (!myPl.was_correct) {
        document.getElementById('result-icon').textContent = '😔';
        document.getElementById('result-text').textContent = 'Salah!';
        document.getElementById('result-text').style.color = '#e74c3c';
        document.getElementById('result-delta').textContent = 'Tidak dapat kartu';
        document.getElementById('result-delta').style.color = '#e74c3c';
        cardInfo.style.display = 'none';
      }
    } else {
      // Classic mode
      cardInfo.style.display = 'none';
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
  }

  // Show answer options (Classic mode only)
  if (currentGameMode === 'Classic' && data.opts) {
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
      div.innerHTML = `<span style="font-size:1.3rem;opacity:0.8;">${shapes[i]}</span><span style="flex:1;">${opt}</span>`;

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
function showFinalResult(rankings) {
  showScreen('screen-final');
  stopTimer();

  const me = rankings.find(p => p.id === myPlayerId);
  const myRank = rankings.findIndex(p => p.id === myPlayerId);

  let title, subtitle;
  if (rankings.length === 1) {
    title = '🏆 MENANG!';
    subtitle = 'Lawan telah keluar dari permainan';
  } else if (rankings[0].score === rankings[1].score) {
    title = '🤝 SERI!';
    subtitle = 'Pertandingan berakhir imbang!';
  } else if (myRank === 0) {
    title = '🏆 MENANG!';
    subtitle = 'Kamu adalah pemenang!';
  } else {
    title = '😔 KALAH';
    subtitle = 'Lebih semangat lain kali!';
  }

  document.getElementById('final-title').textContent = title;
  document.getElementById('final-subtitle').textContent = subtitle;

  const container = document.getElementById('final-rankings');
  container.innerHTML = '';
  const medals = ['👑', '🥈'];
  const rankNames = ['Juara 1', 'Peringkat 2'];

  rankings.forEach((p, i) => {
    const isMe = p.id === myPlayerId;
    const div = document.createElement('div');
    div.className = 'card anim-slideUp';
    div.style.cssText = `padding:20px;display:flex;align-items:center;gap:16px;animation-delay:${i*0.15}s;${isMe ? 'border:2px solid #f39c12;' : ''}`;
    div.innerHTML = `
      <div style="font-size:2.5rem;">${medals[i] || '🎖️'}</div>
      <div style="flex:1;">
        <div style="font-weight:800;font-size:1.1rem;">${p.name}${isMe ? ' <span style="font-size:0.75rem;background:#f39c12;color:#000;padding:2px 8px;border-radius:10px;font-weight:800;">KAMU</span>' : ''}</div>
        <div style="font-size:0.85rem;color:rgba(255,255,255,0.6);font-weight:600;">${rankNames[i] || ''}</div>
      </div>
      <div style="font-size:2rem;font-weight:900;color:${i===0?'#f39c12':'rgba(255,255,255,0.7)'};">${p.score}</div>`;
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
  div.innerHTML = `<div class="chat-name">${data.name}</div>${escapeHtml(data.msg)}`;
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

    // Notify the other peer to initiate connection
    socket.emit('voice_start', { code: myRoomCode });

    // We'll create the peer connection when we receive voice_start from the other side
    // or we can initiate immediately
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

  // Add local tracks
  if (localStream) {
    localStream.getTracks().forEach(track => {
      peerConnection.addTrack(track, localStream);
    });
  }

  // Handle remote tracks
  peerConnection.ontrack = (event) => {
    const audio = document.getElementById('remote-audio') || createRemoteAudio();
    audio.srcObject = event.streams[0];
    audio.play().catch(() => {});
  };

  // Handle ICE candidates
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

  const state = data.state;
  if (state === 'lobby') {
    showScreen('screen-lobby');
    updateLobbyUI(data.room_info);
  } else if (state === 'question' && data.question_data) {
    const qd = data.question_data;
    currentGameMode = qd.game_mode || 'Classic';
    myCorrectIdx = qd.my_correct_idx !== undefined ? qd.my_correct_idx : null;
    updateScoreboard(data.room_info.players, myPlayerId, 'score-');
    renderQuestion(qd, qd.remaining_time);
    if (qd.already_answered) {
      answeredThisRound = true;
      document.getElementById('waiting-opponent').style.display = 'block';
      const btns = document.querySelectorAll('.btn-answer');
      btns.forEach(b => { b.disabled = true; b.style.opacity = '0.5'; });
      stopTimer();
    }
  } else if (state === 'finished' && data.rankings) {
    showFinalResult(data.rankings);
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
  if (!answeredThisRound) {
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
  document.getElementById('waiting-opponent').style.display = 'block';
  document.getElementById('card-grid').style.display = 'none';
});

socket.on('round_result', (data) => {
  stopTimer();
  const players = data.players;
  updateScoreboard(players, myPlayerId, 'score-');

  if (currentGameMode === 'Classic') {
    const myPl = players.find(p => p.id === myPlayerId);
    const oppPl = players.find(p => p.id !== myPlayerId);
    if (myPl) animateScoreDelta('score-p1-box', myPl.delta);
    if (oppPl) animateScoreDelta('score-p2-box', oppPl.delta);
  }

  setTimeout(() => { showRoundResult(data); }, 400);
});

socket.on('game_over', (data) => {
  showFinalResult(data.rankings);
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
    div.innerHTML = `<div style="font-size:0.85rem;font-weight:700;opacity:0.7;">${p.name}</div><div style="font-size:2rem;font-weight:900;color:#2ecc71;">${p.score}</div>`;
    container.appendChild(div);
  });

  const disconnectedDiv = document.createElement('div');
  disconnectedDiv.style.textAlign = 'center';
  disconnectedDiv.innerHTML = `<div style="font-size:0.85rem;font-weight:700;opacity:0.7;">${data.disconnected_name}</div><div style="font-size:2rem;font-weight:900;color:#e74c3c;">🚪</div>`;
  container.appendChild(disconnectedDiv);
});

// Chat events
socket.on('chat_message', (data) => { addChatMessage(data); });

// Voice signaling events
socket.on('voice_start', (data) => {
  // Other peer wants to start voice - we should also get mic and create connection
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
