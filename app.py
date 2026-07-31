from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-chalange')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- DATA SOAL ---
QUIZ_DATA = {
    "mtk_easy": [
        {"id": 1, "question": "Hasil dari 25 × 4 - 30 adalah...", "options": ["70", "80", "60", "50"], "answer": 0},
        {"id": 2, "question": "Jika 3x + 7 = 22, berapa nilai x?", "options": ["3", "5", "7", "15"], "answer": 1},
        {"id": 3, "question": "Luas persegi panjang dengan panjang 12 cm dan lebar 5 cm adalah...", "options": ["34 cm²", "50 cm²", "60 cm²", "120 cm²"], "answer": 2},
        {"id": 4, "question": "15% dari 200 adalah...", "options": ["15", "20", "25", "30"], "answer": 3},
        {"id": 5, "question": "FPB dari 24 dan 36 adalah...", "options": ["6", "12", "18", "24"], "answer": 1},
        {"id": 6, "question": "Jika a = 5 dan b = 3, nilai dari 2a² - 3b adalah...", "options": ["41", "31", "21", "19"], "answer": 0},
        {"id": 7, "question": "Keliling lingkaran dengan jari-jari 7 cm (π = 22/7) adalah...", "options": ["22 cm", "44 cm", "88 cm", "154 cm"], "answer": 1},
        {"id": 8, "question": "Rata-rata dari data: 6, 8, 7, 9, 10 adalah...", "options": ["7", "7.5", "8", "8.5"], "answer": 2},
        {"id": 9, "question": "Hasil dari (-12) + 8 × (-3) adalah...", "options": ["-12", "-24", "-36", "12"], "answer": 2},
        {"id": 10, "question": "Segitiga dengan alas 10 cm dan tinggi 8 cm memiliki luas...", "options": ["80 cm²", "40 cm²", "20 cm²", "18 cm²"], "answer": 1}
    ],
    "mtk_hard": [
        {"id": 11, "question": "Turunan pertama dari f(x) = 3x² + 5x - 4 adalah...", "options": ["6x + 5", "3x + 5", "6x - 4", "6x² + 5"], "answer": 0},
        {"id": 12, "question": "Nilai dari lim(x→2) (x² + 3x - 2) adalah...", "options": ["6", "8", "10", "12"], "answer": 1},
        {"id": 13, "question": "Hasil dari ∫ (4x³ + 2x) dx adalah...", "options": ["12x² + 2 + C", "x⁴ + x² + C", "2x⁴ + x² + C", "4x⁴ + 2x² + C"], "answer": 1},
        {"id": 14, "question": "Turunan dari f(x) = sin(2x) adalah...", "options": ["cos(2x)", "-cos(2x)", "2cos(2x)", "-2cos(2x)"], "answer": 2},
        {"id": 15, "question": "Nilai lim(x→0) [sin(3x) / x] adalah...", "options": ["0", "1", "3", "Tidak terdefinisi"], "answer": 2},
        {"id": 16, "question": "Jika f(x) = (2x + 1)³, maka f'(x) adalah...", "options": ["3(2x+1)²", "6(2x+1)²", "6(2x+1)³", "2(2x+1)²"], "answer": 1},
        {"id": 17, "question": "Hasil integral tentu ∫₀² 3x² dx adalah...", "options": ["4", "6", "8", "12"], "answer": 2},
        {"id": 18, "question": "Turunan pertama dari f(x) = e^(3x) adalah...", "options": ["e^(3x)", "3e^(3x)", "(1/3)e^(3x)", "3x e^(3x-1)"], "answer": 1},
        {"id": 19, "question": "Nilai stasioner dari f(x) = x² - 4x + 5 terjadi saat x = ...", "options": ["x = -2", "x = 0", "x = 2", "x = 4"], "answer": 2},
        {"id": 20, "question": "Jika y = ln(x² + 1), maka dy/dx adalah...", "options": ["1 / (x² + 1)", "2x / (x² + 1)", "x / (x² + 1)", "2x ln(x² + 1)"], "answer": 1}
    ],
    "analogy": [
        {"id": 1, "statement": "Guru seperti tukang kebun. Tukang kebun merawat tanaman agar tumbuh, begitu juga guru membimbing murid agar berkembang.", "answer": "Bukan False Analogy"},
        {"id": 2, "statement": "Otak manusia seperti RAM komputer. Karena RAM bisa ditambah kapasitasnya, maka otak manusia juga bisa ditambah kapasitasnya dengan operasi.", "answer": "False Analogy"},
        {"id": 3, "statement": "Hati manusia seperti mesin mobil. Kalau mesin bisa diganti oli agar awet, berarti hati manusia juga cukup diberi vitamin supaya tidak pernah rusak.", "answer": "False Analogy"},
        {"id": 4, "statement": "Belajar bahasa seperti belajar bermain gitar. Keduanya membutuhkan latihan secara rutin.", "answer": "Bukan False Analogy"},
        {"id": 5, "statement": "Negara seperti sebuah keluarga. Karena ayah boleh menentukan semua keputusan di rumah, maka presiden juga boleh membuat semua keputusan tanpa persetujuan siapa pun.", "answer": "False Analogy"}
    ]
}

