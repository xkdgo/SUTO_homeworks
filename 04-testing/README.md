### Scoring API

## Краткое описание:
Реализован декларативный язык описания и система валидации запросов к HTTP API сервиса скоринга.

## Запуск
Запустить файл
`python3 api.py`

## Тестирование
`py.test -v -l test.py`

`py.test -s -v -l test.py`

## Примеры запросов

`curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin",
"method": "clients_interests", "token":
"07d670619bb0f0c28fa36115953f8afc9968fcb4b1e9ab9c57498efd069eb288a1751d462995e80335298afe50a13ebc76daf9c1afff4cef6a313d9473462943",
"arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/`

ответ

`{"code": 200, "response": {"1": ["books", "hi-tech"], "2": ["pets", "tv"], "3": ["travel", "music"],
"4": ["cinema", "geek"]}}`

при наличии в БД соответсвующих записей


`curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f",
"method": "online_score", "token":
"55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
"arguments": {"phone": "71234567891", "email": "your@domain.ru", "first_name": "Василий",
"last_name": "Васильев", "birthday": "01.01.2000", "gender": 1}}' http://127.0.0.1:8080/method/`

ответ

`{"code": 200, "response": {"score": 5.0}}`