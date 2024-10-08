from flask import Flask, request, render_template_string
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import logging
import re

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')

        ua = UserAgent()
        headers = {'User-Agent': ua.random}

        try:
            demo_page = requests.get('https://hidxx.name/demo/', headers=headers)
            demo_page.raise_for_status()
            app.logger.debug('Accessed demo page successfully')
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error accessing the site: {e}")
            return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка доступа к сайту: {{ e }}</div></div>', e=e)

        soup = BeautifulSoup(demo_page.text, 'html.parser')
        email_input = soup.find('input', {'class': 'input_text_field', 'name': 'demo_mail'})

        if email_input:
            app.logger.debug(f'Found email input field: {email_input}')

            try:
                response = requests.post('https://hidxx.name/demo/success/', data={"demo_mail": email}, headers=headers)
                response.raise_for_status()
                app.logger.debug('Email sent successfully')
            except requests.exceptions.RequestException as e:
                app.logger.error(f"Error sending request: {e}")
                return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка при отправке запроса: {{ e }}</div></div>', e=e)

            soup = BeautifulSoup(response.text, 'html.parser')
            try:
                confirmation_message = soup.find('h2', {'class': 'title'}).get_text(strip=True)
                app.logger.debug(f'Confirmation message: {confirmation_message}')
            except AttributeError as e:
                app.logger.error(f"Error parsing confirmation message: {e}")
                return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка при парсинге подтверждающего сообщения: {{ e }}</div></div>', e=e)

            if re.match(r'^Ваш код выслан\s*на\s*', confirmation_message):
                app.logger.debug('Confirmation message received, code sent to email.')
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
                      </body>
                    </html>
                ''')
            else:
                app.logger.warning(f'Unexpected confirmation message: {confirmation_message}')
                return render_template_string('<div class="container"><div class="alert alert-warning" role="alert">Указанная почта не подходит для получения тестового периода. Ответ сервера: {{ confirmation_message }}</div></div>', confirmation_message=confirmation_message)
        else:
            app.logger.warning('Email input field not found.')
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
                    color: #007bff; /* Цвет заголовка */
                }
                .centered-button {
                    display: flex;
                    justify-content: center;
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
                                        <label for="email">Email</label>
                                        <input type="email" class="form-control" id="email" name="email" placeholder="Введите email" required>
                                    </div>
                                    <div class="centered-button">
                                        <button type="submit" class="btn btn-primary">Получить код</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
          </body>
        </html>
    ''')

if __name__ == '__main__':
    app.run(debug=True)
