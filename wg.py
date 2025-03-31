import requests
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import os
import argparse
import matplotlib.pyplot as plt
from gtts import gTTS
import playsound

# โหลดค่าจากไฟล์ .env
load_dotenv()

# ตั้งค่าการบันทึก log
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ฟังก์ชันดึงข้อมูลจาก OpenWeatherMap API
def get_weather_data(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)  # เพิ่ม timeout
        response.raise_for_status()  # ตรวจสอบสถานะ HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        return None

# ฟังก์ชันตรวจสอบสถานการณ์พายุ
def check_storm_condition(weather_data):
    try:
        weather = weather_data['weather'][0]['main']
        temp = weather_data['main']['temp']
        wind_speed = weather_data['wind']['speed']
        storm_warning = False
        alert_level = None

        # ตรวจสอบพายุจากข้อมูล
        if weather == "Thunderstorm" or wind_speed > 15:
            storm_warning = True
            alert_level = "สูง"
        elif weather == "Rain" or wind_speed > 10:
            storm_warning = True
            alert_level = "ปานกลาง"
        elif weather == "Clear" and temp > 40:
            storm_warning = True
            alert_level = "อันตรายจากความร้อน"
        
        return storm_warning, weather, temp, wind_speed, alert_level

    except KeyError as e:
        logging.error(f"ข้อมูลผิดพลาด: {e}")
        return False, None, None, None, None

# ฟังก์ชันแจ้งเตือนผ่าน LINE Notify
def send_line_notify(message, token):
    headers = {'Authorization': 'Bearer ' + token}
    payload = {'message': message}
    try:
        response = requests.post('https://notify-api.line.me/api/notify', headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        return response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"เกิดข้อผิดพลาดในการส่งแจ้งเตือน: {e}")
        return None

# ฟังก์ชันสร้างข้อความแจ้งเตือน
def create_alert_message(city, weather, temp, wind_speed, alert_level):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"⚠️ สถานการณ์พายุใน {city} ⚠️\n"
    message += f"เวลาปัจจุบัน: {current_time}\n"
    message += f"สภาพอากาศ: {weather}\n"
    message += f"อุณหภูมิ: {temp}°C\n"
    message += f"ความเร็วลม: {wind_speed} m/s\n"
    message += f"ระดับการเตือนภัย: {alert_level}\n"
    message += "โปรดระวังและเตรียมตัวให้พร้อม!"
    return message

# ฟังก์ชันสร้างข้อความส่งข้อมูลสภาพอากาศทั้งหมด
def create_weather_report(city, weather_data):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🌍 สภาพอากาศปัจจุบันใน {city} 🌍\n"
    message += f"เวลาปัจจุบัน: {current_time}\n"
    message += f"สภาพอากาศ: {weather_data['weather'][0]['description']}\n"
    message += f"อุณหภูมิ: {weather_data['main']['temp']}°C\n"
    message += f"ความชื้น: {weather_data['main']['humidity']}%\n"
    message += f"ความดัน: {weather_data['main']['pressure']} hPa\n"
    message += f"ความเร็วลม: {weather_data['wind']['speed']} m/s\n"
    message += f"ทิศทางลม: {weather_data['wind']['deg']}°\n"
    return message

