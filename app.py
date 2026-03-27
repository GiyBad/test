import subprocess
import threading
import os
import time
from flask import Flask, send_from_directory
from pyngrok import ngrok

app = Flask(__name__)

# Папка для HLS
STREAM_DIR = "/tmp/hls_stream"
if not os.path.exists(STREAM_DIR):
    os.makedirs(STREAM_DIR)

# ИСТОЧНИК (Тот самый с токеном test)
SOURCE = "http://45.145.32.13:20440/match_futbol_3_hd/index.m3u8?token=test"
LOGO_URL = "https://i.postimg.cc/LXP8vbtv/Snimok-ekrana-2026-03-19-154147.png"

def run_ffmpeg():
    # ФИЛЬТР: Масштабируем до 1080p и накладываем лого
    # [0:v]scale=1920:1080 — принудительно делаем Full HD
    filter_complex = "[1:v]scale=250:-1[logo]; [0:v]scale=1920:1080[bg]; [bg][logo]overlay=main_w-overlay_w-30:30"
    
    command = [
        'ffmpeg',
        '-re',
        '-hide_banner',
        '-loglevel', 'error',
        '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        '-i', SOURCE,
        '-i', LOGO_URL,
        '-filter_complex', filter_complex,
        '-c:v', 'libx264',
        '-preset', 'veryfast', # Для 1080p на Гитхабе ставим veryfast (баланс качества)
        '-crf', '20',           # Качество выше (чем меньше число, тем лучше картинка)
        '-maxrate', '5000k',    # Лимит битрейта для 1080p
        '-bufsize', '10000k',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-f', 'hls',
        '-hls_time', '4',
        '-hls_list_size', '6',
        '-hls_flags', 'delete_segments',
        os.path.join(STREAM_DIR, 'live.m3u8')
    ]
    
    while True:
        print("Запуск FFmpeg 1080p...")
        # Очистка старых сегментов
        for f in os.listdir(STREAM_DIR):
            try: os.remove(os.path.join(STREAM_DIR, f))
            except: pass
            
        process = subprocess.Popen(command)
        process.wait()
        print("Поток упал, рестарт через 5 сек...")
        time.sleep(5)

@app.route('/live.m3u8')
def playlist():
    return send_from_directory(STREAM_DIR, 'live.m3u8')

@app.route('/<filename>')
def segments(filename):
    return send_from_directory(STREAM_DIR, filename)

if __name__ == '__main__':
    # Запускаем стрим в отдельном потоке
    threading.Thread(target=run_ffmpeg, daemon=True).start()
    
    # Если есть токен Ngrok в переменных окружения (для GitHub Actions)
    auth_token = os.environ.get("NGROK_AUTH")
    if auth_token:
        ngrok.set_auth_token(auth_token)
        public_url = ngrok.connect(8080).public_url
        print(f"\n ССЫЛКА ДЛЯ IPTV: {public_url}/live.m3u8 \n")
    
    app.run(host='0.0.0.0', port=8080)
