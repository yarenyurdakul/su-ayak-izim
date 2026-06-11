# main.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Tüm modülleri içeri alıyoruz
from app.activity import activity_bp
from app.questions import questions_bp
from app.weather import weather_bp 
from app.flower import flower_bp
from app.izsu import izsu_bp 
from app.profil import profil_bp
from app.istatistik import istatistik_bp
from app.uses import uses_bp

load_dotenv()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

# --- KRİTİK KISIM: Kapıları sisteme tanıtıyoruz ---
app.register_blueprint(activity_bp, url_prefix="/activity")
app.register_blueprint(questions_bp, url_prefix="/quiz")
app.register_blueprint(weather_bp, url_prefix="/weather")
app.register_blueprint(flower_bp, url_prefix="/flower")
app.register_blueprint(izsu_bp, url_prefix="/izsu")
app.register_blueprint(profil_bp, url_prefix="/profil")
app.register_blueprint(istatistik_bp,url_prefix="/stats")
app.register_blueprint(uses_bp,url_prefix="/kullanimlar")

@app.route("/")
def home():
    return {"mesaj": "Su Ayak İzi API Tüm Modülleriyle Yayında!"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 