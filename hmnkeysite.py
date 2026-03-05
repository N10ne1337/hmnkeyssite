"""
hmnkeysite.py — Flask-приложение для получения тестовых ключей HideMyName.
Совместимо с Vercel (@vercel/python) и локальным запуском.
"""

import os
import re
import requests
from flask import Flask, request, render_template_string
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────
#  Конфигурация
# ──────────────────────────────────────────────

# Список зеркал — проверяются по очереди, пока не ответит одно
MIRRORS = [
    "hidemy.name",
    "hidemy.io",
    "hidemy.net",
    "hidemyname.org",
    "hidemyna.me",
]

# Прокси (опционально). Можно задать через переменную окружения:
#   export HMN_PROXY="socks5://user:pass@host:port"
#   export HMN_PROXY="http://host:port"
DEFAULT_PROXY = os.environ.get("HMN_PROXY", "")

# Таймаут на каждый запрос (сек.)
REQUEST_TIMEOUT = 15

# Домены временных почт, которые HideMyName отклоняет
DISPOSABLE_EMAIL_DOMAINS = {
    "temp-mail.org", "tempmail.com", "guerrillamail.com",
    "guerrillamail.net", "sharklasers.com", "grr.la",
    "guerrillamailblock.com", "pokemail.net", "spam4.me",
    "throwaway.email", "mailinator.com", "yopmail.com",
    "yopmail.fr", "trashmail.com", "trashmail.me",
    "mohmal.com", "getnada.com", "tempail.com",
    "10minutemail.com", "10minutemail.net", "minutemail.com",
    "tempmailo.com", "emailondeck.com", "fake-box.com",
    "dispostable.com", "maildrop.cc", "mailnesia.com",
    "tempr.email", "discard.email", "discardmail.com",
    "mailcatch.com", "tempinbox.com", "meltmail.com",
    "harakirimail.com", "crazymailing.com", "binkmail.com",
}

# ──────────────────────────────────────────────
#  Flask app
# ──────────────────────────────────────────────

app = Flask(__name__)

# ──────────────────────────────────────────────
#  Вспомогательные функции
# ──────────────────────────────────────────────

