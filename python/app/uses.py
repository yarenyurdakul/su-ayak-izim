from flask import Blueprint, request, jsonify
from .database import kullanici_verilerini_getir, bugunku_su_kullanimina_ekle

uses_bp = Blueprint('uses', __name__)

@uses_bp.route("/shower_timer", methods=['POST'])
def shower_timer_calculate():
    veri = request.get_json()
    
    
    if not veri or "user_id" not in veri or "duration_seconds" not in veri:
        return jsonify({"error": "user_id ve duration_seconds (saniye) gönderilmelidir."}), 400
        
    user_id = veri.get("user_id")
    duration_seconds = float(veri.get("duration_seconds", 0))
    duration_minutes = duration_seconds / 60.0
    
    
    database_veri = kullanici_verilerini_getir(user_id)
    dus_basligi = "Normal duş başlığı" 
    
    if database_veri and database_veri.get("dus_basligi"):
        dus_basligi = database_veri.get("dus_basligi")
        
    try:
        
        if dus_basligi == "Eko duş başlığı":
            harcanan_su = 5.5 * duration_minutes
        else:
            harcanan_su = 17.5 * duration_minutes
            
        
        harcanan_su = round(harcanan_su, 2)
        duration_minutes = round(duration_minutes, 2)

        
        kayit_basarili_mi = bugunku_su_kullanimina_ekle(user_id, harcanan_su, "dus_banyo")

        if not kayit_basarili_mi:
            return jsonify({"error": "Veritabanına kaydedilirken bir sorun oluştu."}), 500

        
        return jsonify({
            "status": "success",
            "message": "Duş verisi bugünkü genel harcamaya eklendi! Yarın bu ekstra kullanım sıfırlanacak.",
            "data": {
                "gecen_sure_dakika": duration_minutes,
                "harcanan_su_litre": harcanan_su,
                "dus_basligi_tipi": dus_basligi
            }
        }), 200

    except Exception as e:
        print(f"Duş Sayacı Hesaplama Hatası: {e}")
        return jsonify({"error": "Hesaplama sırasında bir sorun oluştu."}), 500
    

    