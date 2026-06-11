from flask import Blueprint, request, jsonify
from .database import kullanici_verilerini_getir, calculate_tablosuna_kaydet, hesaplanmis_verileri_getir, gunluk_tuketim_gecmisi_kaydet

# Blueprint tanımlaması yapıyoruz (Flask app yerine)
activity_bp = Blueprint('activity', __name__)

@activity_bp.route("/calculate", methods=['POST'])
def calculate():
    veri = request.get_json()
    user_id = veri.get("user_id")
    database_veri = kullanici_verilerini_getir(user_id)
        
    try:
        dakika = float(database_veri.get("kullanilan_musluk_suyu_dk", 0))
        musluk_debi = float(database_veri.get("musluk_suyu") or 0)
        hesaplamaM = (dakika * musluk_debi)
        calculate_tablosuna_kaydet(user_id, "musluk_kullanimi", hesaplamaM)



        db_dus_dakika = float(database_veri.get("dus_suresi", 0))
        database_dus_baslik_verisi = database_veri.get("dus_basligi")
        
        if database_dus_baslik_verisi == "Normal duş başlığı":
            nDusBasligi = (17.5 * db_dus_dakika)
            calculate_tablosuna_kaydet(user_id, "dus_hesaplamasi", nDusBasligi)
        elif database_dus_baslik_verisi == "Eko duş başlığı":
            eDusBasligi = (5.5 * db_dus_dakika)
            calculate_tablosuna_kaydet(user_id, "dus_hesaplamasi", eDusBasligi)



        yesOrNo = database_veri.get("dis_fircalama")
        musluk_debi = float(database_veri.get("musluk_suyu", 0))
        dis_fircalama_sure = float(database_veri.get("dis_fircalama_sure", 0))
        durulama_suresi = float(database_veri.get("durulama_suresi", 0)) 

        if yesOrNo in [1, True, "1", "true"]:
            dis_akan_su = float(musluk_debi * dis_fircalama_sure)
            calculate_tablosuna_kaydet(user_id, "dis_fircalamada_akan_su", dis_akan_su)
        elif yesOrNo in [0, False, "0", "false"]:
            durulama_akan_su = (durulama_suresi * musluk_debi)
            calculate_tablosuna_kaydet(user_id, "dis_fircalamada_akan_su", durulama_akan_su)
        


        g_el_yikama_saniye = database_veri.get("el_yikama_saniye", 0)
        el_yikama_hesap = (g_el_yikama_saniye * 0.9)
        calculate_tablosuna_kaydet(user_id, "el_yikama_hesaplamasi", el_yikama_hesap)



        eBulasik = database_veri.get("nasil_bulasik")
        evde_yasayan_kisi = database_veri.get("evde_kac_kisi", 1)
        
        if eBulasik == "elde yıkama":
            elde_yikama_hesap = (50 / evde_yasayan_kisi)
            calculate_tablosuna_kaydet(user_id, "elde_bulasik_yikama", elde_yikama_hesap)

        elif eBulasik == "Bulaşık makinesinde":
            kisi_sayisi = database_veri.get("evde_kac_kisi") or 1
            dishwasherLitre = 10.6
            userDishwasher = round(dishwasherLitre / float(kisi_sayisi), 2)
            calculate_tablosuna_kaydet(user_id, "bulasik_makinesi", userDishwasher)





        kisi_sayisi = database_veri.get("evde_kac_kisi") or 1
        washingMachineLitre = 49.25
        userWashingMachine = round(washingMachineLitre / float(kisi_sayisi), 2)
        calculate_tablosuna_kaydet(user_id, "camasir_makinesi", userWashingMachine)


        cleaningN = database_veri.get("ev_temizligi")
        if cleaningN == "Kova ve bez":
            kova_su = 10
            calculate_tablosuna_kaydet(user_id, "ev_temizligi_hesaplama", kova_su)
        elif cleaningN == "akan su":
            akan_su_kac_dk = database_veri.get("musluk_kac_dk", 0)
            akan_su = 17.5 * akan_su_kac_dk
            calculate_tablosuna_kaydet(user_id, "ev_temizligi_hesaplama", akan_su)
    
        bitki_su = bool(database_veri.get("bitki"))
        if bitki_su == True:
            herb_veri = database_veri.get("bitki_sulama_litre", 0)
            calculate_tablosuna_kaydet(user_id, "bitki_sulama_litre_hesaplama", herb_veri)

        veriler = hesaplanmis_verileri_getir(user_id)
        if veriler:
            # 1. Duş/Banyo Kategorisi
            dus_banyo_toplam = (
                float(veriler.get("dus_hesaplamasi") or 0) +
                float(veriler.get("dis_fircalamada_akan_su") or 0) +
                float(veriler.get("el_yikama_hesaplamasi") or 0)
            )
            
            # 2. Mutfak Kategorisi
            mutfak_toplam = (
                float(veriler.get("elde_bulasik_yikama") or 0) +
                float(veriler.get("bulasik_makinesi") or 0) +
                float(veriler.get("musluk_kullanimi") or 0)
            )
            
            # 3. Temizlik Kategorisi 
            temizlik_toplam = (
                float(veriler.get("ev_temizligi_hesaplama") or 0) +
                float(veriler.get("camasir_makinesi") or 0) +
                float(veriler.get("bitki_sulama_litre_hesaplama") or 0)
            )
            
            genel_toplam = dus_banyo_toplam + mutfak_toplam + temizlik_toplam
            
            from .database import gunluk_tuketim_gecmisi_kaydet
            gunluk_tuketim_gecmisi_kaydet(user_id, genel_toplam, dus_banyo_toplam, mutfak_toplam, temizlik_toplam)

        return jsonify({"status": "success",
                        "dus_banyo_toplam":dus_banyo_toplam,
                        "mutfak_toplam":mutfak_toplam,
                        "temizlik_toplam":temizlik_toplam,
                        "genel_toplam":genel_toplam}),200
    except Exception as e:
        print(f"Hesaplama Hatası: {e}")
        return jsonify({"Hata": "Bilinmeyen Sorun"}), 500

@activity_bp.route("/get_calculate/<user_id>", methods=["GET"])
def get_calculate(user_id):    
    try:
        sonuclar = hesaplanmis_verileri_getir(user_id)
        if not sonuclar:
            return jsonify({"error": "Kullanıcıya ait hesaplanmış veriler bulunamadı"}), 404
        return jsonify({"status": "success", "data": sonuclar}), 200
    except:
        return jsonify({"hata": "sonuçlarla ilgili bir sorun oluştu."}), 500

def toplam_su_tuketimi_hesapla(user_id):
    veriler = hesaplanmis_verileri_getir(user_id)
    if not veriler: return 0
    toplam = (
        float(veriler.get("musluk_kullanimi") or 0) +
        float(veriler.get("dus_hesaplamasi") or 0) +
        float(veriler.get("dis_fircalamada_akan_su") or 0) +
        float(veriler.get("el_yikama_hesaplamasi") or 0) +
        float(veriler.get("elde_bulasik_yikama") or 0) +
        float(veriler.get("bulasik_makinesi") or 0) +  
        float(veriler.get("camasir_makinesi") or 0) +  
        float(veriler.get("ev_temizligi_hesaplama") or 0) +
        float(veriler.get("bitki_sulama_litre_hesaplama") or 0)
    )
    return toplam