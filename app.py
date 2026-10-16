import base64
import io
import subprocess
from flask import Flask, render_template_string
from flask_socketio import SocketIO
from PIL import Image
import mss

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Kali Full Remote Desktop</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background: #0f0f17; color: #00ffcc; margin: 0; padding: 10px; }
        h3 { margin: 10px 0; color: #00ffcc; }
        #screen-container { width: 100%; max-width: 900px; margin: 0 auto; border: 2px solid #00ffcc; background: #000; box-shadow: 0 0 15px rgba(0,255,204,0.3); }
        #screen { width: 100%; height: auto; display: block; }
        #touchpad { width: 100%; max-width: 900px; height: 200px; margin: 15px auto; background: #1a1a2e; border: 2px dashed #00ffcc; border-radius: 10px; touch-action: none; display: flex; align-items: center; justify-content: center; color: #00ffcc; font-size: 15px; font-weight: bold; cursor: pointer; }
        .controls { display: flex; justify-content: center; gap: 10px; margin-top: 10px; }
        .btn { padding: 12px 20px; font-size: 16px; cursor: pointer; border: 1px solid #00ffcc; border-radius: 8px; background: #1a1a2e; color: #00ffcc; flex: 1; max-width: 160px; font-weight: bold; }
        .btn:active { background: #00ffcc; color: black; }
    </style>
</head>
<body>
    <h3>Kontrolli i Plotë i Kompjuterit</h3>
    <div id="screen-container">
        <img id="screen" src="" alt="Duke u lidhur me ekranin...">
    </div>

    <!-- Zona Touchpad për të lëvizur miun kudo në ekran -->
    <div id="touchpad">Kalo gishtin ose miun këtu për të lëvizur kursorin kudo</div>

    <div class="controls">
        <button class="btn" onclick="sendClick('1')">Klik Majtas</button>
        <button class="btn" onclick="sendClick('3')">Klik Djathtas</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        const screenImg = document.getElementById('screen');
        const touchpad = document.getElementById('touchpad');

        // Përditësimi i imazhit live të ekranit
        socket.on('frame', function(data) {
            screenImg.src = 'data:image/jpeg;base64,' + data.image;
        });

        let isTouching = false;
        let lastX = 0;
        let lastY = 0;

        touchpad.addEventListener('pointerdown', (e) => {
            isTouching = true;
            lastX = e.clientX;
            lastY = e.clientY;
        });

        window.addEventListener('pointermove', (e) => {
            if (!isTouching) return;
            let dx = e.clientX - lastX;
            let dy = e.clientY - lastY;
            lastX = e.clientX;
            lastY = e.clientY;

            // Dërgo zhvendosjen te serveri për të lëvizur kursorin global
            socket.emit('mouse_move', { x: dx * 2, y: dy * 2 });
        });

        window.addEventListener('pointerup', () => {
            isTouching = false;
        });

        function sendClick(button) {
            socket.emit('mouse_click', { button: button });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('mouse_move')
def handle_mouse_move(data):
    dx = int(data['x'])
    dy = int(data['y'])
    # Lëviz kursorin e sistemit operativ relativisht
    subprocess.run(['xdotool', 'mousemove_relative', '--', str(dx), str(dy)])

@socketio.on('mouse_click')
def handle_mouse_click(data):
    btn = data['button']
    subprocess.run(['xdotool', 'click', btn])

def send_screens():
    with mss.mss() as sct:
        monitor = sct.monitors[1] # Kap monitorin kryesor të kompjuterit
        while True:
            img = sct.grab(monitor)
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            pil_img.thumbnail((1024, 768)) # Kompresim për shpejtësi
            
            buffer = io.BytesIO()
            pil_img.save(buffer, format="JPEG", quality=60)
            encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            socketio.emit('frame', {'image': encoded_image})
            socketio.sleep(0.1) # Rreth 10 korniza në sekondë

@socketio.on('connect')
def handle_connect():
    socketio.start_background_task(send_screens)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

