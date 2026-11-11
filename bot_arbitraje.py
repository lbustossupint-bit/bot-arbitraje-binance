import requests
import time

# ==========================================
# ⚙️ CONFIGURACIÓN DEL BOT
# ==========================================
TELEGRAM_TOKEN = "8886172264:AAFeEb79mU-2DthvbZ1RkiyoKllTXkUTp1Q"
TELEGRAM_CHAT_ID = "862025425"

# Umbral porcentual para disparar la alerta (ej: 1.5 significa 1.5%)
UMBRAL_BRECHA_PCT = 1.6
# Frecuencia de chequeo en segundos (recomendado: 30 segundos)
INTERVALO_SEGUNDOS = 30

# Pausa tras enviar una alerta para no spammear (ej: 300 seg = 5 minutos)
COOLDOWN_ALERTAS = 300


# ==========================================
# 📡 FUNCIONES DE CONEXIÓN
# ==========================================
def enviar_alerta_telegram(mensaje):
    """Envía un mensaje formateado a tu chat de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ Error al enviar mensaje a Telegram: {e}")


def obtener_precio_spot():
    """Obtiene el último precio del par USDTARS en el mercado SPOT."""
    url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTARS"
    try:
        res = requests.get(url, timeout=5).json()
        if "price" in res:
            return float(res["price"])
    except Exception as e:
        print(f"⚠️ Error Spot: {e}")
    return None


def obtener_precio_p2p(trade_type="BUY"):
    """
    Obtiene el mejor precio del P2P de Binance.
    trade_type='BUY'  -> Precio de compra (ofertas de vendedores)
    trade_type='SELL' -> Precio de venta (ofertas de compradores)
    """
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
        "payTypes": [],  # Podés agregar ["MercadoPago"] para filtrar por medio de pago
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


# ==========================================
# 🚀 BUCLE PRINCIPAL DE MONITOREO
# ==========================================
def iniciar_bot():
    print("🚀 Bot de Arbitraje iniciado. Monitoreando Spot vs P2P...\n")
    enviar_alerta_telegram("🤖 *Bot de Arbitraje Binance iniciado y monitoreando mercado...*")

    while True:
        try:
            precio_spot = obtener_precio_spot()
            p2p_compra = obtener_precio_p2p("BUY")   # Tu precio para comprar en P2P
            p2p_venta = obtener_precio_p2p("SELL")   # Tu precio para vender en P2P

            if precio_spot and p2p_compra and p2p_venta:
                # Brecha 1: Comprar en Spot y Vender en P2P
                brecha_spot_a_p2p = ((p2p_venta - precio_spot) / precio_spot) * 100
                
                # Brecha 2: Comprar en P2P y Vender en Spot
                brecha_p2p_a_spot = ((precio_spot - p2p_compra) / p2p_compra) * 100

                # Imprimir estado en la consola local
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Spot: ${precio_spot:,.2f} | P2P Venta: ${p2p_venta:,.2f} | Brecha (Spot->P2P): {brecha_spot_a_p2p:+.2f}%")

                # Verificar si alguna brecha supera el umbral configurado
                if abs(brecha_spot_a_p2p) >= UMBRAL_BRECHA_PCT or abs(brecha_p2p_a_spot) >= UMBRAL_BRECHA_PCT:
                    mensaje = (
                        f"⚡ *¡ALERTA DE BRECHA DETECTADA!*\n\n"
                        f"• *USDT Spot:* `${precio_spot:,.2f} ARS`\n"
                        f"• *P2P Venta (Vos vendés):* `${p2p_venta:,.2f} ARS`\n"
                        f"• *P2P Compra (Vos comprás):* `${p2p_compra:,.2f} ARS`\n\n"
                        f"📈 *Brecha (Comprar Spot ➔ Vender P2P):* `{brecha_spot_a_p2p:+.2f}%`\n"
                        f"📉 *Brecha (Comprar P2P ➔ Vender Spot):* `{brecha_p2p_a_spot:+.2f}%`"
                    )
                    
                    print(f"\n🚨 Umbral superado ({UMBRAL_BRECHA_PCT}%). Enviando alerta a Telegram...")
                    enviar_alerta_telegram(mensaje)
                    
                    # Espera prolongada tras alerta para no saturar
                    print(f"⏳ Entrando en cooldown de {COOLDOWN_ALERTAS} segundos...\n")
                    time.sleep(COOLDOWN_ALERTAS)

        except Exception as e:
            print(f"❌ Error inesperado en la ejecución: {e}")

        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    iniciar_bot()