from __future__ import annotations
from typing import List, Optional

async def send_low_stock_email(request_app, to_list: List[str], item_name: str, count: int, low_limit: int, warehouse_name: str):
    if request_app is None:
        from server import app as request_app

    mailcfg = request_app.state.mailcfg
    from asfeslib.net.mail import MailClient

    subject = f"Низкий остаток: {item_name}"
    text = (
        f"На складе '{warehouse_name}' низкий остаток товара '{item_name}'.\n"
        f"Текущее количество: {count}\n"
        f"Порог: {low_limit}\n"
    )

    client = MailClient(mailcfg)
    try:
        await client.send(to_list, subject, text)
    except Exception:
        pass
