import os

import httpx


def send_message(chat_id: str, text: str) -> dict:
    token = os.getenv("KERNEL_TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("KERNEL_TELEGRAM_TOKEN n'est pas défini (token du bot Telegram).")
    resp = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram a refusé le message : {data.get('description', resp.text)}")
    return {"message_id": data["result"]["message_id"]}
