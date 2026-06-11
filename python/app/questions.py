# app/questions.py
from flask import Blueprint, request, jsonify
from .database import veritabani_kaydet, kullanici_verilerini_getir

questions_bp = Blueprint('questions', __name__)

@questions_bp.route("/evde_kac_kisi", methods=['POST'])
def household():
    veri = request.get_json()
    user_id = veri.get("user_id")
    households = veri.get("kisi_sayisi")

    if households is None:
        return jsonify({"Hata": "Lütfen evde kaç kişinin yaşadığını giriniz."}), 400
    
    veritabani_kaydet(user_id, "evde_kac_kisi", households)
    return jsonify({"status": "success"})

@questions_bp.route("/ilce", methods=['POST'])        
def town():
    veri = request.get_json()
    user_id = veri.get("user_id")
    whichTown = veri.get("ilce")
    town_barrage = veri.get("ilce_baraj")
    
    veritabani_kaydet(user_id, "ilce", whichTown)

    baraj_isimleri = {
        1: "Tahtalı",
        2: "Balçova",
        3: "Gördes",
        4: "Alaçatı"
    }

    if town_barrage in baraj_isimleri:
        veritabani_kaydet(user_id, "ilce_baraji", baraj_isimleri[town_barrage])
    else:
        return jsonify({"hata": "Lütfen ilçe seçiminizi yapınız!"}), 400

    return jsonify({"status": "success"})



@questions_bp.route("/musluk_ayari", methods=['POST'])
def tap(): 
    veri = request.get_json()
    user_id = veri.get("user_id")
    musluk_ayari = veri.get("musluk_ayari")
    dakika = float(veri.get("musluk_dakikasi", 0))

    lowWater = 8
    midWater = 17.5
    highWater = 27

    if musluk_ayari == 1 :
        su_miktari = lowWater
    elif musluk_ayari == 2:
        su_miktari = midWater
    elif musluk_ayari == 3:
        su_miktari = highWater
    else:
        return jsonify({"status":"error","mesaj":"hata"})

    veritabani_kaydet(user_id, "kullanilan_musluk_suyu_dk", dakika)
    veritabani_kaydet(user_id, "musluk_ayari", musluk_ayari)
    veritabani_kaydet(user_id, "musluk_suyu", su_miktari)
    return jsonify({"status": "success"})

@questions_bp.route("/dis_fircalama", methods=['POST'])
def tooth():
    veri = request.get_json()
    user_id = veri.get("user_id")
    toothBrush = veri.get("dis_fircalama")

    dis_fircalama_sure = float(veri.get("fircalama_suresi", 0))
    durulama_suresi = float(veri.get("durulama_suresi", 0)) 

    veritabani_kaydet(user_id, "dis_fircalama", toothBrush)
    veritabani_kaydet(user_id, "dis_fircalama_sure", dis_fircalama_sure)
    veritabani_kaydet(user_id, "durulama_suresi", durulama_suresi)
    return jsonify({"status": "success"})

@questions_bp.route("/el_yikama", methods=['POST'])
def handWash():
    veri = request.get_json()
    user_id = veri.get("user_id")
    washSecond = veri.get("el_yikama")
    veritabani_kaydet(user_id, "el_yikama_saniye", washSecond)
    return jsonify({"status": "success"})

@questions_bp.route("/dus_basligi", methods=['POST'])
def showerHad():
    veri = request.get_json()
    user_id = veri.get("user_id")
    how_showerHad = veri.get("dus_basligi")
    dusta_suresi = float(veri.get("dus_suresi", 0))

    veritabani_kaydet(user_id, "dus_suresi", dusta_suresi)
    veritabani_kaydet(user_id, "dus_basligi", how_showerHad)
    return jsonify({"status": "success"})

