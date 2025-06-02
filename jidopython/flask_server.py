from flask import Flask, send_file
app = Flask(__name__)

@app.route('/')
def home():
    return 'ESP32용 BMP 서버입니다.'

@app.route('/map.bmp')
def serve_bmp():
    return send_file('map.bmp', mimetype='image/bmp')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