rooms = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def get_question_data(mode, idx):
    if idx < len(QUIZ_DATA[mode]):
        q_data = QUIZ_DATA[mode][idx]
        return {
            'q_num': idx + 1,
            'question': q_data['question'] if mode != 'analogy' else f'"{q_data["statement"]}"',
            'options': q_data.get('options', ["Bukan False Analogy", "False Analogy"]),
            'mode': mode
        }
    return None

@socketio.on('create_room')
def on_create_room(data):
    room_code = generate_room_code()
    player_id = data['player_id']
    
    rooms[room_code] = {
        'host_id': player_id,
        'guest_id': None,
        'players': {
            player_id: {'name': data['name'], 'score': 0, 'role': 'Host', 'sid': request.sid}
        },
        'mode': data['mode'],
        'current_q_index': 0,
        'status': 'waiting'
    }
    join_room(room_code)
    emit('room_created', {'room_code': room_code, 'mode': data['mode']})

@socketio.on('join_room')
def on_join_room(data):
    code = data['code'].upper()
    player_id = data['player_id']
    
    if code in rooms and rooms[code]['status'] == 'waiting':
        if player_id not in rooms[code]['players']:
            rooms[code]['guest_id'] = player_id
            rooms[code]['players'][player_id] = {'name': data['name'], 'score': 0, 'role': 'Guest', 'sid': request.sid}
        else:
            rooms[code]['players'][player_id]['sid'] = request.sid
        
        join_room(code)
        
        host_id = rooms[code]['host_id']
        host_name = rooms[code]['players'][host_id]['name']
        
        emit('guest_joined', {'guest_name': data['name']}, to=code)
        emit('join_success', {'host_name': host_name, 'mode': rooms[code]['mode']}, to=request.sid)
    else:
        emit('room_error', {'msg': 'Kode Room tidak valid atau Room penuh/sudah mulai.'})

@socketio.on('restore_session')
def on_restore_session(data):
    code = data.get('code')
    player_id = data.get('player_id')
    
    if code in rooms and player_id in rooms[code]['players']:
        rooms[code]['players'][player_id]['sid'] = request.sid
        join_room(code)
        room = rooms[code]
        
        state_data = {
            'status': room['status'],
            'players': room['players'],
            'is_host': room['host_id'] == player_id
        }
        
        if room['status'] == 'playing':
            state_data['current_question'] = get_question_data(room['mode'], room['current_q_index'])
            
        emit('session_restored', state_data, to=request.sid)
    else:
        emit('session_invalid', to=request.sid)

@socketio.on('leave_room')
def on_leave_room(data):
    code = data.get('code')
    if code in rooms:
        emit('opponent_disconnected', {'msg': 'Lawan telah meninggalkan room.'}, to=code)
        del rooms[code]

@socketio.on('start_game')
def on_start_game(data):
    code = data['code']
    if code in rooms and rooms[code]['host_id'] == data['player_id']:
        rooms[code]['status'] = 'playing'
        q_data = get_question_data(rooms[code]['mode'], 0)
        emit('new_question', q_data, to=code)

