# pereval

## Что это?

Бэкенд для REST API сервера приёма заявок на добавление перевалов в базу туристической организации.

## Как это запустить?
 
* Скачиваете Git-репозиторий:
```shell
git clone https://github.com/2nky/pereval
```

* Устанавливаете зависимости:
```shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

* Запускаете отладочный сервер:
```shell
python3 ./manage.py runserver
```

После этого API будет доступно на `http://127.0.0.1:8000/`.

## Swagger

Если вы хотите попробовать это API в деле, то оно описано
в файле `static/swagger.yaml` по спецификация OpenAPI 3.

После запуска приложения можно браузером пойти на страничку
`http://127.0.0.1:8000/swagger-ui.html` и ознакомиться с разными
методами для работы с ним.

## Автор
Борисова Полина (http://github.com/2nky/)