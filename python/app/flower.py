from flask import Blueprint, request, jsonify
import datetime
from .database import get_db_connection, kullanici_verisi_getir, kullanici_verisi_kaydet, kullanici_verilerini_getir
from .activity import toplam_su_tuketimi_hesapla
from .izsu import get_baraj_limiti

flower_bp = Blueprint('flower', __name__)


@flower_bp.route("/su_deposu_kontrol", methods=["POST"])
def su_deposu_kontrol():
    veri = request.get_json()
    user_id = veri.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "user_id gerekli"}), 400

    toplam_harcama = toplam_su_tuketimi_hesapla(user_id)
    bugun = datetime.date.today()

# 1. ADIM: VERİTABANINDAN KULLANICI PROFİLİNİ ÇEK
    # (Kullanıcının hangi ilçede olduğu ve hangi barajı seçtiği burada yazıyor)
    kullanici_profili = kullanici_verilerini_getir(user_id)
    
    # Eğer adam uygulamaya yeni kayıt olmuşsa ve henüz ilçe/baraj seçmemişse
    # sistem patlamasın diye varsayılan olarak "Tahtalı" barajını atıyoruz.
    secilen_baraj = kullanici_profili.get("ilce_baraji", "Tahtalı") if kullanici_profili else "Tahtalı"

    # 2. ADIM: İZSU'DAN GÜNCEL LİMİTİ ÇEK (Veritabanından gelen baraj adıyla)
    gunluk_limit, risk_durumu, doluluk = get_baraj_limiti(secilen_baraj)

    # 3. ADIM: KULLANICININ O GÜNKÜ SU DURUMUNU ÇEK (Damla hesabı için)
    su_durumu = kullanici_verisi_getir(user_id)

    if su_durumu is None:
        if toplam_harcama <= gunluk_limit:
            kullanici_verisi_kaydet(user_id, toplam_harcama, bugun, su_damlasi=1, yeni_kayit_mi=True)
            return jsonify({
                "status": "success", 
                "mesaj": f"Tebrikler! İlk su damlanızı kazandınız. (Limit: {gunluk_limit}L)", 
                "toplam_harcama": toplam_harcama
            })
        else:
            kullanici_verisi_kaydet(user_id, toplam_harcama, bugun, su_damlasi=0, yeni_kayit_mi=True)
            return jsonify({
                "status": "limit_asildi", 
                "mesaj": f"Limit ({gunluk_limit}L) aşıldı, damla kazanılamadı.", 
                "toplam_harcama": toplam_harcama
            })

    else:
        son_islem = su_durumu['son_islem_tarihi']
        mevcut_damla = su_durumu['su_damlasi'] or 0

        if son_islem == bugun:
            kullanici_verisi_kaydet(user_id, toplam_harcama, bugun, su_damlasi=mevcut_damla, yeni_kayit_mi=False)
            return jsonify({
                "status": "bilgi", 
                "mesaj": "Bugünkü harcamanız güncellendi.", 
                "toplam_harcama": toplam_harcama
            })
        
        # Yeni bir gün ise dinamik limiti kontrol et
        else:
            if toplam_harcama <= gunluk_limit:
                yeni_damla = mevcut_damla + 1
                kullanici_verisi_kaydet(user_id, toplam_harcama, bugun, su_damlasi=yeni_damla, yeni_kayit_mi=False)
                return jsonify({
                    "status": "success", 
                    "mesaj": f"Yeni bir gün, yeni bir damla! Tebrikler. (Limit: {gunluk_limit}L)", 
                    "toplam_harcama": toplam_harcama
                })
            else:
                kullanici_verisi_kaydet(user_id, toplam_harcama, bugun, su_damlasi=mevcut_damla, yeni_kayit_mi=False)
                return jsonify({
                    "status": "limit_asildi", 
                    "mesaj": f"Bugünkü harcamanız {gunluk_limit} litreyi geçtiği için damla kazanamadınız.",
                    "toplam_harcama": toplam_harcama
                })


# --- ÇİÇEĞİ SULAMA ENDPOINT'İ ---