@socketio.on('submit_answer')
def on_submit_answer(data):
    code = data['code']
    player_id = data['player_id']
    
    if code not in rooms: return
    room = rooms[code]
    
    mode = room['mode']
    idx = room['current_q_index']
    
    if idx >= len(QUIZ_DATA[mode]): return
    
    correct_ans = QUIZ_DATA[mode][idx]['answer']
    answer_idx = data['answer_idx']
    
    if mode == 'analogy':
        is_correct = (answer_idx == 0 and correct_ans == "Bukan False Analogy") or \
                     (answer_idx == 1 and correct_ans == "False Analogy")
    else:
        is_correct = (answer_idx == correct_ans)

    answerer_name = room['players'][player_id]['name']
    
    if is_correct:
        room['players'][player_id]['score'] += 5
        room['current_q_index'] += 1
    else:
        room['players'][player_id]['score'] -= 5
    
    next_q_data = get_question_data(mode, room['current_q_index'])
    if not next_q_data:
        room['status'] = 'finished'

    emit('answer_result', {
        'answerer_name': answerer_name,
        'is_correct': is_correct,
        'scores': room['players'],
        'next_question': next_q_data,
        'game_over': next_q_data is None
    }, to=code)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    for code, room in list(rooms.items()):
        disconnected = False
        for pid, pdata in list(room['players'].items()):
            if pdata.get('sid') == sid:
                disconnected = True
                break
        if disconnected:
            emit('opponent_disconnected', {'msg': 'Lawan keluar dari web atau koneksi terputus.'}, to=code)
            if code in rooms:
                del rooms[code]
            break

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chalange.my.id - Kahoot Edition</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Montserrat', sans-serif; background-color: #121212; }
        .kahoot-card { transition: all 0.1s ease; box-shadow: 0 6px 0 rgba(0,0,0,0.3); }
        .kahoot-card:active { transform: translateY(4px); box-shadow: 0 2px 0 rgba(0,0,0,0.3); }
        .disabled-btn { opacity: 0.5; pointer-events: none; }
        @keyframes popIn { 0% { transform: scale(0.5); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); } }
        .pop-in { animation: popIn 0.5s ease-out; }
        @keyframes shake { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-10px); } 75% { transform: translateX(10px); } }
        .shake { animation: shake 0.4s ease-in-out; }
        @keyframes slideUp { 0% { transform: translateY(40px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
        .slide-up { animation: slideUp 0.4s ease-out; }
    </style>
</head>
<body class="text-white min-h-screen flex flex-col justify-between p-4 selection:bg-purple-500 selection:text-white">

    <!-- HEADER / SKOR ATAS -->
    <header class="flex justify-between items-center bg-gray-900/80 backdrop-blur p-4 rounded-2xl mb-4 border border-gray-800 shadow-xl">
        <h1 class="text-xl md:text-2xl font-black tracking-wider text-purple-400">CHALANGE 1v1</h1>
        <div id="stats-multi" class="hidden flex w-full max-w-sm justify-between items-center mx-auto bg-black/50 px-4 py-2 rounded-xl text-base font-bold border border-gray-700">
            <div class="text-blue-400 text-center flex-1"><span id="p1-name">P1</span><br><span id="p1-score" class="text-xl text-white">0</span></div>
            <div class="text-gray-500 text-lg font-black px-3">VS</div>
            <div class="text-red-400 text-center flex-1"><span id="p2-name">P2</span><br><span id="p2-score" class="text-xl text-white">0</span></div>
        </div>
    </header>

    <main class="max-w-4xl w-full mx-auto flex-grow flex flex-col justify-center">

        <!-- MENU UTAMA -->
        <div id="multiplayer-menu" class="bg-gray-900 p-8 md:p-10 rounded-3xl text-center border border-gray-800 shadow-2xl">
            <h2 class="text-3xl font-black mb-6 text-white tracking-wide">KAHOOT 1v1 ARENA</h2>
            <input type="text" id="player-name" placeholder="Ketik Nama Kamu..." class="w-full p-4 bg-gray-800 text-white text-xl font-bold rounded-2xl mb-6 text-center focus:outline-none focus:ring-4 focus:ring-purple-600 border border-gray-700">
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                <div class="bg-gray-800/60 p-6 rounded-2xl border border-gray-700 flex flex-col justify-between">
                    <div>
                        <h3 class="font-extrabold text-lg mb-3 text-purple-300">Buat Room Baru</h3>
                        <select id="room-mode" class="w-full p-3.5 bg-gray-900 text-white rounded-xl mb-4 font-bold border border-gray-700 focus:outline-none">
                            <option value="mtk_easy">MTK (Easy)</option>
                            <option value="mtk_hard">MTK Kalkulus (Hard)</option>
                            <option value="analogy">Analogi Logika</option>
                        </select>
                    </div>
                    <button onclick="createRoom()" class="w-full bg-yellow-500 hover:bg-yellow-400 text-gray-900 p-4 rounded-xl font-black text-xl shadow-lg transition-transform active:scale-95">CREATE ROOM</button>
                </div>
                
                <div class="bg-gray-800/60 p-6 rounded-2xl border border-gray-700 flex flex-col justify-between">
                    <div>
                        <h3 class="font-extrabold text-lg mb-3 text-purple-300">Gabung Room Teman</h3>
                        <input type="text" id="join-code" placeholder="KODE ROOM" class="w-full p-3.5 bg-gray-900 text-white rounded-xl mb-4 font-bold text-center uppercase tracking-widest border border-gray-700 focus:outline-none">
                    </div>
                    <button onclick="joinRoom()" class="w-full bg-blue-600 hover:bg-blue-500 text-white p-4 rounded-xl font-black text-xl shadow-lg transition-transform active:scale-95">JOIN ROOM</button>
                </div>
            </div>
        </div>

        <!-- LOBBY -->
        <div id="waiting-lobby" class="hidden bg-gray-900 p-10 rounded-3xl text-center border border-gray-800 shadow-2xl">
            <h2 class="text-2xl font-extrabold mb-2 text-gray-400">KODE ROOM</h2>
            <div id="display-room-code" class="text-6xl font-black text-yellow-400 tracking-widest my-4 bg-black/40 py-4 rounded-2xl border border-gray-800"></div>
            <p class="text-lg mb-6 text-gray-400">Bagikan kode ini ke lawanmu agar bisa masuk.</p>
            
            <div id="lobby-status" class="bg-gray-800 p-5 rounded-2xl mb-6 text-lg font-bold text-gray-300 border border-gray-700">
                Menunggu lawan bergabung...
            </div>
            
            <button id="btn-start-match" onclick="startMatch()" class="hidden w-full bg-green-600 hover:bg-green-500 text-white p-4 rounded-2xl font-black text-2xl shadow-lg mb-4 transition-transform active:scale-95">
                MULAI PERMAINAN
            </button>

            <button onclick="leaveRoom()" class="w-full bg-gray-700 hover:bg-gray-600 text-white p-4 rounded-2xl font-bold text-lg transition-transform active:scale-95">
                KEMBALI KE MENU
            </button>
        </div>

        <!-- QUIZ SCREEN (KAHOOT STYLE) -->
        <div id="quiz-screen" class="hidden flex flex-col justify-between flex-grow">
            <div class="text-center font-extrabold text-lg mb-3 text-purple-400 bg-gray-900/50 py-1 px-4 rounded-full w-max mx-auto border border-gray-800" id="q-counter">Soal 1</div>
            
            <!-- Kotak Soal Utama -->
            <div class="bg-white text-gray-900 p-8 md:p-12 rounded-3xl shadow-2xl text-center mb-8 min-h-[180px] flex items-center justify-center border-b-8 border-gray-300">
                <h2 id="question-text" class="text-2xl md:text-4xl font-black leading-snug"></h2>
            </div>

            <!-- Grid Pilihan Jawaban Ala Kahoot (Merah, Biru, Kuning, Hijau dengan Simbol) -->
            <div id="options-grid" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
        </div>

        <!-- FEEDBACK SCREEN -->
        <div id="feedback-screen" class="hidden text-center p-12 rounded-3xl shadow-2xl transition-all border-4 border-black/20">
            <h2 id="feedback-title" class="text-5xl md:text-6xl font-black mb-4 tracking-wider"></h2>
            <p id="feedback-sub" class="text-2xl font-extrabold"></p>
        </div>

        <!-- RESULT SCREEN -->
        <div id="result-screen" class="hidden bg-gray-900 p-10 rounded-3xl text-center border border-gray-800 shadow-2xl">
            <h2 id="result-title" class="text-4xl md:text-5xl font-black mb-8 text-yellow-400">SKOR AKHIR</h2>
            <div id="final-standings" class="flex flex-col gap-4 text-xl font-bold mb-8 text-gray-200"></div>
            
            <button onclick="leaveRoom()" class="bg-purple-600 hover:bg-purple-500 font-black text-xl px-8 py-4 rounded-2xl shadow-xl text-white transition-transform active:scale-95">
                KEMBALI KE MENU UTAMA
            </button>
        </div>

        <!-- SURRENDER / DISCONNECT SCREEN (Lose GUI & Win by Surrender) -->
        <div id="surrender-screen" class="hidden text-center p-12 rounded-3xl shadow-2xl border-4 border-black/20 flex flex-col items-center justify-center min-h-[400px]">
            <div id="surrender-icon" class="text-7xl md:text-8xl mb-6 pop-in"></div>
            <h2 id="surrender-title" class="text-5xl md:text-6xl font-black mb-4 tracking-wider"></h2>
            <p id="surrender-sub" class="text-2xl font-extrabold mb-8"></p>
            <div id="surrender-scores" class="flex flex-col gap-3 text-lg font-bold mb-8 text-gray-200 w-full max-w-sm mx-auto"></div>
            <button onclick="leaveRoom()" class="bg-purple-600 hover:bg-purple-500 font-black text-xl px-8 py-4 rounded-2xl shadow-xl text-white transition-transform active:scale-95">
                KEMBALI KE MENU UTAMA
            </button>
        </div>

    </main>

    <script>
        const socket = io();
        
        function getPlayerId() {
            let pid = localStorage.getItem("playerId");
            if (!pid) {
                pid = 'pid_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem("playerId", pid);
            }
            return pid;
        }

        const playerId = getPlayerId();
        let myRoomCode = localStorage.getItem("roomCode") || "";

        document.addEventListener("DOMContentLoaded", () => {
            const savedName = localStorage.getItem("playerName");
            if (savedName) {
                document.getElementById("player-name").value = savedName;
            }
            
            if (myRoomCode) {
                socket.emit('restore_session', { code: myRoomCode, player_id: playerId });
            }
        });

        const elMultiMenu = document.getElementById('multiplayer-menu');
        const elLobby = document.getElementById('waiting-lobby');
        const elQuiz = document.getElementById('quiz-screen');
        const elFeedback = document.getElementById('feedback-screen');
        const elResult = document.getElementById('result-screen');
        const elSurrender = document.getElementById('surrender-screen');

        function hideAllScreens() {
            elMultiMenu.classList.add('hidden');
            elLobby.classList.add('hidden');
            elQuiz.classList.add('hidden');
            elFeedback.classList.add('hidden');
            elResult.classList.add('hidden');
            elSurrender.classList.add('hidden');
            document.getElementById('stats-multi').classList.add('hidden');
        }
        
        function updateScoresUI(playersObj) {
            const players = Object.values(playersObj);
            if (players.length > 0) {
                document.getElementById('p1-name').innerText = players[0].name;
                document.getElementById('p1-score').innerText = players[0].score;
            }
            if(players.length > 1) {
                document.getElementById('p2-name').innerText = players[1].name;
                document.getElementById('p2-score').innerText = players[1].score;
            }
        }

        function createRoom() {
            const name = document.getElementById('player-name').value || "Host";
            localStorage.setItem("playerName", name);
            const mode = document.getElementById('room-mode').value;
            socket.emit('create_room', { player_id: playerId, name, mode });
        }

        function joinRoom() {
            const name = document.getElementById('player-name').value || "Penantang";
            localStorage.setItem("playerName", name);
            const code = document.getElementById('join-code').value.trim();
            if(!code) return alert("Masukkan kode room.");
            socket.emit('join_room', { player_id: playerId, name, code });
        }

        function leaveRoom() {
            if (myRoomCode) {
                socket.emit('leave_room', { code: myRoomCode });
                localStorage.removeItem("roomCode");
            }
            location.reload();
        }

        socket.on('room_created', (data) => {
            myRoomCode = data.room_code;
            localStorage.setItem("roomCode", myRoomCode);
            elMultiMenu.classList.add('hidden');
            elLobby.classList.remove('hidden');
            document.getElementById('display-room-code').innerText = myRoomCode;
        });

        socket.on('join_success', (data) => {
            myRoomCode = document.getElementById('join-code').value.toUpperCase();
            localStorage.setItem("roomCode", myRoomCode);
            elMultiMenu.classList.add('hidden');
            elLobby.classList.remove('hidden');
            document.getElementById('display-room-code').innerText = myRoomCode;
            document.getElementById('lobby-status').innerText = `Tergabung ke room ${data.host_name}. Menunggu host mulai.`;
        });

        socket.on('guest_joined', (data) => {
            const status = document.getElementById('lobby-status');
            status.classList.add('text-green-400');
            status.innerText = `Lawan Bergabung: ${data.guest_name}`;
            document.getElementById('btn-start-match').classList.remove('hidden');
        });

        socket.on('room_error', (data) => {
            alert(data.msg);
            localStorage.removeItem("roomCode");
        });

        socket.on('session_restored', (data) => {
            elMultiMenu.classList.add('hidden');
            
            if (data.status === 'waiting') {
                elLobby.classList.remove('hidden');
                document.getElementById('display-room-code').innerText = myRoomCode;
                if (Object.keys(data.players).length > 1) {
                    document.getElementById('lobby-status').innerText = `Pemain lengkap.`;
                    if (data.is_host) document.getElementById('btn-start-match').classList.remove('hidden');
                }
            } else if (data.status === 'playing') {
                updateScoresUI(data.players);
                renderQuestion(data.current_question);
            }
        });

        socket.on('session_invalid', () => {
            localStorage.removeItem("roomCode");
            myRoomCode = "";
            elMultiMenu.classList.remove('hidden');
        });

        function startMatch() {
            socket.emit('start_game', { code: myRoomCode, player_id: playerId });
        }

        function renderQuestion(qData) {
            elLobby.classList.add('hidden');
            elFeedback.classList.add('hidden');
            document.getElementById('stats-multi').classList.remove('hidden');
            elQuiz.classList.remove('hidden');
            
            document.getElementById('q-counter').innerText = `Soal ${qData.q_num}`;
            document.getElementById('question-text').innerText = qData.question;
            
            const grid = document.getElementById('options-grid');
            grid.innerHTML = '';
            grid.classList.remove('disabled-btn');

            // Warna & Simbol Khas Kahoot (Merah-Segitiga, Biru-Belah Ketupat, Kuning-Lingkaran, Hijau-Kotak)
            const kahootStyles = [
                { bg: "bg-red-600 hover:bg-red-500", symbol: "▲" },
                { bg: "bg-blue-600 hover:bg-blue-500", symbol: "◆" },
                { bg: "bg-yellow-500 hover:bg-yellow-400 text-gray-900", symbol: "●" },
                { bg: "bg-green-600 hover:bg-green-500", symbol: "■" }
            ];

            qData.options.forEach((opt, idx) => {
                const style = kahootStyles[idx % 4];
                const btn = document.createElement('button');
                btn.className = `${style.bg} kahoot-card p-6 rounded-2xl font-black text-xl md:text-2xl text-left flex items-center gap-4 text-white shadow-lg slide-up`;
                btn.innerHTML = `<span class="bg-black/20 w-12 h-12 flex items-center justify-center rounded-xl text-2xl">${style.symbol}</span> <span class="flex-grow">${opt}</span>`;
                btn.onclick = () => {
                    grid.classList.add('disabled-btn');
                    socket.emit('submit_answer', { code: myRoomCode, player_id: playerId, answer_idx: idx });
                };
                grid.appendChild(btn);
            });
        }

        socket.on('new_question', (data) => {
            renderQuestion(data);
        });

        socket.on('answer_result', (data) => {
            elQuiz.classList.add('hidden');
            elFeedback.classList.remove('hidden');
            updateScoresUI(data.scores);

            if (data.is_correct) {
                elFeedback.className = "bg-green-600 text-white text-center p-12 rounded-3xl shadow-2xl border-4 border-green-400 pop-in";
                document.getElementById('feedback-title').innerText = "BENAR!";
                document.getElementById('feedback-sub').innerText = `${data.answerer_name} +5 Poin`;
            } else {
                elFeedback.className = "bg-red-600 text-white text-center p-12 rounded-3xl shadow-2xl border-4 border-red-400 shake";
                document.getElementById('feedback-title').innerText = "SALAH!";
                document.getElementById('feedback-sub').innerText = `${data.answerer_name} -5 Poin`;
            }

            setTimeout(() => {
                if (data.game_over) {
                    showGameOver(data.scores);
                } else {
                    renderQuestion(data.next_question);
                }
            }, 2000);
        });

        function showGameOver(scoresObj) {
            hideAllScreens();
            elResult.classList.remove('hidden');

            const sorted = Object.values(scoresObj).sort((a, b) => b.score - a.score);
            const standings = document.getElementById('final-standings');
            standings.innerHTML = '';
            
            const isWinner = sorted[0].score > sorted[1].score;
            const myName = localStorage.getItem("playerName") || "Host";
            const iWon = sorted[0].name === myName && isWinner;

            if (sorted[0].score === sorted[1].score) {
                document.getElementById('result-title').innerText = "SERI!";
                document.getElementById('result-title').className = "text-4xl md:text-5xl font-black mb-8 text-gray-300";
            } else if (iWon) {
                document.getElementById('result-title').innerText = "KAMU MENANG!";
                document.getElementById('result-title').className = "text-4xl md:text-5xl font-black mb-8 text-green-400";
            } else {
                document.getElementById('result-title').innerText = "KAMU KALAH!";
                document.getElementById('result-title').className = "text-4xl md:text-5xl font-black mb-8 text-red-400";
            }

            sorted.forEach((p, index) => {
                const badge = index === 0 ? "👑 Juara 1" : "🥈 Peringkat 2";
                standings.innerHTML += `<div class="bg-gray-800 p-5 rounded-2xl border border-gray-700 flex justify-between items-center"><span class="text-yellow-400">${badge} : ${p.name}</span> <span class="text-purple-300 font-black text-2xl">${p.score} Poin</span></div>`;
            });
        }

        // --- SURRENDER / DISCONNECT HANDLER ---
        socket.on('opponent_disconnected', (data) => {
            hideAllScreens();
            elSurrender.classList.remove('hidden');

            // Lawan keluar/meninggalkan web => lawan menyerah, kamu menang
            elSurrender.className = "bg-green-600 text-white text-center p-12 rounded-3xl shadow-2xl border-4 border-green-400 flex flex-col items-center justify-center min-h-[400px] pop-in";
            document.getElementById('surrender-icon').innerText = "🏳️";
            document.getElementById('surrender-title').innerText = "KAMU MENANG!";
            document.getElementById('surrender-sub').innerText = "Lawan menyerah dan meninggalkan pertandingan.";

            // Tampilkan skor akhir yang tersimpan di UI
            const p1 = document.getElementById('p1-name').innerText;
            const p1s = document.getElementById('p1-score').innerText;
            const p2 = document.getElementById('p2-name').innerText;
            const p2s = document.getElementById('p2-score').innerText;

            const scoresDiv = document.getElementById('surrender-scores');
            scoresDiv.innerHTML = `
                <div class="bg-black/30 p-4 rounded-2xl border border-green-300/30 flex justify-between items-center">
                    <span class="text-green-200">${p1}</span>
                    <span class="font-black text-2xl text-white">${p1s} Poin</span>
                </div>
                <div class="bg-black/30 p-4 rounded-2xl border border-green-300/30 flex justify-between items-center">
                    <span class="text-red-200 line-through opacity-70">${p2} (Menyerah)</span>
                    <span class="font-black text-2xl text-white">${p2s} Poin</span>
                </div>
            `;

            localStorage.removeItem("roomCode");
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
