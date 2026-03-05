import os
import re
from flask import Flask, request, render_template_string
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

# Список актуальных зеркал сервиса (проверяются по очереди)
MIRRORS = [
    "https://hidemy.io",
    "https://hidemy.name", 
    "https://hidemy.net",
    "https://hidemyna.com",
    "https://hideme.ru",
]

# Список заблокированных/временных почтовых доменов
BLOCKED_EMAIL_DOMAINS = [
    "temp-mail.org", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "mailinator.com", "throwaway.email", "fakeinbox.com", "yopmail.com",
    "trashmail.com", "getnada.com", "mintemail.com", "sharklasers.com",
    "spam4.me", "grr.la", "maildrop.cc", "emailondeck.com"
]

# Прокси (опционально) - установить переменную окружения или указать здесь
PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

app = Flask(__name__)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def validate_email(email: str) -> tuple[bool, str]:
    """Валидация email на основе блэк-листа доменов"""
    if not email or "@" not in email:
        return False, "Введите корректный email"
    
    domain = email.split("@")[-1].lower()
    
    if domain in BLOCKED_EMAIL_DOMAINS:
        return False, "Временные почты запрещены. Используйте реальный email"
    
    # Проверка на публичные домены временной почты
    blocked_patterns = ["temp", "fake", "throw", "trash", "spam", "junk", "test"]
    for pattern in blocked_patterns:
        if pattern in domain:
            return False, f"Домен {domain} заблокирован. Используйте постоянную почту"
    
    return True, ""


def find_working_mirror(session: requests.Session, headers: dict) -> str | None:
    """Поиск рабочего зеркала из списка"""
    for mirror in MIRRORS:
        try:
            # Провяем доступность главной страницы
            test_url = f"{mirror}/demo/"
            response = session.get(test_url, headers=headers, timeout=10, allow_redirects=True)
            
            if response.status_code == 200 and "demo" in response.text.lower():
                print(f"✓ Рабочее зеркало: {mirror}")
                return mirror
        except requests.exceptions.RequestException:
            continue
    
    return None


def parse_email_input(soup: BeautifulSoup) -> dict | None:
    """Улучшенный поиск поля ввода email с гибкими селекторами"""
    # Список селекторов для поиска поля email
    selectors = [
        {'name': 'demo_mail'},
        {'name': 'email'},
        {'name': 'mail'},
        {'id': 'demo_mail'},
        {'id': 'email'},
        {'class': 'input_text_field'},
        {'class': re.compile(r'text.*mail', re.I)},
        {'type': 'email'},
    ]
    
    for selector in selectors:
        field = soup.find('input', selector)
        if field:
            return {
                'name': field.get('name', 'demo_mail'),
                'type': field.get('type', 'text'),
                'required': field.get('required') is not None
            }
    
    # Альтернативный поиск через форму
    form = soup.find('form')
    if form:
        inputs = form.find_all('input', {'type': ['text', 'email']})
        for inp in inputs:
            name = inp.get('name', '').lower()
            if 'mail' in name or 'email' in name:
                return {
                    'name': inp.get('name'),
                    'type': inp.get('type', 'text'),
                    'required': inp.get('required') is not None
                }
    
    return None


def check_already_used(soup: BeautifulSoup, email: str) -> bool:
    """Проверка, не используется ли уже этот email"""
    page_text = soup.get_text().lower()
    
    # Паттерны сообщений об уже использованной почте
    used_patterns = [
        r"уже\s+использовал",
        r"вы\s+уже\s+получали",
        r"данный\s+email\s+уже",
        r"почта\s+уже\s+использована",
        r"already\s+used",
        r"already\s+registered"
    ]
    
    for pattern in used_patterns:
        if re.search(pattern, page_text):
            return True
    
    return False


# ============================================================
# HTML ШАБЛОН (Bootstrap 5 + современный дизайн)
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
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        body {
            background: var(--bg-gradient);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .card-custom {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            border: none;
        }
        
        .btn-custom {
            background: var(--primary-color);
            border: none;
            padding: 12px 30px;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .btn-custom:hover {
            background: #1d4ed8;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        
        .form-control-custom {
            border-radius: 10px;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        
        .form-control-custom:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .icon-large {
            font-size: 3rem;
            color: var(--primary-color);
        }
        
        .status-badge {
            font-size: 0.75rem;
            padding: 5px 12px;
        }
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
                        <span class="badge bg-primary status-badge">Beta</span>
                    </div>
                    
                    {{% if error %}}
                    <div class="alert alert-danger d-flex align-items-center" role="alert">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <div>{{ error }}</div>
                    </div>
                    {{% endif %}}
                    
                    {{% if success %}}
                    <div class="alert alert-success d-flex align-items-center" role="alert">
                        <i class="bi bi-check-circle-fill me-2"></i>
                        <div>{{ success }}</div>
                    </div>
                    {{% endif %}}
                    
                    {{% if warning %}}
                    <div class="alert alert-warning d-flex align-items-center" role="alert">
                        <i class="bi bi-exclamation-circle-fill me-2"></i>
                        <div>{{ warning }}</div>
                    </div>
                    {{% endif %}}
                    
                    <form method="post">
                        <div class="mb-3">
                            <label for="email" class="form-label fw-semibold">
                                <i class="bi bi-envelope me-1"></i>Email адрес
                            </label>
                            <input type="email" 
                                   class="form-control form-control-custom" 
                                   id="email" 
                                   name="email" 
                                   placeholder="your@email.com"
                                   required
                                   value="{{ email or '' }}">
                            <div class="form-text">Используйте постоянную почту, не временную</div>
                        </div>
                        
                        <div class="mb-3" id="proxy-section">
                            <label for="proxy" class="form-label fw-semibold">
                                <i class="bi bi-globe me-1"></i>Прокси (опционально)
                            </label>
                            <input type="text" 
                                   class="form-control form-control-custom" 
                                   id="proxy" 
                                   name="proxy" 
                                   placeholder="http://user:pass@host:port">
                        </div>
                        
                        <div class="d-grid">
                            <button type="submit" class="btn btn-custom btn-primary text-white">
                                <i class="bi bi-key me-2"></i>Получить ключ
                            </button>
                        </div>
                    </form>
                    
                    <hr class="my-4">
                    
                    <div class="text-center text-muted small">
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
