from flask import Blueprint, request, jsonify
from .database import get_db_connection
import datetime

istatistik_bp = Blueprint('istatistik', __name__)

@istatistik_bp.route("/haftalik_getir", methods=["POST"])
def haftalik_getir():
    veri = request.get_json()
    user_id = veri.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "user_id gerekli"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Veritabanı bağlantı hatası"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Veritabanından o kullanıcıya ait SON 7 GÜNÜN verisini çekiyoruz
        sql = """
        SELECT tarih, genel_toplam, dus_banyo_toplam, mutfak_toplam, temizlik_toplam 
        FROM su_gecmisi 
        WHERE kullanici_id = %s 
        ORDER BY tarih DESC 
        LIMIT 7
        """""
        cursor.execute(sql, (user_id,))
        kayitlar = cursor.fetchall()

        if not kayitlar:
            return jsonify({"status": "success", "mesaj": "Henüz veri yok", "data": None})


        haftalik_toplam = 0
        kategori_toplam = {"dus_banyo": 0, "mutfak": 0, "temizlik": 0}
        gunluk_veriler = []


        for kayit in kayitlar:
            haftalik_toplam += kayit['genel_toplam']
            kategori_toplam["dus_banyo"] += kayit['dus_banyo_toplam']
            kategori_toplam["mutfak"] += kayit['mutfak_toplam']
            kategori_toplam["temizlik"] += kayit['temizlik_toplam']

            gunluk_veriler.append({
                "tarih": kayit['tarih'].strftime("%Y-%m-%d"),
                "litre": round(kayit['genel_toplam'], 1)
            })

 
        dus_yuzde = (kategori_toplam["dus_banyo"] / haftalik_toplam) * 100 if haftalik_toplam > 0 else 0
        mutfak_yuzde = (kategori_toplam["mutfak"] / haftalik_toplam) * 100 if haftalik_toplam > 0 else 0
        temizlik_yuzde = (kategori_toplam["temizlik"] / haftalik_toplam) * 100 if haftalik_toplam > 0 else 0

        return jsonify({
            "status": "success",
            "data": {
                "haftalik_toplam": round(haftalik_toplam, 1),
                "gunluk_grafik": gunluk_veriler[::-1], 
                "kategoriler": {
                    "dus_banyo": {"litre": round(kategori_toplam["dus_banyo"], 1), "yuzde": round(dus_yuzde)},
                    "mutfak": {"litre": round(kategori_toplam["mutfak"], 1), "yuzde": round(mutfak_yuzde)},
                    "temizlik": {"litre": round(kategori_toplam["temizlik"], 1), "yuzde": round(temizlik_yuzde)}
                }
            }
        })

    except Exception as e:
        print(f"İstatistik Hatası: {e}")
        return jsonify({"status": "error", "message": "Bilinmeyen bir hata oluştu"}), 500
    finally:
        cursor.close()
        conn.close()