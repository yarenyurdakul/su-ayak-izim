# app/izsu.py
from flask import Blueprint, jsonify, request
import requests
import pandas as pd

izsu_bp = Blueprint('izsu', __name__)

# --- YARDIMCI FONKSİYON  ---
def get_baraj_limiti(istenen_baraj_adi):
    url = "https://openapi.izmir.bel.tr/api/izsu/barajdurum"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        js_data = response.json()
        df = pd.DataFrame(js_data)
        
        # Baraj ismini içinde arıyoruz (örn: "Tahtalı" kelimesi geçiyorsa bulur)
        hedef_baraj = df[df['BarajKuyuAdi'].str.contains(istenen_baraj_adi, case=False, na=False)]
        
        if not hedef_baraj.empty:
            doluluk = pd.to_numeric(hedef_baraj.iloc[0]['DolulukOrani'], errors='coerce')
        else:
            doluluk = 50.0 # Bulunamazsa varsayılan
            
        if doluluk < 35:
            return 140, "Yüksek Risk", doluluk
        elif 35 <= doluluk <= 70:
            return 160, "Orta Risk", doluluk
        else:
            return 180, "Düşük Risk", doluluk
            
    except Exception as e:
        print(f"İZSU API Hatası: {e}")
        return 160, "Bilinmeyen Risk (API Hatası)", 50.0

# bu kısımda kullanıcı hangi baraja bağlıysa o braj ile ilgili bilgiler 
@izsu_bp.route('/baraj_durumu', methods=['POST'])
def baraj_durumu_endpoint():
    veri = request.get_json()
    baraj_adi = veri.get("baraj_adi")
    
    if not baraj_adi:
        return jsonify({"durum": False, "mesaj": "baraj_adi gerekli"}), 400
        
    limit, risk, doluluk = get_baraj_limiti(baraj_adi)
    
    return jsonify({
        "durum": True,
        "baraj_adi": baraj_adi,
        "doluluk_orani": doluluk,
        "gunluk_limit": limit,
        "risk_durumu": risk
    }), 200


@izsu_bp.route('/barajlar', methods=['GET'])
def baraj():
    url = "https://openapi.izmir.bel.tr/api/izsu/barajdurum"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 OPR/127.0.0.0 (Edition Yx GX TR 2)",
    }
    try:
        response = requests.get(url, headers=headers, verify=False)
        js_data = response.json()
        df = pd.DataFrame(js_data)
        tablo = df[['BarajKuyuAdi', 'DolulukOrani']] 
        dicts = tablo.to_dict(orient='records')
        return jsonify(dicts)
    except Exception as e:
        return jsonify({
            "mesaj": "Kod try bloğunda patladı, sebebi şu:", 
            "hata_detayi": str(e)
        }), 500