from flask import Flask, request, render_template_string, redirect, url_for
from flask_frozen import Freezer
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
freezer = Freezer(app)

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
            return render_template_string('<div class="container"><div class="alert alert-danger" role="alert">Ошибка доступа к сайту: {{ e }}</div></div>', e=e)

        soup = BeautifulSoup(demo_page.text, 'html.parser')
        email_input = soup.find('input', {'class': 'input_text_field', 'name': 'demo_mail'})

        if email_input:
            try:
                response = requests.post('https://hidxxx.name/demo/success/', data={"demo_mail": email}, headers=headers, proxies=proxies)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
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

if __name__ == '__main__':
    freezer.freeze() 
