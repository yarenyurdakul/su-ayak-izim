
import mysql.connector
import os
import datetime 

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),       
        user=os.getenv("DB_USER"),            
        password=os.getenv("DB_PASSWORD"),    
        database=os.getenv("DB_NAME") ,
        charset='utf8mb4',
        use_pure=True
    )

def kullanici_verilerini_getir(user_id):
    if not user_id: return None
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True) 
        sql = "SELECT * FROM answers WHERE kullanici_id = %s"
        cursor.execute(sql, (user_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"VERİ ÇEKME HATASI: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def veritabani_kaydet(user_id, kolon_adi, deger):
    if user_id is None: return
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT idanswers FROM answers WHERE kullanici_id = %s", (user_id,))
        kayit = cursor.fetchone()
        if kayit:
            sql = f"UPDATE answers SET {kolon_adi} = %s WHERE kullanici_id = %s"
            cursor.execute(sql, (deger, user_id))
        else:
            sql = f"INSERT INTO answers (kullanici_id, {kolon_adi}) VALUES (%s, %s)"
            cursor.execute(sql, (user_id, deger))
        conn.commit() 
    except Exception as e:
        print(f"VERİTABANI KAYIT HATASI: {e}")
    finally:
        cursor.close()
        conn.close()

def calculate_tablosuna_kaydet(user_id, kolon_adi, deger):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = f"""
            INSERT INTO calculate (kullanici_id, {kolon_adi}) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE {kolon_adi} = %s
        """
        cursor.execute(sql, (user_id, deger, deger))
        conn.commit()
    except Exception as e:
        print(f"CALCULATE KAYIT HATASI: {e}")
    finally:
        cursor.close()
        conn.close()

def hesaplanmis_verileri_getir(user_id):
    if not user_id: return {}
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True) 
        sql = "SELECT * FROM calculate WHERE kullanici_id = %s"
        cursor.execute(sql, (user_id,))
        sonuc = cursor.fetchone()
        return sonuc if sonuc else {}
    except Exception as e:
        print(f"CALCULATE VERİ ÇEKME HATASI: {e}")
        return {}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- ÇİÇEK VE SU DAMLASI VERİTABANI FONKSİYONLARI ---
def kullanici_verisi_getir(kullanici_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT kullanilan_su, son_islem_tarihi, su_damlasi FROM kullanici_su_durumu WHERE kullanici_id = %s", 
            (kullanici_id,)
        )
        return cursor.fetchone()
    except Exception as err:
        print(f"Hata oluştu: {err}")
        return None
    finally:
        cursor.close()
        db.close()

def kullanici_verisi_kaydet(kullanici_id, kullanilan_su, islem_tarihi, su_damlasi, yeni_kayit_mi=False):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        if yeni_kayit_mi:
            cursor.execute("""
                INSERT INTO kullanici_su_durumu (kullanici_id, kullanilan_su, son_islem_tarihi, su_damlasi) 
                VALUES (%s, %s, %s, %s)
            """, (kullanici_id, kullanilan_su, islem_tarihi, su_damlasi))
        else:
            cursor.execute("""
                UPDATE kullanici_su_durumu 
                SET kullanilan_su = %s, son_islem_tarihi = %s, su_damlasi = %s
                WHERE kullanici_id = %s
            """, (kullanilan_su, islem_tarihi, su_damlasi, kullanici_id))
        
        db.commit()
    except Exception as err:
        print(f"Hata oluştu: {err}")
    finally:
        cursor.close()
        db.close()



def profil_bilgilerini_getir(user_id):
    conn = get_db_connection()
    if conn is None: return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        # 3 Tabloyu (Users, answers, kullanici_su_durumu) birbirine bağlıyoruz
        sql = """
        SELECT u.nickname, u.mail, a.evde_kac_kisi, k.kullanilan_su
        FROM Users u
        LEFT JOIN answers a ON u.id = a.kullanici_id
        LEFT JOIN kullanici_su_durumu k ON u.id = k.kullanici_id
        WHERE u.id = %s
        """
        cursor.execute(sql, (user_id,))
        result = cursor.fetchone()
        return result
    except Exception as e:
        print(f"Profil Verisi Çekme Hatası: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def gunluk_tuketim_gecmisi_kaydet(user_id, toplam, dus, mutfak, temizlik):
    conn = get_db_connection()
    if not conn: return
    
    cursor = conn.cursor()
    bugun = datetime.date.today()
    
    try:
        # "id" yerine "kullanici_id" ile kontrol et
        sql_check = "SELECT kullanici_id FROM su_gecmisi WHERE kullanici_id = %s AND tarih = %s"
        cursor.execute(sql_check, (user_id, bugun))
        kayit = cursor.fetchone()
        
        if kayit:
            sql_update = """UPDATE su_gecmisi 
                            SET genel_toplam=%s, dus_banyo_toplam=%s, mutfak_toplam=%s, temizlik_toplam=%s 
                            WHERE kullanici_id=%s AND tarih=%s"""
            cursor.execute(sql_update, (toplam, dus, mutfak, temizlik, user_id, bugun))
        else:
            sql_insert = """INSERT INTO su_gecmisi 
                            (kullanici_id, tarih, genel_toplam, dus_banyo_toplam, mutfak_toplam, temizlik_toplam) 
                            VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql_insert, (user_id, bugun, toplam, dus, mutfak, temizlik))
            
        conn.commit()
    except Exception as e:
        print(f"Geçmiş Kayıt Hatası: {e}")
    finally:
        cursor.close()
        conn.close()


def bugunku_su_kullanimina_ekle(user_id, ekstra_litre, kategori="dus_banyo"):
    conn = get_db_connection()
    if not conn: return False
    
    cursor = conn.cursor(dictionary=True)
    bugun = datetime.date.today()
    
    try:
  
        sql_check = "SELECT genel_toplam, dus_banyo_toplam FROM su_gecmisi WHERE kullanici_id = %s AND tarih = %s"
        cursor.execute(sql_check, (user_id, bugun))
        kayit = cursor.fetchone()
        
        if kayit:
       
            # (Veritabanındaki NULL değerleri patlamasın diye 'or 0' kullandık)
            yeni_toplam = (kayit['genel_toplam'] or 0) + ekstra_litre
            yeni_dus = (kayit['dus_banyo_toplam'] or 0) + ekstra_litre
            
            # WHERE koşulunu tablonuzdaki Primary Key'lere (kullanici_id ve tarih) göre güncelledik.
            sql_update = """UPDATE su_gecmisi 
                            SET genel_toplam = %s, dus_banyo_toplam = %s 
                            WHERE kullanici_id = %s AND tarih = %s"""
            cursor.execute(sql_update, (yeni_toplam, yeni_dus, user_id, bugun))
            
        else:
        
            sql_insert = """INSERT INTO su_gecmisi (kullanici_id, tarih, genel_toplam, dus_banyo_toplam, mutfak_toplam, temizlik_toplam) 
                            VALUES (%s, %s, %s, %s, 0, 0)"""
            cursor.execute(sql_insert, (user_id, bugun, ekstra_litre, ekstra_litre))
            
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Günlük Kullanıma Ekleme Hatası: {e}")
        return False
        
    finally:
        cursor.close()
        conn.close()