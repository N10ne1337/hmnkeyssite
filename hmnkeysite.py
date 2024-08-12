from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Website</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    </head>
    <body>
        <h1>Welcome to My Website</h1>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

from flask import Flask, request, render_template_string
from os import system
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        proxy = request.form.get('proxy')
        email = request.form.get('email')
        confirm = request.form.get('confirm')

        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        proxies = {'https': f'http://{proxy}'} if proxy else None

        if not confirm:
            try:
                demo_page = requests.get('https://hidxxx.name/demo/', headers=headers, proxies=proxies)
                demo_page.raise_for_status()
            except requests.exceptions.RequestException as e:
                return f'Ошибка доступа к сайту: {e}'

            soup = BeautifulSoup(demo_page.text, 'html.parser')
            email_input = soup.find('input', {'class': 'input_text_field', 'name': 'demo_mail'})

            if email_input:
                try:
                    response = requests.post('https://hidxxx.name/demo/success/', data={
                        "demo_mail": email
                    }, headers=headers, proxies=proxies)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    return f'Ошибка при отправке запроса: {e}'

                if 'Ваш код выслан на почту' in response.text:
                    return render_template_string('''
                        <style>
                            .center {
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                justify-content: center;
                                height: 100vh;
                            }
                            form {
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                            }
                            input, button {
                                margin: 5px;
                            }
                        </style>
                        <div class="center">
                            <form method="post">
                                Ссылка для подтверждения: <input type="text" name="confirm"><br>
                                <input type="hidden" name="proxy" value="{{ proxy }}">
                                <input type="hidden" name="email" value="{{ email }}">
                                <input type="submit" value="Подтвердить">
                            </form>
                        </div>
                    ''', proxy=proxy, email=email)
                else:
                    return f'Указанная почта не подходит для получения тестового периода. Ответ сервера: {response.text}'
            else:
                return 'Невозможно получить тестовый период'
        else:
            try:
                response = requests.get(confirm, headers=headers, proxies=proxies)
                response.raise_for_status()
                if 'Спасибо' in response.text:
                    return 'Почта подтверждена. Код отправлен на ваш email.'
                else:
                    return 'Ссылка невалидная, повторите попытку.'
            except requests.exceptions.RequestException as e:
                return f'Ошибка при подтверждении: {e}'

    return render_template_string('''
        <style>
            .center {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }
            form {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            input, button {
                margin: 5px;
            }
        </style>
        <div class="center">
            <form method="post">
                Прокси: <input type="text" name="proxy"><br>
                Электронная почта: <input type="email" name="email" required><br>
                <input type="submit" value="Отправить">
            </form>
        </div>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