def _build_session(proxy: str = "") -> requests.Session:
    """Создаёт requests.Session с реалистичными заголовками и (опционально) прокси."""
    ua = UserAgent()
    session = requests.Session()
    session.headers.update({
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.7,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session


def _find_working_mirror(session: requests.Session) -> str | None:
    """Перебирает зеркала и возвращает первый откликнувшийся базовый URL."""
    for domain in MIRRORS:
        url = f"https://{domain}/demo/"
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                # Сохраняем реальный домен (после редиректов)
                return f"https://{domain}"
        except requests.exceptions.RequestException:
            continue
    return None


def _extract_csrf(soup: BeautifulSoup) -> dict:
    """Ищет скрытые поля формы (CSRF-токен, middleware-token и т.п.)."""
    hidden_fields = {}
    for inp in soup.find_all("input", attrs={"type": "hidden"}):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            hidden_fields[name] = value
    return hidden_fields


def _find_email_input(soup: BeautifulSoup) -> bool:
    """Проверяет наличие поля ввода email на странице (гибкий поиск)."""
    # Вариант 1: по имени
    field = soup.find("input", attrs={"name": "demo_mail"})
    if field:
        return True
    # Вариант 2: по типу email
    field = soup.find("input", attrs={"type": "email"})
    if field:
        return True
    # Вариант 3: по классу (старая вёрстка)
    field = soup.find("input", attrs={"class": re.compile(r"input.*field", re.I)})
    if field:
        return True
    # Вариант 4: по placeholder
    field = soup.find("input", attrs={"placeholder": re.compile(r"e-?mail", re.I)})
    if field:
        return True
    return False


def _validate_email(email: str) -> str | None:
    """Возвращает сообщение об ошибке или None, если email допустим."""
    if not email or "@" not in email:
        return "Введите корректный email-адрес."
    domain = email.rsplit("@", 1)[-1].lower().strip()
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        return (
            f"Домен <strong>{domain}</strong> входит в список временных почт, "
            "которые отклоняются сервисом. Используйте постоянную почту."
        )
    return None


def _parse_confirmation(soup: BeautifulSoup) -> str | None:
    """Гибко ищет текст подтверждения на странице ответа."""
    # Приоритетные селекторы (от нового к старому макету)
    selectors = [
        "h2.title",
        "h2",
        ".message h2",
        ".result-message",
        ".demo-result",
        ".content h2",
        "p.title",
    ]
    for sel in selectors:
        tag = soup.select_one(sel)
        if tag:
            text = tag.get_text(strip=True)
            if text:
                return text
    return None


# ──────────────────────────────────────────────
#  HTML-шаблоны (Bootstrap 5)
# ──────────────────────────────────────────────

LAYOUT_HEAD = """
<!DOCTYPE html>
<html lang="ru" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet"
        integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YcnS/1TlKAppNJg3teh8ifhNnFb4iDCVYedc"
        crossorigin="anonymous">
  <title>HideMyName Keys</title>
  <style>
    body { min-height: 100vh; display: flex; align-items: center; }
    .card { border: none; border-radius: 1rem; box-shadow: 0 .5rem 1rem rgba(0,0,0,.35); }
    .card-header { border-radius: 1rem 1rem 0 0 !important; }
    .btn-primary { border-radius: .5rem; }
    small.text-secondary { font-size: .78rem; }
  </style>
</head>
<body>
<div class="container">
  <div class="row justify-content-center">
    <div class="col-lg-5 col-md-7">
"""

LAYOUT_TAIL = """
    </div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
        crossorigin="anonymous"></script>
</body>
</html>
"""

HOME_TEMPLATE = (
    LAYOUT_HEAD
    + """
<div class="card">
  <div class="card-header bg-primary text-white text-center py-3">
    <h4 class="mb-0">🔑 HideMyName Keys</h4>
  </div>
  <div class="card-body p-4">
    {% if error %}
      <div class="alert alert-danger">{{ error | safe }}</div>
    {% endif %}
    <form method="post" autocomplete="off">
      <div class="mb-3">
        <label for="email" class="form-label">Email-адрес</label>
        <input type="email" class="form-control" id="email" name="email"
               placeholder="you@example.com" required>
        <div class="form-text">
          Не используйте <em>temp-mail, mailinator</em> и подобные сервисы.
        </div>
      </div>
      <div class="mb-3">
        <label for="proxy" class="form-label">Прокси <span class="text-secondary">(необязательно)</span></label>
        <input type="text" class="form-control" id="proxy" name="proxy"
               placeholder="socks5://user:pass@host:port"
               value="{{ default_proxy }}">
        <div class="form-text">
          Если IP сервера заблокирован — укажите HTTPS/SOCKS5-прокси.
        </div>
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-primary btn-lg">Получить тестовый ключ</button>
      </div>
    </form>
  </div>
  <div class="card-footer text-center">
    <small class="text-secondary">
      Скрипт перебирает актуальные зеркала автоматически.
    </small>
  </div>
</div>
"""
    + LAYOUT_TAIL
)

SUCCESS_TEMPLATE = (
    LAYOUT_HEAD
    + """
<div class="card">
  <div class="card-header bg-success text-white text-center py-3">
    <h4 class="mb-0">✅ Готово!</h4>
  </div>
  <div class="card-body p-4 text-center">
    <p class="lead">Ссылка подтверждения отправлена на почту.</p>
    <p>Перейдите по ней — после этого тестовый ключ придёт вторым письмом.</p>
    <a href="/" class="btn btn-outline-primary mt-2">← На главную</a>
  </div>
</div>
"""
    + LAYOUT_TAIL
)

ERROR_TEMPLATE = (
    LAYOUT_HEAD
    + """
<div class="card">
  <div class="card-header bg-danger text-white text-center py-3">
    <h4 class="mb-0">⚠️ Ошибка</h4>
  </div>
  <div class="card-body p-4">
    <div class="alert alert-warning mb-3">{{ message | safe }}</div>
    <a href="/" class="btn btn-outline-primary">← Назад</a>
  </div>
</div>
"""
    + LAYOUT_TAIL
)

# ──────────────────────────────────────────────
#  Роуты
# ──────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template_string(
            HOME_TEMPLATE, error=None, default_proxy=DEFAULT_PROXY
        )

    # ── POST ─────────────────────────────────
    email = (request.form.get("email") or "").strip()
    proxy = (request.form.get("proxy") or DEFAULT_PROXY).strip()

    # 1. Валидация email
    email_error = _validate_email(email)
    if email_error:
        return render_template_string(
            HOME_TEMPLATE, error=email_error, default_proxy=proxy
        )

    # 2. Готовим сессию (cookies + заголовки сохраняются)
    session = _build_session(proxy)

    # 3. Ищем рабочее зеркало
    base_url = _find_working_mirror(session)
    if not base_url:
        return render_template_string(
            ERROR_TEMPLATE,
            message=(
                "Ни одно зеркало не ответило. "
                "Попробуйте указать прокси или повторите позже.<br>"
                f"<small>Проверенные домены: {', '.join(MIRRORS)}</small>"
            ),
        )

    # 4. Загружаем страницу /demo/ (cookies + CSRF)
    demo_url = f"{base_url}/demo/"
    try:
        demo_resp = session.get(demo_url, timeout=REQUEST_TIMEOUT)
        demo_resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return render_template_string(
            ERROR_TEMPLATE,
            message=f"Ошибка доступа к <code>{demo_url}</code>:<br>{exc}",
        )

    soup = BeautifulSoup(demo_resp.text, "html.parser")

    if not _find_email_input(soup):
        return render_template_string(
            ERROR_TEMPLATE,
            message="Поле ввода email не найдено на странице. Возможно, вёрстка вновь изменилась.",
        )

    # 5. Собираем скрытые поля (CSRF и пр.) + email
    form_data = _extract_csrf(soup)
    form_data["demo_mail"] = email

    # 6. Отправляем POST
    post_url = f"{base_url}/demo/"  # некоторые зеркала шлют на тот же URL
    # Попробуем также альтернативный путь /demo/success/
    # (определяем из атрибута action формы, если есть)
    form_tag = soup.find("form")
    if form_tag and form_tag.get("action"):
        action = form_tag["action"]
        if action.startswith("http"):
            post_url = action
        else:
            post_url = base_url + action

    # Referer — обязателен для многих WAF
    session.headers["Referer"] = demo_url

    try:
        post_resp = session.post(post_url, data=form_data, timeout=REQUEST_TIMEOUT)
        post_resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return render_template_string(
            ERROR_TEMPLATE,
            message=f"Ошибка при отправке формы:<br>{exc}",
        )

    # 7. Парсим ответ
    result_soup = BeautifulSoup(post_resp.text, "html.parser")
    confirmation = _parse_confirmation(result_soup)

    if not confirmation:
        return render_template_string(
            ERROR_TEMPLATE,
            message="Не удалось распознать ответ сервера. Возможно, вёрстка изменилась.",
        )

    # 8. Проверяем текст подтверждения (обновлённое regex)
    #    Варианты: «Ваш код выслан на …», «Код отправлен на …», «Code sent to …»
    success_pattern = re.compile(
        r"(код\s*(выслан|отправлен)|code\s*sent|ссылка\s*(отправлена|выслана))",
        re.IGNORECASE,
    )

    if success_pattern.search(confirmation):
        return render_template_string(SUCCESS_TEMPLATE)

    # Не успех — показываем что ответил сервер
    return render_template_string(
        ERROR_TEMPLATE,
        message=(
            "Сервис не принял запрос.<br>"
            f"Ответ: <strong>{confirmation}</strong><br><br>"
            "Возможные причины: email уже использовался, временная почта, "
            "IP в чёрном списке. Попробуйте другой email или прокси."
        ),
    )


# ──────────────────────────────────────────────
#  Точка входа (локальный запуск)
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)    return render_template_string(BASE_TEMPLATE, warning="Запрос отправлен. Проверьте почту через несколько минут.", email=email)
                    
            except requests.exceptions.ConnectionError:
                return render_template_string(BASE_TEMPLATE, error="Ошибка соединения. Используйте прокси.", email=email)
            except requests.exceptions.Timeout:
                return render_template_string(BASE_TEMPLATE, error="Таймаут. Сервис недоступен.", email=email)
            except requests.exceptions.HTTPError:
                return render_template_string(BASE_TEMPLATE, error="Ошибка HTTP. Сервис недоступен.", email=email)
            except Exception as e:
                return render_template_string(BASE_TEMPLATE, error=f"Ошибка: {str(e)[:100]}", email=email)
        
        return render_template_string(BASE_TEMPLATE)
    
    except Exception as e:
        return render_template_string(BASE_TEMPLATE, error=f"Критическая ошибка: {str(e)[:80]}")


