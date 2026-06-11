from flask import Blueprint, request, jsonify
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import datetime
import os


weather_bp = Blueprint('weather', __name__)

# Open-Meteo'nun WMO (Dünya Meteoroloji Örgütü) kodlarını Türkçeye çeviren fonksiyon
def hava_durumu_metni_getir(kod, gunduz_mu):
    if kod == 0:
        return "Güneşli" if gunduz_mu else "Açık"
    elif kod in [1, 2, 3]:
        if kod == 1: return "Az Bulutlu"
        elif kod == 2: return "Parçalı Bulutlu"
        else: return "Çok Bulutlu"
    elif kod in [45, 48]:
        return "Sisli"
    elif kod in [51, 53, 55, 56, 57]:
        return "Çisenti"
    elif kod in [61, 63, 65, 66, 67]:
        return "Yağmurlu"
    elif kod in [71, 73, 75, 77]:
        return "Kar Yağışlı"
    elif kod in [80, 81, 82]:
        return "Sağanak Yağışlı"
    elif kod in [85, 86]:
        return "Yoğun Kar"
    elif kod in [95, 96, 99]:
        return "Fırtınalı / Gök Gürültülü"
    else:
        return "Bilinmiyor"

@weather_bp.route("/weather", methods=["POST","GET"])
def weather():
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 38.4127, 
        "longitude": 27.1384,
        "hourly": ["temperature_2m", "precipitation_probability", "precipitation", "rain", "snowfall", "is_day", "weather_code"],
        "timezone": "auto",
        "forecast_days": 1
    }
    
    try:
        responses = openmeteo.weather_api(url, params = params)
        response = responses[0]

        hourly = response.Hourly()
        
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
        hourly_rain = hourly.Variables(3).ValuesAsNumpy()
        hourly_snowfall = hourly.Variables(4).ValuesAsNumpy()
        hourly_is_day = hourly.Variables(5).ValuesAsNumpy()
        hourly_weather_code = hourly.Variables(6).ValuesAsNumpy() 

        dates = pd.date_range(
            start = pd.to_datetime(hourly.Time() + response.UtcOffsetSeconds(), unit = "s", utc = True),
            end = pd.to_datetime(hourly.TimeEnd() + response.UtcOffsetSeconds(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        )

        saatlik_veriler = []

        for i in range(len(dates)):
            is_day = bool(hourly_is_day[i])
            wmo_kodu = int(hourly_weather_code[i])
            durum_metni = hava_durumu_metni_getir(wmo_kodu, is_day)
            
   
            yagmur_ihtimali_degeri = int(hourly_precipitation_probability[i])
            

            # if yagmur_ihtimali_degeri >= 10:
            #     yuz_ifadesi = "mutlu"
            # else:
            #     yuz_ifadesi = "üzgün"

            saatlik_veriler.append({
                "saat": dates[i].strftime('%H:%M'),
                "sicaklik": round(float(hourly_temperature_2m[i]), 1),
                "yagmur_ihtimali": yagmur_ihtimali_degeri,
                "toplam_yagis": round(float(hourly_precipitation[i]), 2),
                "yagmur_miktari": round(float(hourly_rain[i]), 2),
                "kar_miktari": round(float(hourly_snowfall[i]), 2),
                "gunduz_mu": is_day,
                "durum_metni": durum_metni,
                "durum_kodu": wmo_kodu,
                # "emoji": yuz_ifadesi  
            })

            suanki_saat = datetime.datetime.now().hour
        

        if suanki_saat < len(saatlik_veriler):
            guncel_hava = saatlik_veriler[suanki_saat]
        else:
            guncel_hava = saatlik_veriler[0]

        return jsonify({
            "status": "success",
            "tarih": dates[0].strftime('%d.%m.%Y'),
            
            
            "hava_derece": guncel_hava["sicaklik"],
            "hava_durumu": guncel_hava["durum_metni"],
            "yagis_orani": guncel_hava["yagmur_ihtimali"],
            
         
            "data": saatlik_veriler
        }), 200

    except Exception as e:
        print(f"Hava durumu çekilirken hata: {e}")
        return jsonify({"error": "Hava durumu bilgisi alinamadi"}), 500