# ฟังก์ชันบันทึกข้อมูลสภาพอากาศลงไฟล์
def log_weather_data(city, weather, temp, wind_speed, alert_level):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        'time': current_time,
        'city': city,
        'weather': weather,
        'temp': temp,
        'wind_speed': wind_speed,
        'alert_level': alert_level
    }
    try:
        with open('weather_log.json', 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
        logging.info("บันทึกข้อมูลสภาพอากาศสำเร็จ")
    except IOError as e:
        logging.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# ฟังก์ชันแสดงข้อมูลสภาพอากาศในรูปแบบกราฟ
def plot_weather_data(log_file='weather_log.json'):
    try:
        times, temps, wind_speeds = [], [], []

        with open(log_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                times.append(entry['time'])
                temps.append(entry['temp'])
                wind_speeds.append(entry['wind_speed'])

        plt.figure(figsize=(10, 5))
        plt.plot(times, temps, label='Temperature (°C)', color='red')
        plt.plot(times, wind_speeds, label='Wind Speed (m/s)', color='blue')
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.title('Weather Data Over Time')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการสร้างกราฟ: {e}")

# ฟังก์ชันตรวจสอบคุณภาพอากาศ (AQI)
def get_air_quality_data(lat, lon, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลคุณภาพอากาศ: {e}")
        return None

def check_air_quality(aqi_data):
    try:
        aqi = aqi_data['list'][0]['main']['aqi']
        aqi_levels = {
            1: "ดีมาก",
            2: "ดี",
            3: "ปานกลาง",
            4: "แย่",
            5: "แย่มาก"
        }
        return aqi, aqi_levels.get(aqi, "ไม่ทราบระดับ")
    except KeyError as e:
        logging.error(f"ข้อมูล AQI ผิดพลาด: {e}")
        return None, None

# ฟังก์ชันส่งข้อความเสียง
def send_voice_alert(message, language='th'):
    try:
        tts = gTTS(text=message, lang=language)
        tts.save("alert.mp3")
        playsound.playsound("alert.mp3")
        logging.info("ส่งข้อความเสียงสำเร็จ!")
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการส่งข้อความเสียง: {e}")

# ฟังก์ชันหลักสำหรับเช็คสถานการณ์พายุและส่งการแจ้งเตือน
def storm_warning_system(city, api_key, line_token):
    logging.info(f"กำลังตรวจสอบพายุใน {city}...")
    weather_data = get_weather_data(city, api_key)

    if weather_data:
        storm_warning, weather, temp, wind_speed, alert_level = check_storm_condition(weather_data)

        if storm_warning:
            logging.warning(f"เตือนภัย: พายุระดับ {alert_level} อาจจะใกล้เข้ามา!")
            message = create_alert_message(city, weather, temp, wind_speed, alert_level)
            status = send_line_notify(message, line_token)
            send_voice_alert(message)

            log_weather_data(city, weather, temp, wind_speed, alert_level)

            if status == 200:
                logging.info("ส่งการแจ้งเตือนสำเร็จ!")
            else:
                logging.error("ไม่สามารถส่งการแจ้งเตือนได้")
        else:
            logging.info("สภาพอากาศปกติ ไม่มีพายุเกิดขึ้น")

        weather_report = create_weather_report(city, weather_data)
        send_line_notify(weather_report, line_token)
    else:
        logging.error("ไม่สามารถดึงข้อมูลสภาพอากาศ")

# ฟังก์ชันเริ่มต้นการตรวจสอบในระยะเวลาที่กำหนด
def start_weather_check(city, api_key, line_token, interval=3600):
    while True:
        storm_warning_system(city, api_key, line_token)
        time.sleep(interval)

# เริ่มต้นโปรแกรม
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ระบบแจ้งเตือนพายุ")
    parser.add_argument("--city", type=str, default="Changwat Chachoengsao", help="ชื่อเมืองที่ต้องการตรวจสอบ")
    parser.add_argument("--interval", type=int, default=1800, help="ระยะเวลาการตรวจสอบ (วินาที)")
    parser.add_argument("--plot", action="store_true", help="แสดงกราฟข้อมูลสภาพอากาศ")
    args = parser.parse_args()

    city = args.city
    interval = args.interval
    api_key = os.getenv("API_KEY")
    line_token = os.getenv("LINE_TOKEN")

    if not api_key or not line_token:
        logging.error("กรุณาใส่ API Key และ LINE Token ในไฟล์ .env")
    else:
        if args.plot:
            plot_weather_data()
        else:
            start_weather_check(city, api_key, line_token, interval)