# ============================================================
# VERCEL - просто экспортируем app (без сложного handler)
# ============================================================
```

## `vercel.json` (исправленный)

```json
{
  "version": 2,
  "builds": [
    {
      "src": "hmnkeysite.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "15mb"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "hmnkeysite.py"
    }
  ],
  "functions": {
    "hmnkeysite.py": {
      "runtime": "python3.12"
    }
  }
}
```

## `requirements.txt`

```
flask>=2.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
```

Убрал `fake-useragent` - он часто вызывает проблемы на сервере. Теперь используется фиксированный User-Agent.

## Причина ошибки

Проблема была в:
1. Сложном WSGI-handler'е который не работает на Vercel
2. `fake-useragent` может падать на сервере
3. Нужно было просто экспортировать `app` объект

После этого задеплойте:

```bash
vercel --prod --force
```def validate_email(email: str) -> tuple[bool, str]:
    if not email or "@" not in email:
        return False, "Введите корректный email"
    
    domain = email.split("@")[-1].lower()
    
    if domain in BLOCKED_EMAIL_DOMAINS:
        return False, "Временные почты запрещены"
    
    blocked_patterns = ["temp", "fake", "throw", "trash", "spam", "junk", "test"]
    for pattern in blocked_patterns:
        if pattern in domain:
            return False, f"Домен {domain} заблокирован"
    
    return True, ""


def find_working_mirror(session: requests.Session, headers: dict, proxies: dict = None) -> str | None:
    for mirror in MIRRORS:
        try:
            test_url = f"{mirror}/demo/"
            response = session.get(test_url, headers=headers, timeout=10, allow_redirects=True, proxies=proxies)
            if response.status_code == 200:
                return mirror
        except:
            continue
    return None


def parse_email_input(soup: BeautifulSoup) -> dict | None:
    selectors = [
        {'name': 'demo_mail'},
        {'name': 'email'},
        {'name': 'mail'},
        {'id': 'demo_mail'},
        {'id': 'email'},
        {'class': 'input_text_field'},
        {'type': 'email'},
    ]
    
    for selector in selectors:
        field = soup.find('input', selector)
        if field:
            return {
                'name': field.get('name', 'demo_mail'),
                'type': field.get('type', 'text'),
            }
    
    form = soup.find('form')
    if form:
        inputs = form.find_all('input', {'type': ['text', 'email']})
        for inp in inputs:
            name = inp.get('name', '').lower()
            if 'mail' in name or 'email' in name:
                return {'name': inp.get('name'), 'type': inp.get('type', 'text')}
    
    return None


def check_already_used(soup: BeautifulSoup) -> bool:
    page_text = soup.get_text().lower()
    patterns = [r"уже\s+использовал", r"вы\s+уже\s+получали", r"already\s+used"]
    return any(re.search(p, page_text) for p in patterns)


# ============================================================
# HTML ШАБЛОН
# ============================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HideMyName Keys</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        :root { --primary-color: #2563eb; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .card-custom { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); border: none; }
        .btn-custom { background: var(--primary-color); border: none; padding: 12px 30px; border-radius: 10px; font-weight: 600; transition: all 0.3s; }
        .btn-custom:hover { background: #1d4ed8; transform: translateY(-2px); }
        .form-control-custom { border-radius: 10px; padding: 12px 15px; border: 2px solid #e2e8f0; }
        .form-control-custom:focus { border-color: var(--primary-color); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .icon-large { font-size: 3rem; color: var(--primary-color); }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6 col-lg-5">
                <div class="card card-custom p-4">
                    <div class="text-center mb-4">
                        <i class="bi bi-shield-lock icon-large"></i>
                        <h3 class="mt-3 fw-bold">HideMyName Keys</h3>
                        <span class="badge bg-primary">Beta</span>
                    </div>
                    {% if error %}
                    <div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>{{ error }}</div>
                    {% endif %}
                    {% if success %}
                    <div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>{{ success }}</div>
                    {% endif %}
                    {% if warning %}
                    <div class="alert alert-warning"><i class="bi bi-exclamation-circle me-2"></i>{{ warning }}</div>
                    {% endif %}
                    <form method="post">
                        <div class="mb-3">
                            <label class="form-label fw-semibold"><i class="bi bi-envelope me-1"></i>Email</label>
                            <input type="email" class="form-control form-control-custom" name="email" placeholder="your@email.com" required value="{{ email or '' }}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-semibold"><i class="bi bi-globe me-1"></i>Прокси (опционально)</label>
                            <input type="text" class="form-control form-control-custom" name="proxy" placeholder="http://user:pass@host:port">
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-custom btn-primary text-white">
                                <i class="bi bi-key me-2"></i>Получить ключ
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


# ============================================================
# МАРШРУТ
# ============================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        proxy_input = request.form.get('proxy', '').strip()
        proxy = proxy_input if proxy_input else PROXY
        
        is_valid, msg = validate_email(email)
        if not is_valid:
            return render_template_string(BASE_TEMPLATE, error=msg, email=email)
        
        session = requests.Session()
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
        
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        try:
            mirror = find_working_mirror(session, headers, proxies)
            if not mirror:
                return render_template_string(BASE_TEMPLATE, error="Сервис недоступен", email=email)
            
            demo_url = f"{mirror}/demo/"
            response = session.get(demo_url, headers=headers, proxies=proxies, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if check_already_used(soup):
                return render_template_string(BASE_TEMPLATE, warning="Email уже использовался", email=email)
            
            email_field = parse_email_input(soup)
            if not email_field:
                return render_template_string(BASE_TEMPLATE, error="Форма не найдена", email=email)
            
            post_url = urljoin(mirror, '/demo/success/')
            post_data = {email_field['name']: email}
            
            submit_response = session.post(
                post_url, data=post_data,
                headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded', 'Referer': demo_url},
                proxies=proxies, timeout=30
            )
            submit_response.raise_for_status()
            
            result_soup = BeautifulSoup(submit_response.text, 'html.parser')
            page_text = result_soup.get_text(strip=True)
            
            success_patterns = [r'ваш\s*код\s*выслан', r'код\s*отправлен', r'письмо\s*отправлено', r'check\s*your\s*email']
            error_patterns = [r'временн', r'temp', r'уже\s+использовал', r'недействительн']
            
            is_success = any(re.search(p, page_text, re.I) for p in success_patterns)
            has_error = any(re.search(p, page_text, re.I) for p in error_patterns)
            
            if is_success:
                return render_template_string(BASE_TEMPLATE, success="✓ Ссылка подтверждения отправлена на почту!")
            elif has_error:
                return render_template_string(BASE_TEMPLATE, warning="Сервер вернул ошибку. Попробуйте другой email.", email=email)
            else:
                return render_template_string(BASE_TEMPLATE, warning="Запрос отправлен. Проверьте почту.", email=email)
                
        except requests.exceptions.ConnectionError:
            return render_template_string(BASE_TEMPLATE, error="Ошибка соединения. Попробуйте прокси.", email=email)
        except requests.exceptions.Timeout:
            return render_template_string(BASE_TEMPLATE, error="Таймаут. Сервис недоступен.", email=email)
        except Exception as e:
            return render_template_string(BASE_TEMPLATE, error=f"Ошибка: {str(e)[:80]}", email=email)
    
    return render_template_string(BASE_TEMPLATE)


# ============================================================
# VERCEL HANDLER (без внешних библиотек)
# ============================================================

def handler(event, context):
    """Vercel Serverless Function handler"""
    from json import dumps as json_dumps
    
    # Получаем метод и путь
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = event.get('headers', {})
    query_params = event.get('queryStringParameters', {}) or {}
    
    # Получаем body
    body = event.get('body', '')
    if event.get('isBase64Encoded', False):
        import base64
        body = base64.b64decode(body)
    
    # Создаём environ для WSGI
    environ = {
        'REQUEST_METHOD': http_method,
        'SCRIPT_NAME': '',
        'PATH_INFO': path,
        'QUERY_STRING': '&'.join(f"{k}={v}" for k, v in query_params.items()),
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'HTTP_HOST': headers.get('host', 'localhost'),
        'wsgi.url_scheme': 'https',
        'wsgi.input': __import__('io').BytesIO(body.encode() if body else b''),
        'wsgi.errors': __import__('sys').stderr,
        'wsgi.multithread': True,
        'wsgi.multiprocess': True,
    }
    
    # Добавляем заголовки
    for key, value in headers.items():
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    response_status = [200]
    response_headers = [('Content-Type', 'text/html')]
    
    def start_response(status, headers):
        response_status[0] = int(status.split()[0])
        response_headers.extend(headers)
    
    # Вызываем Flask приложение
    response_body = b''.join(app(environ, start_response))
    
    return {
        'statusCode': response_status[0],
        'headers': dict(response_headers),
        'body': response_body.decode('utf-8')
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) class="text-center text-muted small">
                        <p class="mb-1"><i class="bi bi-info-circle me-1"></i>Требуется подписка iCloud+</p>
                        <p class="mb-0">Ключ будет отправлен на указанную почту</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


# ============================================================
# ОСНОВНОЙ МАРШРУТ
# ============================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    success = None
    warning = None
    email = None
    used_proxy = None
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        proxy_input = request.form.get('proxy', '').strip()
        
        # Использовать прокси из формы или из конфигурации
        proxy = proxy_input if proxy_input else PROXY
        
        # Валидация email
        is_valid, validation_msg = validate_email(email)
        if not is_valid:
            return render_template_string(
                BASE_TEMPLATE, 
                error=validation_msg, 
                email=email
            )
        
        # Настройка сессии и заголовков
        session = requests.Session()
        
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Настройка прокси для сессии
        proxies = None
        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            used_proxy = proxy
        
        try:
            # Поиск рабочего зеркала
            mirror = find_working_mirror(session, headers)
            
            if not mirror:
                return render_template_string(
                    BASE_TEMPLATE,
                    error="Не удалось найти рабочее зеркало сервиса. Попробуйте позже.",
                    email=email
                )
            
            demo_url = f"{mirror}/demo/"
            
            # Загрузка демо-страницы
            response = session.get(
                demo_url, 
                headers=headers, 
                proxies=proxies,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Парсинг страницы
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Проверка на уже использованную почту
            if check_already_used(soup, email):
                return render_template_string(
                    BASE_TEMPLATE,
                    warning="Этот email уже использовался для получения ключа ранее.",
                    email=email
                )
            
            # Поиск поля ввода
            email_field = parse_email_input(soup)
            
            if not email_field:
                return render_template_string(
                    BASE_TEMPLATE,
                    error="Не удалось найти форму ввода. Сайт可能 изменил структуру.",
                    email=email
                )
            
            # Отправка email
            post_url = urljoin(mirror, '/demo/success/')
            post_data = {email_field['name']: email}
            
            submit_response = session.post(
                post_url,
                data=post_data,
                headers={
                    **headers,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': demo_url
                },
                proxies=proxies,
                timeout=30
            )
            submit_response.raise_for_status()
            
            # Анализ ответа
            result_soup = BeautifulSoup(submit_response.text, 'html.parser')
            page_text = result_soup.get_text(strip=True)
            
            # Проверка успешного ответа - исправленное регулярное выражение
            success_patterns = [
                r'Ваш\s*код\s*выслан\s*на',
                r'код\s*отправлен',
                r'выслан\s*на\s*почту',
                r'check\s*your\s*email',
                r'confirmation\s*sent',
                r'письмо\s*отправлено'
            ]
            
            is_success = any(re.search(pattern, page_text, re.IGNORECASE) for pattern in success_patterns)
            
            # Проверка на ошибки
            error_patterns = [
                r'временн.*почт',
                r'temp.*mail',
                r'уже\s+использовал',
                r'недействительн',
                r'invalid',
                r'error'
            ]
            
            has_error = any(re.search(pattern, page_text, re.IGNORECASE) for pattern in error_patterns)
            
            if is_success:
                return render_template_string(
                    BASE_TEMPLATE,
                    success="✓ Ссылка подтверждения отправлена! Перейдите по ней, чтобы получить ключ на почту."
                )
            elif has_error:
                # Извлекаем текст ошибки
                error_div = result_soup.find('div', class_=re.compile(r'error|alert|warning', re.I))
                error_text = error_div.get_text(strip=True) if error_div else "Произошла ошибка"
                return render_template_string(
                    BASE_TEMPLATE,
                    warning=f"Сервер вернул: {error_text[:100]}",
                    email=email
                )
            else:
                return render_template_string(
                    BASE_TEMPLATE,
                    warning="Запрос отправлен, но ответ сервера неопределён. Проверьте почту через несколько минут.",
                    email=email
                )
                
        except requests.exceptions.ConnectionError:
            return render_template_string(
                BASE_TEMPLATE,
                error="Ошибка соединения. Возможно, сервис заблокировал ваш IP. Попробуйте использовать прокси.",
                email=email
            )
        except requests.exceptions.Timeout:
            return render_template_string(
                BASE_TEMPLATE,
                error="Превышен таймаут ожидания. Сервис может быть недоступен.",
                email=email
            )
        except requests.exceptions.HTTPError as e:
            return render_template_string(
                BASE_TEMPLATE,
                error=f"HTTP ошибка: {e.response.status_code}",
                email=email
            )
        except Exception as e:
            return render_template_string(
                BASE_TEMPLATE,
                error=f"Произошла ошибка: {str(e)[:100]}",
                email=email
            )
    
    return render_template_string(BASE_TEMPLATE)


# ============================================================
# VERCEL COMPATIBILITY
# ============================================================

# Для Vercel требуется экспорт объекта app
# Vercel автоматически передаёт environ и start_response
def handler(event, context):
    """Vercel serverless function handler"""
    from vercel_wsgi import make_environ
    
    environ = make_environ(event)
    
    def start_response(status, headers):
        return lambda x: None
    
    response = app(environ, start_response)
    
    return {
        "statusCode": 200,
        "body": b"".join(response),
        "headers": {"Content-Type": "text/html"}
    }


if __name__ == '__main__':
    # Локальный запуск
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
