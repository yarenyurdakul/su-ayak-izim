from flask import Blueprint, request, jsonify
from .database import profil_bilgilerini_getir

profil_bp = Blueprint('profil', __name__)

@profil_bp.route("/profil_getir", methods=["POST"])
def profil_getir():
    veri = request.get_json()
    user_id = veri.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "user_id gerekli"}), 400

    db_veri = profil_bilgilerini_getir(user_id)

    if not db_veri:
        return jsonify({"status": "error", "message": "Kullanıcı bulunamadı"}), 404

    # Veriler null gelirse diye varsayılan (default) değerler atıyoruz
    ad_soyad = db_veri.get("nickname") or "Belirtilmemiş"
    eposta = db_veri.get("mail") or "Belirtilmemiş"
    hane_halki = db_veri.get("evde_kac_kisi") or "Belirtilmemiş"
    
    # Senin görseldeki kullanilan_su verisini çekiyoruz!
    gunluk_tuketim = db_veri.get("kullanilan_su") 
    if gunluk_tuketim == "Belirtilmemiş" or gunluk_tuketim is None:
        hesaplanan_tuketim = 0  # Eğer anket çözülmediyse varsayılan olarak 0 gönder
    else:
        hesaplanan_tuketim = round(float(gunluk_tuketim))


    return jsonify({
        "status": "success",
        "data": {
            "ad_soyad": ad_soyad,
            "eposta": eposta,
            "konum": "İzmir, Türkiye",  
            "hane_halki": hane_halki,
            "gunluk_tuketim": hesaplanan_tuketim
        }
    })