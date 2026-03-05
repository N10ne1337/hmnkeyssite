"""
HideMyName Keys — Flask on Vercel
Файл: api/index.py
"""

from __future__ import annotations

import os
import re
import requests
from flask import Flask, request, render_template_string
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────
#  Конфигурация
# ──────────────────────────────────────────────

MIRRORS = [
    "hidemy.name",
    "hidemy.io",
    "hidemy.net",
    "hidemyname.org",
    "hidemyna.me",
]

DEFAULT_PROXY = os.environ.get("HMN_PROXY", "")
REQUEST_TIMEOUT = 12

# Пул реалистичных User-Agent (без fake_useragent)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

DISPOSABLE_DOMAINS = {
    "temp-mail.org", "tempmail.com", "guerrillamail.com",
    "guerrillamail.net", "sharklasers.com", "grr.la",
    "mailinator.com", "yopmail.com", "yopmail.fr",
    "trashmail.com", "trashmail.me", "getnada.com",
    "10minutemail.com", "minutemail.com", "mohmal.com",
    "emailondeck.com", "dispostable.com", "maildrop.cc",
    "tempail.com", "discard.email", "discardmail.com",
    "throwaway.email", "fake-box.com", "tempinbox.com",
    "harakirimail.com", "meltmail.com", "mailnesia.com",
}

# ──────────────────────────────────────────────
#  Flask
# ──────────────────────────────────────────────

app = Flask(__name__)

# ──────────────────────────────────────────────
#  Утилиты
# ──────────────────────────────────────────────

def _random_ua() -> str:
    import random
    return random.choice(USER_AGENTS)


def _build_session(proxy: str = "") -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _random_ua(),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.7,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def _find_mirror(session: requests.Session) -> str | None:
    for domain in MIRRORS:
        url = f"https://{domain}/demo/"
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT,
                            allow_redirects=True)
            if r.status_code == 200:
                return f"https://{domain}"
        except requests.exceptions.RequestException:
            continue
    return None


def _extract_hidden_fields(soup: BeautifulSoup) -> dict:
    fields = {}
    for inp in soup.find_all("input", attrs={"type": "hidden"}):
        name = inp.get("name")
        if name:
            fields[name] = inp.get("value", "")
    return fields


def _has_email_field(soup: BeautifulSoup) -> bool:
    if soup.find("input", attrs={"name": "demo_mail"}):
        return True
    if soup.find("input", attrs={"type": "email"}):
        return True
    if soup.find("input", attrs={"class": re.compile(
            r"input.*field", re.I)}):
        return True
    if soup.find("input", attrs={"placeholder": re.compile(
            r"e-?mail", re.I)}):
        return True
    return False


def _validate_email(email: str) -> str | None:
    if not email or "@" not in email:
        return "Введите корректный email."
    domain = email.rsplit("@", 1)[-1].lower().strip()
    if domain in DISPOSABLE_DOMAINS:
        return (
            f"Домен <strong>{domain}</strong> — временная почта. "
            "Сервис их отклоняет. Используйте обычную почту."
        )
    return None


def _parse_confirmation(soup: BeautifulSoup) -> str | None:
    for sel in ["h2.title", "h2", ".message h2",
                ".result-message", ".demo-result",
                ".content h2", "p.title", ".alert"]:
        tag = soup.select_one(sel)
        if tag:
            txt = tag.get_text(strip=True)
            if txt:
                return txt
    return None


# ──────────────────────────────────────────────
#  Шаблоны (Bootstrap 5.3, тёмная тема)
# ──────────────────────────────────────────────

_HEAD = """<!DOCTYPE html>
<html lang="ru" data-bs-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet">
<title>HideMyName Keys</title>
<style>
body{min-height:100vh;display:flex;align-items:center}
.card{border:none;border-radius:1rem;box-shadow:0 .5rem 1rem rgba(0,0,0,.35)}
.card-header{border-radius:1rem 1rem 0 0!important}
</style>
</head><body><div class="container">
<div class="row justify-content-center"><div class="col-lg-5 col-md-7">"""

_TAIL = """</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js">
</script></body></html>"""

