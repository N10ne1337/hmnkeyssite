from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import time
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import logging

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        proxy = request.form.get('proxy')
        email = request.form.get('email')

        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        proxies = {'https': f'http://{proxy}'} if proxy else None

        try:
            demo_page = requests.get('https://hidxxx.name/demo/', headers=headers, proxies=proxies)
            demo_page.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error accessing the site: {e}")
            return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка доступа к сайту: {{ e }}</div></div>', e=e)

        soup = BeautifulSoup(demo_page.text, 'html.parser')
        email_input = soup.find('input', {'class': 'input_text_field', 'name': 'demo_mail'})

        if email_input:
            try:
                response = requests.post('https://hidxxx.name/demo/success/', data={"demo_mail": email}, headers=headers, proxies=proxies)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                app.logger.error(f"Error sending request: {e}")
                return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка при отправке запроса: {{ e }}</div></div>', e=e)

            soup = BeautifulSoup(response.text, 'html.parser')
            confirmation_message = soup.find('h2', {'class': 'title'}).get_text(strip=True)
            
            # Используем регулярное выражение для проверки текста
            if re.match(r'^Ваш код выслан\s*на\s*', confirmation_message):
                return render_template_string('''
                    <!doctype html>
                    <html lang="en">
                      <head>
                        <meta charset="utf-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
                        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
                        <title>Подтверждение Email</title>
                      </head>
                      <body>
                        <div class="container mt-5">
                            <div class="alert alert-info" role="alert">
                                Ссылка подтверждения была отправлена на указанную почту. Перейдите по ней чтобы вам пришёл код на почту.
                            </div>
                            <a href="/" class="btn btn-primary">Домой</a>
                        </div>
                        <div class="container mt-3">
                            <form id="vpnForm" method="post" action="/get_vpn_config">
                                <div class="form-group">
                                    <label for="access_code">Код доступа из письма</label>
                                    <input type="text" class="form-control" id="access_code" name="access_code" placeholder="Введите код доступа">
                                </div>
                                <button type="submit" class="btn btn-primary">Получить конфигурацию VPN для роутера</button>
                            </form>
                        </div>
                      </body>
                    </html>
                ''')
            else:
                return render_template_string('<div class="container"><div class="alert alert-warning" role="alert">Указанная почта не подходит для получения тестового периода. Ответ сервера: {{ response.text }}</div></div>', response=response)
        else:
            return render_template_string('<div class="container"><div class="alert alert-warning" role="alert">Невозможно получить тестовый период</div></div>')

    return render_template_string('''
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <style>
                .centered-header {
                    text-align: center;
                    color: #007bff; /* Цвет кнопки "Получить код" */
                }
            </style>
            <title>HideMyName Keys (Beta)</title>
          </head>
          <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header centered-header">
                                <h2>HideMyName Keys (Beta)</h2>
                            </div>
                            <div class="card-body">
                                <form method="post">
                                    <div class="form-group">
                                        <label for="proxy">Прокси</label>
                                        <input type="text" class="form-control" id="proxy" name="proxy" placeholder="Введите прокси">
                                    </div>
                                    <div class="form-group">
                                        <label for="email">Email</label>
                                        <input type="email" class="form-control" id="email" name="email" placeholder="Введите email">
                                    </div>
                                    <button type="submit" class="btn btn-primary">Получить код</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
          </body>
        </html>
    ''')

@app.route('/get_vpn_config', methods=['POST'])
def get_vpn_config():
    access_code = request.form.get('access_code')

    # Используем UserAgent для заголовков
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    try:
        # Отправляем запрос с кодом доступа
        response = requests.post('https://hidxxx.name/vpn/router/', data={"code": access_code}, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending request to VPN router page: {e}")
        return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка при отправке запроса: {{ e }}</div></div>', e=e)

    # Ждем 3 секунды для обработки на сервере
    time.sleep(3)

    # Логирование содержимого страницы для отладки
    app.logger.debug(f"Response content: {response.text}")

    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        # Получаем нужные данные
        description_tag = soup.find('span', class_='account_info')
        description = description_tag.text.strip() if description_tag else 'Не удалось найти описание'

        server_tag = soup.find('span', class_='account_serverlist')
        server = server_tag.text.strip() if server_tag else 'Не удалось найти сервер'

        username_tag = soup.find('span', class_='account_number')
        username = username_tag.text.strip() if username_tag else 'Не удалось найти имя пользователя'

        password_tag = soup.find('span', class_='account_password').find('span', class_='red')
        password = password_tag.text.strip() if password_tag else 'Не удалось найти пароль'
    except Exception as e:
        app.logger.error(f"Error parsing VPN configuration data: {e}")
        return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка при парсинге данных конфигурации VPN: {{ e }}</div></div>', e=e)

    app.logger.info(f"Parsed VPN configuration: description={description}, server={server}, username={username}, password={password}")

    return render_template_string('''
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <title>Конфигурация VPN</title>
          </head>
          <body>
            <div class="container mt-5">
                <h2>Конфигурация VPN для роутера</h2>
                <ul class="list-group">
                    <li class="list-group-item"><strong>Описание:</strong> {{ description }}</li>
                    <li class="list-group-item"><strong>Сервер:</strong> {{ server }}</li>
                    <li class="list-group-item"><strong>Имя пользователя:</strong> {{ username }}</li>
                    <li class="list-group-item"><strong>Пароль:</strong> {{ password }}</li>
                </ul>
                <a href="/" class="btn btn-primary mt-3">Домой</a>
            </div>
          </body>
        </html>
    ''', description=description, server=server, username=username, password=password)

if __name__ == '__main__':
    app.run(debug=True)
