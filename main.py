import os
import time
from typing import Optional, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Next Move Alerts", version="1.0.0")

# Next Move is intentionally standalone: no Binance keys, no trading code,
# no TradeHub imports, and no database dependency.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

TELEGRAM_TOKEN = os.getenv("NEXTMOVE_TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("NEXTMOVE_TELEGRAM_CHAT_ID", "").strip()

# Lightweight server-side duplicate guard. The browser already prevents
# threshold duplicates; this is a second safety net for accidental repeats.
_last_alert: dict[str, float] = {}
DUPLICATE_WINDOW_SECONDS = 45


class AlertPayload(BaseModel):
    symbol: str = Field(min_length=2, max_length=30)
    direction: Literal["LONG", "SHORT", "NEUTRAL"]
    timeframe: str = Field(min_length=1, max_length=10)
    probability: float = Field(ge=0, le=100)
    threshold: float = Field(default=70, ge=0, le=100)
    score: Optional[float] = None
    price: Optional[float] = None
    expected_move_pct: Optional[float] = None
    expected_price: Optional[float] = None
    room_pct: Optional[float] = None
    strength: Optional[str] = None
    bar_time: Optional[int] = None


def telegram_configured() -> bool:
    return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def fmt_num(v: Optional[float], decimals: int = 4) -> str:
    if v is None:
        return "—"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(x) >= 100:
        return f"{x:.2f}"
    if abs(x) >= 1:
        return f"{x:.4f}"
    return f"{x:.8f}".rstrip("0").rstrip(".")


def build_alert_message(p: AlertPayload) -> str:
    icon = "🟢" if p.direction == "LONG" else "🔴" if p.direction == "SHORT" else "⚪"
    lines = [
        "🚨 <b>Next Move Alert</b>",
        "",
        f"<b>{p.symbol.upper()}</b>  {icon} <b>{p.direction}</b>",
        f"الفريم: <b>{p.timeframe}</b>",
        f"الاحتمالية: <b>{p.probability:.2f}%</b>",
    ]
    if p.score is not None:
        lines.append(f"Score: <b>{p.score:+.2f}</b>")
    if p.price is not None:
        lines.append(f"السعر: <b>{fmt_num(p.price)}</b>")
    if p.expected_move_pct is not None:
        sign = "+" if p.direction == "LONG" else "-" if p.direction == "SHORT" else ""
        lines.append(f"الحركة المتوقعة: <b>{sign}{abs(p.expected_move_pct):.3f}%</b>")
    if p.expected_price is not None:
        lines.append(f"السعر المتوقع: <b>{fmt_num(p.expected_price)}</b>")
    if p.room_pct is not None and p.room_pct < 900:
        lines.append(f"Room: <b>{p.room_pct:.3f}%</b>")
    lines += ["", f"حد التنبيه المضبوط: {p.threshold:.0f}%"]
    return "\n".join(lines)


async def send_telegram(text: str) -> None:
    if not telegram_configured():
        raise HTTPException(status_code=503, detail="Next Move Telegram is not configured")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    # Small retry/backoff here as well so a brief Telegram/network hiccup
    # doesn't immediately lose an alert.
    delays = (0.0, 1.0, 2.0, 4.0)
    last_error = "Telegram request failed"
    async with httpx.AsyncClient(timeout=12.0) as client:
        for delay in delays:
            if delay:
                await __import__("asyncio").sleep(delay)
            try:
                r = await client.post(url, json=payload)
                if r.status_code == 429:
                    try:
                        retry_after = float(r.json().get("parameters", {}).get("retry_after", 1))
                    except Exception:
                        retry_after = 1
                    await __import__("asyncio").sleep(min(max(retry_after, 1), 10))
                    continue
                if r.is_success:
                    data = r.json()
                    if data.get("ok"):
                        return
                try:
                    last_error = r.json().get("description") or f"HTTP {r.status_code}"
                except Exception:
                    last_error = f"HTTP {r.status_code}"
            except Exception as exc:
                last_error = str(exc)

    raise HTTPException(status_code=502, detail=last_error)


@app.get("/")
async def root():
    return {
        "service": "Next Move Alerts",
        "status": "online",
        "trading": False,
        "telegram_configured": telegram_configured(),
    }


@app.get("/api/nextmove/health")
async def health():
    return {
        "ok": True,
        "service": "nextmove-alerts",
        "telegram_configured": telegram_configured(),
        "trading_enabled": False,
    }


@app.post("/api/nextmove/test")
async def test_telegram():
    await send_telegram(
        "✅ <b>Next Move Predictor</b>\n\nتم الاتصال بنجاح.\nهذا البوت للتنبيهات فقط ولا ينفذ أي صفقة."
    )
    return {"ok": True}


@app.post("/api/nextmove/alert")
async def alert(p: AlertPayload, request: Request):
    if p.direction == "NEUTRAL" or p.probability < p.threshold:
        return {"ok": True, "sent": False, "reason": "below_threshold_or_neutral"}

    key = f"{p.symbol.upper()}:{p.timeframe}:{p.direction}"
    now = time.time()
    last = _last_alert.get(key, 0.0)
    if now - last < DUPLICATE_WINDOW_SECONDS:
        return {"ok": True, "sent": False, "reason": "duplicate_guard"}

    await send_telegram(build_alert_message(p))
    _last_alert[key] = now
    return {"ok": True, "sent": True}