@flower_bp.route("/cicegi_sula", methods=["POST"])
def cicegi_sula():
    db = None
    try:
        gelen_veri = request.get_json(silent=True)
        if not gelen_veri or 'user_id' not in gelen_veri:
            return jsonify({"mesaj": "kullanici_id eksik!", "durum": False}), 400

        kullanici_id = gelen_veri.get('user_id')
        bugun = datetime.date.today()

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # 1. ADIM: Kullanıcının damlası var mı kontrol et
        cursor.execute("SELECT su_damlasi FROM kullanici_su_durumu WHERE kullanici_id = %s", (kullanici_id,))
        kullanici_durumu = cursor.fetchone()

        if not kullanici_durumu or (kullanici_durumu['su_damlasi'] or 0) <= 0:
            return jsonify({
                "mesaj": "Yeterli su damlanız yok! Damla kazanmak için su tasarrufu yapmalısınız.", 
                "durum": False
            }), 200
        # 2. ADIM: Damla sayısını 1 azalt
        cursor.execute("""
            UPDATE kullanici_su_durumu 
            SET su_damlasi = su_damlasi - 1 
            WHERE kullanici_id = %s
        """, (kullanici_id,))

        # 3. ADIM: Çiçeği sula (Tarihi güncelle)
        cursor.execute("SELECT * FROM cicek_durumu WHERE kullanici_id = %s", (kullanici_id,))
        cicek = cursor.fetchone()

        if cicek is None:
            # Çiçek kaydı yoksa yeni oluştur
            cursor.execute("""
                INSERT INTO cicek_durumu (kullanici_id, son_sulanma_tarihi) 
                VALUES (%s, %s)
            """, (kullanici_id, bugun))
        else:
            # Varsa tarihi bugüne çek
            cursor.execute("""
                UPDATE cicek_durumu 
                SET son_sulanma_tarihi = %s 
                WHERE kullanici_id = %s
            """, (bugun, kullanici_id))

        db.commit() # Tüm işlemleri onayla
        
        # Güncel kalan damla sayısını da gönderelim ki arayüzde (UI) hemen güncellensin
        yeni_damla_sayisi = kullanici_durumu['su_damlasi'] - 1
        
        return jsonify({
            "mesaj": "Çiçek başarıyla sulandı! 1 damla harcandı.", 
            "durum": True,
                "kalan_damla": yeni_damla_sayisi
        }), 200

    except Exception as e:
        if db: db.rollback() # Bir hata olursa yapılan değişiklikleri geri al (Güvenlik)
        print("HATA:", str(e))
        return jsonify({"mesaj": "İşlem sırasında bir hata oluştu", "durum": False}), 500
    finally:
        if db and db.is_connected():
            cursor.close()
            db.close()


@flower_bp.route("/cicek_durumu", methods=["POST"])
def cicek_durumunu_getir():
    try:
        gelen_veri = request.get_json(silent=True)
        if not gelen_veri or 'user_id' not in gelen_veri:
            return jsonify({"mesaj": "kullanici_id eksik!", "durum": False}), 400

        kullanici_id = gelen_veri.get('user_id')
        bugun = datetime.date.today()

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT son_sulanma_tarihi FROM cicek_durumu WHERE kullanici_id = %s", (kullanici_id,))
        cicek = cursor.fetchone()

        if cicek is None:
            return jsonify({
                "cicek_durumu": "mutlu",
                "sulanmayan_gun_sayisi": 0,
                "durum": True
            }), 200
        # Tarih farkını hesapla
        son_sulanma = cicek['son_sulanma_tarihi']
        
        # Eğer tarih verisi datetime formatında geldiyse direkt çıkarabiliriz
        # .days özelliği aradaki farkı tam sayı (int) olarak verir

        if isinstance(son_sulanma, str): 
            son_sulanma = datetime.datetime.strptime(son_sulanma, '%Y-%m-%d').date()

        elif isinstance(son_sulanma, datetime.datetime):
            son_sulanma = son_sulanma.date()        

        gun_farki = (bugun - son_sulanma).days

        durum_kodu = ""
        
        if gun_farki <= 1:
            # Bugün (0) veya dün (1) sulanmışsa Mutlu
            durum_kodu = "mutlu"
        elif gun_farki == 2 or gun_farki == 3:
            # 2 veya 3 gün geçmişse Üzgün
            durum_kodu = "uzgun"
        else:
            # 3 günden fazla (4, 5, 6...) geçmişse Ağlayan
            durum_kodu = "aglayan"

        return jsonify({
            "cicek_durumu": durum_kodu,
            "sulanmayan_gun_sayisi": gun_farki,
            "durum": True
        }), 200

    except Exception as e:
        print("HATA:", str(e))
        return jsonify({"mesaj": "Sunucu hatası", "durum": False}), 500
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
    