TPL_HOME = _HEAD + """
<div class="card">
  <div class="card-header bg-primary text-white text-center py-3">
    <h4 class="mb-0">🔑 HideMyName Keys</h4></div>
  <div class="card-body p-4">
    {% if error %}
      <div class="alert alert-danger">{{ error|safe }}</div>
    {% endif %}
    <form method="post" autocomplete="off">
      <div class="mb-3">
        <label class="form-label" for="email">Email</label>
        <input type="email" class="form-control" id="email"
               name="email" placeholder="you@example.com" required>
        <div class="form-text">Не используйте temp-mail и подобные.</div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="proxy">
          Прокси <small class="text-secondary">(необязательно)</small>
        </label>
        <input type="text" class="form-control" id="proxy"
               name="proxy" placeholder="socks5://user:pass@host:port"
               value="{{ proxy }}">
      </div>
      <div class="d-grid">
        <button class="btn btn-primary btn-lg" type="submit">
          Получить ключ</button>
      </div>
    </form>
  </div>
  <div class="card-footer text-center">
    <small class="text-secondary">Зеркала проверяются автоматически</small>
  </div>
</div>""" + _TAIL

TPL_OK = _HEAD + """
<div class="card">
  <div class="card-header bg-success text-white text-center py-3">
    <h4 class="mb-0">✅ Готово!</h4></div>
  <div class="card-body p-4 text-center">
    <p class="lead">Ссылка подтверждения отправлена на почту.</p>
    <p>Перейдите по ней — тестовый ключ придёт вторым письмом.</p>
    <a href="/" class="btn btn-outline-primary mt-2">← На главную</a>
  </div>
</div>""" + _TAIL

TPL_ERR = _HEAD + """
<div class="card">
  <div class="card-header bg-danger text-white text-center py-3">
    <h4 class="mb-0">⚠️ Ошибка</h4></div>
  <div class="card-body p-4">
    <div class="alert alert-warning">{{ msg|safe }}</div>
    <a href="/" class="btn btn-outline-primary">← Назад</a>
  </div>
</div>""" + _TAIL

# ──────────────────────────────────────────────
#  Роуты
# ──────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template_string(
            TPL_HOME, error=None, proxy=DEFAULT_PROXY)

    email = (request.form.get("email") or "").strip()
    proxy = (request.form.get("proxy") or DEFAULT_PROXY).strip()

    # Валидация
    err = _validate_email(email)
    if err:
        return render_template_string(TPL_HOME, error=err, proxy=proxy)

    # Сессия
    session = _build_session(proxy)

    # Зеркало
    base = _find_mirror(session)
    if not base:
        return render_template_string(TPL_ERR, msg=(
            "Ни одно зеркало не ответило.<br>"
            "Попробуйте указать прокси или повторите позже.<br>"
            f"<small>Домены: {', '.join(MIRRORS)}</small>"))

    # GET /demo/
    demo_url = f"{base}/demo/"
    try:
        demo = session.get(demo_url, timeout=REQUEST_TIMEOUT)
        demo.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return render_template_string(
            TPL_ERR, msg=f"Ошибка: {exc}")

    soup = BeautifulSoup(demo.text, "html.parser")
    if not _has_email_field(soup):
        return render_template_string(
            TPL_ERR, msg="Поле email не найдено — вёрстка изменилась.")

    # Формируем POST-данные
    data = _extract_hidden_fields(soup)
    data["demo_mail"] = email

    # Определяем URL для POST
    post_url = demo_url
    form_tag = soup.find("form")
    if form_tag and form_tag.get("action"):
        action = form_tag["action"]
        post_url = action if action.startswith("http") \
            else base + action

    session.headers["Referer"] = demo_url

    try:
        resp = session.post(post_url, data=data,
                            timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return render_template_string(
            TPL_ERR, msg=f"Ошибка отправки: {exc}")

    # Парсим ответ
    result = BeautifulSoup(resp.text, "html.parser")
    msg = _parse_confirmation(result)

    if not msg:
        return render_template_string(
            TPL_ERR, msg="Не удалось распознать ответ сервера.")

    ok_pattern = re.compile(
        r"(код\s*(выслан|отправлен)"
        r"|code\s*sent"
        r"|ссылка\s*(отправлена|выслана))",
        re.IGNORECASE)

    if ok_pattern.search(msg):
        return render_template_string(TPL_OK)

    return render_template_string(TPL_ERR, msg=(
        f"Ответ сервера: <strong>{msg}</strong><br><br>"
        "Попробуйте другой email или прокси."))


# Vercel ищет именно «app» — оставляем на уровне модуля
# Для локального запуска:
if __name__ == "__main__":
    app.run(debug=True, port=5000)
