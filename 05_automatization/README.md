## Cервер на ванильном Python
### Веб‐сервер умеет:
```Масштабироваться на несколько worker'ов
Числов worker'ов задается аргументом командной строки ‐w
Отвечать 200, 403 или 404 на GET‐запросы и HEAD‐запросы
Отвечать 405 на прочие запросы
Возвращать файлы по произвольному пути в DOCUMENT_ROOT.
Вызов /file.html должен возвращать содердимое DOCUMENT_ROOT/file.html
DOCUMENT_ROOT задается аргументом командной строки ‐r
Возвращать index.html как индекс директории
Вызов /directory/ должен возвращать DOCUMENT_ROOT/directory/index.html
Отвечать следующими заголовками для успешных GET‐запросов: Date, Server, Content‐Length, Content‐Type,
Connection
Корректный Content‐Type для: .html, .css, .js, .jpg, .jpeg, .png, .gif, .swf
Понимать пробелы и %XX в именах файлов
```


### Запуск

Скрипт запускается командой в терминале из папки, в которой находится:

`sudo python3 httpd.py`

Помощь

`python3 httpd.py --help`

### Архитектура

Сервер использует мультиплексированную архитектуру с при помощи селекторов

По умолчанию используется наиболее эффективный селектор на платформе.

При указании количества worker в каждом из тредов используется по своему селектору,
который обслуживает группу сокетов

### Бенчмарк

для 5 worker

```ab -n 50000 -c 100 -r "http://localhost:8080/"
This is ApacheBench, Version 2.3 <$Revision: 1706008 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        OTUServer
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        63 bytes

Concurrency Level:      100
Time taken for tests:   97.729 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      9500000 bytes
HTML transferred:       3150000 bytes
Requests per second:    511.62 [#/sec] (mean)
Time per request:       195.458 [ms] (mean)
Time per request:       1.955 [ms] (mean, across all concurrent requests)
Transfer rate:          94.93 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.3      0      13
Processing:    63  195  19.6    200     319
Waiting:       61  194  19.5    199     318
Total:         70  195  19.6    200     319

Percentage of the requests served within a certain time (ms)
  50%    200
  66%    204
  75%    206
  80%    208
  90%    212
  95%    215
  98%    220
  99%    230
 100%    319 (longest request)
```
### Результаты тестов

```
./httptest.py
directory index file exists ... ok
document root escaping forbidden ... ok
Send bad http headers ... ok
file located in nested folders ... ok
absent file returns 404 ... ok
urlencoded filename ... ok
file with two dots in name ... ok
query string after filename ... ok
filename with spaces ... ok
Content-Type for .css ... ok
Content-Type for .gif ... ok
Content-Type for .html ... ok
Content-Type for .jpeg ... ok
Content-Type for .jpg ... ok
Content-Type for .js ... ok
Content-Type for .png ... ok
Content-Type for .swf ... ok
head method support ... ok
directory index file absent ... ok
large file downloaded correctly ... ok
post method forbidden ... ok
Server header exists ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.254s

OK

```