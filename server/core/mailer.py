from __future__ import annotations

from typing import List
from datetime import datetime, timezone
import html as _html
import logging

from server.core.config import settings

logger = logging.getLogger("mailer")


def _render_low_stock_html(
    *,
    item_name: str,
    count: int,
    low_limit: int,
    warehouse_name: str,
) -> str:
    item_name_h = _html.escape(item_name or "—")
    warehouse_h = _html.escape(warehouse_name or "—")
    now_str = datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")

    dashboard_url = f"https://{settings.DOMAIN}/"

    return f"""\
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Низкий остаток</title>
  </head>
  <body style="margin:0;padding:0;background:#0b0d14;color:#e7eaf6;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0d14;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0"
                 style="width:600px;max-width:92vw;background:#12172b;border:1px solid #252b43;border-radius:18px;overflow:hidden;">
            
            <!-- Header -->
            <tr>
              <td style="padding:18px 20px;background:#0f1326;border-bottom:1px solid #252b43;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="font-size:18px;font-weight:800;letter-spacing:.4px;">
                      ASFES Warehouse
                    </td>
                    <td align="right" style="font-size:12px;color:#a8b0cf;">
                      {now_str}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding:20px;">
                <div style="font-size:20px;font-weight:800;margin-bottom:6px;">
                  Низкий остаток товара
                </div>

                <div style="color:#a8b0cf;font-size:14px;margin-bottom:14px;">
                  На складе <b style="color:#e7eaf6;">{warehouse_h}</b>
                  остаток ниже порога.
                </div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                       style="background:#0f1326;border:1px solid #252b43;border-radius:14px;">
                  <tr>
                    <td style="padding:14px 16px;">
                      <div style="font-size:14px;color:#a8b0cf;">Товар</div>
                      <div style="font-size:18px;font-weight:700;">{item_name_h}</div>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:0 16px 14px;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td width="50%" style="padding:8px 0;">
                            <div style="font-size:12px;color:#a8b0cf;">Текущее количество</div>
                            <div style="font-size:22px;font-weight:800;color:#ff5c7a;">{count}</div>
                          </td>
                          <td width="50%" style="padding:8px 0;">
                            <div style="font-size:12px;color:#a8b0cf;">Порог low-stock</div>
                            <div style="font-size:22px;font-weight:800;">{low_limit}</div>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <div style="height:12px;"></div>

                <div style="font-size:13px;color:#a8b0cf;line-height:1.6;">
                  Рекомендуем пополнить запас в ближайшее время.
                </div>

                <div style="height:18px;"></div>

                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center" style="background:#7b61ff;border-radius:10px;">
                      <a href="{dashboard_url}"
                         style="display:inline-block;padding:10px 14px;color:#ffffff;text-decoration:none;font-weight:700;font-size:14px;">
                        Открыть дашборд
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:14px 20px;border-top:1px solid #252b43;font-size:12px;color:#a8b0cf;">
                Это автоматическое уведомление ASFES Warehouse System.<br/>
                Если вы не ожидаете такие письма — проверьте настройки уведомлений склада.
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


async def send_low_stock_email(
    request_app,
    to_list: List[str],
    item_name: str,
    count: int,
    low_limit: int,
    warehouse_name: str,
):
    if request_app is None:
        from server import app as request_app

    mailcfg = request_app.state.mailcfg

    from asfeslib.net.mail import MailClient, MailMessage

    subject = f"Низкий остаток: {item_name}"
    html_body = _render_low_stock_html(
        item_name=item_name,
        count=count,
        low_limit=low_limit,
        warehouse_name=warehouse_name,
    )

    msg = MailMessage(
        to=to_list,
        subject=subject,
        body=html_body,
        html=True,
    )

    client = MailClient(mailcfg)
    try:
        await client.send(msg)
    except Exception as e:
        logger.exception("send_low_stock_email failed: %r", e)