@questions_bp.route("/bulasik_yontemi", methods=['POST'])
def washingUp():
    veri = request.get_json()
    user_id = veri.get("user_id")
    how_washingUp = veri.get("bulasik_yontemi")
    veritabani_kaydet(user_id, "nasil_bulasik", how_washingUp)
    return jsonify({"status": "success"})

@questions_bp.route("/ev_temizligi", methods=['POST'])
def cleaning():
    veri = request.get_json()
    user_id = veri.get("user_id")
    cleaning = veri.get("ev_temizligi")
    veritabani_kaydet(user_id, "ev_temizligi", cleaning)

    if cleaning == "akan su":
        usedWater = veri.get("musluk_kac_dk")
        veritabani_kaydet(user_id, "musluk_kac_dk", usedWater)
    return jsonify({"status": "success"})

@questions_bp.route("/bitki_sulama", methods=['POST'])
def herb():
    veri = request.get_json()
    user_id = veri.get("user_id")
    herb = veri.get("bitki_sulama") 
    veritabani_kaydet(user_id, "bitki", herb)

    if herb == True:
        bitki_sulama_litresi = float(veri.get("bitki_sulama_litresi", 0)) 
        veritabani_kaydet(user_id, "bitki_sulama_litre", bitki_sulama_litresi)
    
    return jsonify({"status": "success"})


@questions_bp.route("/ayarlari_guncelle", methods=['POST'])
def ayarlari_guncelle():
    veri = request.get_json()
    user_id = veri.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "user_id gerekli"}), 400

    try:
        # 1. DUŞ GÜNCELLEMELERİ
        if "dus_basligi" in veri:
            veritabani_kaydet(user_id, "dus_basligi", veri["dus_basligi"])
        if "dus_suresi" in veri:
            veritabani_kaydet(user_id, "dus_suresi", float(veri["dus_suresi"]))

        # 2. DİŞ FIRÇALAMA GÜNCELLEMELERİ
        if "dis_fircalama" in veri:
            veritabani_kaydet(user_id, "dis_fircalama", veri["dis_fircalama"])
        if "fircalama_suresi" in veri:
            veritabani_kaydet(user_id, "dis_fircalama_sure", float(veri["fircalama_suresi"]))
        if "durulama_suresi" in veri:
            veritabani_kaydet(user_id, "durulama_suresi", float(veri["durulama_suresi"]))

        # 3. MUSLUK AYARI 
        if "musluk_ayari" in veri:
            ayar = veri["musluk_ayari"]
            veritabani_kaydet(user_id, "musluk_ayari", ayar)
        
            if ayar == 1: su_miktari = 8
            elif ayar == 2: su_miktari = 17.5
            elif ayar == 3: su_miktari = 27
            
            veritabani_kaydet(user_id, "musluk_suyu", su_miktari)
            
        if "musluk_dakikasi" in veri:
            veritabani_kaydet(user_id, "kullanilan_musluk_suyu_dk", float(veri["musluk_dakikasi"]))

        # 4. BULAŞIK VE EV TEMİZLİĞİ
        if "bulasik_yontemi" in veri:
            veritabani_kaydet(user_id, "nasil_bulasik", veri["bulasik_yontemi"])
        if "ev_temizligi" in veri:
            veritabani_kaydet(user_id, "ev_temizligi", veri["ev_temizligi"])
        if "el_yikama" in veri:
            veritabani_kaydet(user_id, "el_yikama_saniye", veri["el_yikama"])

        # 5. BİTKİ SULAMA
        if "bitki_sulama" in veri:
            veritabani_kaydet(user_id, "bitki", veri["bitki_sulama"])
        if "bitki_sulama_litresi" in veri:
            veritabani_kaydet(user_id, "bitki_sulama_litre", float(veri["bitki_sulama_litresi"]))

        return jsonify({"status": "success", "message": "Değişiklikler başarıyla kaydedildi!"})

    except Exception as e:
        print(f"Güncelleme Hatası: {e}")
        return jsonify({"status": "error", "message": "Kayıt sırasında bir sorun oluştu."}), 500