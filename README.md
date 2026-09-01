# Next Move Alerts — Standalone Backend

خدمة مستقلة بالكامل عن TradeHub، وظيفتها الوحيدة استقبال تنبيه من Next Move Predictor وإرساله إلى Telegram.

## لا يحتوي المشروع على
- مفاتيح Binance
- تنفيذ أوامر تداول
- قاعدة بيانات TradeHub
- استيراد أي ملف من TradeHub

## Railway Variables
أضف داخل خدمة Next Move الجديدة فقط:

- `NEXTMOVE_TELEGRAM_TOKEN`
- `NEXTMOVE_TELEGRAM_CHAT_ID`

## التشغيل على Railway
Railway سيستخدم `Procfile` تلقائياً:

`uvicorn main:app --host 0.0.0.0 --port $PORT`

بعد النشر أنشئ Public Domain للخدمة، ثم ضع الرابط في خانة Backend داخل Next Move Predictor.

## المسارات
- `GET /api/nextmove/health`
- `POST /api/nextmove/test`
- `POST /api/nextmove/alert`

هذه الخدمة لا تستطيع فتح أو إغلاق أي صفقة لأنها لا تحتوي أي كود تداول أو مفاتيح Binance.
