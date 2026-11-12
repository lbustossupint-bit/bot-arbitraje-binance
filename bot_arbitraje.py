import os
import requests
import time
import threading
from flask import Flask

app = Flask(__name__)

# --- CONFIGURACIÓN DESDE ENVIRONMENT ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

try:
    UMBRAL_BRECHA_PCT = float(os.environ.get("UMBRAL_BRECHA_PCT", 1.6))
except ValueError:
    UMBRAL_BRECHA_PCT = 1.6

INTERVALO_SEGUNDOS = 30
COOLDOWN_ALERTAS = 300

bot_iniciado = False

@app.route('/')
def home():
    return "🤖 Bot de Arbitraje Binance activo 24/7."

def enviar_alerta_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERROR: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        datos = res.json()
        if not datos.get("ok"):
            print(f"❌ Error de Telegram API: {datos.get('description')}")
        else:
            print("✅ Mensaje enviado con éxito a Telegram.")
    except Exception as e:
        print(f"❌ Error al enviar mensaje a Telegram: {e}")

def obtener_precio_spot():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTARS"
    try:
        res = requests.get(url, timeout=5).json()
        if "price" in res:
            return float(res["price"])
    except Exception as e:
        print(f"⚠️ Error Spot: {e}")
    return None

def obtener_precio_p2p(trade_type="BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "asset": "USDT",
        "fiat": "ARS",
        "merchantCheck": False,
        "page": 1,
        "rows": 5,
        "payTypes": [],
        "tradeType": trade_type
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5).json()
        anuncios = res.get("data", [])
        if anuncios:
            return float(anuncios[0]["adv"]["price"])
    except Exception as e:
        print(f"⚠️ Error P2P ({trade_type}): {e}")
    return None

def iniciar_bot():
    print("🚀 Iniciando bucle de monitoreo Spot vs P2P...")
    enviar_alerta_telegram("🤖 *Bot de Arbitraje Binance desplegado en Render y activo 24/7...*")

    while True:
        try:
            precio_spot = obtener_precio_spot()
            p2p_compra = obtener_precio_p2p("BUY")
            p2p_venta = obtener_precio_p2p("SELL")

            if precio_spot and p2p_compra and p2p_venta:
                brecha_spot_a_p2p = ((p2p_venta - precio_spot) / precio_spot) * 100
                brecha_p2p_a_spot = ((precio_spot - p2p_compra) / p2p_compra) * 100

                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Spot: ${precio_spot:,.2f} | P2P Venta: ${p2p_venta:,.2f} | Brecha: {brecha_spot_a_p2p:+.2f}%")

                if abs(brecha_spot_a_p2p) >= UMBRAL_BRECHA_PCT or abs(brecha_p2p_a_spot) >= UMBRAL_BRECHA_PCT:
                    mensaje = (
                        f"⚡ *¡ALERTA DE BRECHA DETECTADA (≥ {UMBRAL_BRECHA_PCT}%)!*\n\n"
                        f"• *USDT Spot:* `${precio_spot:,.2f} ARS`\n"
                        f"• *P2P Venta (Vos vendés):* `${p2p_venta:,.2f} ARS`\n"
                        f"• *P2P Compra (Vos comprás):* `${p2p_compra:,.2f} ARS`\n\n"
                        f"📈 *Brecha (Comprar Spot ➔ Vender P2P):* `{brecha_spot_a_p2p:+.2f}%`\n"
                        f"📉 *Brecha (Comprar P2P ➔ Vender Spot):* `{brecha_p2p_a_spot:+.2f}%`"
                    )
                    enviar_alerta_telegram(mensaje)
                    time.sleep(COOLDOWN_ALERTAS)

        except Exception as e:
            print(f"❌ Error inesperado: {e}")

        time.sleep(INTERVALO_SEGUNDOS)

# --- INICIALIZACIÓN FUERA DEL IF MAIN (Para Gunicorn) ---
if not bot_iniciado:
    bot_iniciado = True
    t = threading.Thread(target=iniciar_bot)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
