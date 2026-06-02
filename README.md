# CryptoSafe Manager

CryptoSafe Manager - локальный менеджер паролей с графическим интерфейсом на PySide6. Данные хранятся в выбранном пользователем SQLite-файле и шифруются на стороне клиента.

Текущая версия: **0.6.0 (Sprint 6)**.

## Возможности

- Создание и открытие отдельных файлов хранилища `.db`.
- Защита мастер-паролем: Argon2id используется для проверки пароля, PBKDF2-SHA256 - для получения 256-битного ключа шифрования.
- Шифрование записей целиком через AES-256-GCM.
- CRUD для записей: название, логин, пароль, URL, категория и заметки.
- Поиск по записям в таблице.
- Генерация надежных паролей и индикатор сложности.
- Автоматическая загрузка favicon по URL с локальным кешем в `favicons/`.
- Контекстное меню для копирования логина, пароля, URL или пары `логин:пароль`.
- Безопасный буфер обмена с автоочисткой, настраиваемым таймаутом и уведомлениями.
- Блокировка хранилища при неактивности приложения.
- Смена мастер-пароля с перешифрованием записей.
- Резервное копирование базы данных.
- Журнал аудита с последовательными номерами, хеш-цепочкой, подписями записей, проверкой целостности и экспортом в JSON/CSV.
- Sprint 6: защищенный импорт и экспорт хранилища, выборочная выгрузка записей, CSV/Bitwarden/LastPass-совместимые форматы, encrypted JSON, password/public-key encryption, sharing-пакеты и QR payload chunking.

## Требования

- Python 3.12+.
- Windows, macOS или Linux.
- Для Windows используется `pywin32`, для macOS - `pyobjc`.

Зависимости перечислены в [src/requirements.txt](src/requirements.txt).

## Установка

```bash
git clone https://github.com/aleksejsamarin06-source/crypto.git
cd crypto

python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r src/requirements.txt
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r src/requirements.txt
```

## Запуск

```bash
python main.py
```

При первом запуске приложение предложит создать новое хранилище: нужно задать мастер-пароль и путь к SQLite-файлу, по умолчанию `~/cryptosafe.db`.

## Работа с приложением

1. Создайте новое хранилище через мастер первого запуска или меню `Файл -> Новый`.
2. Откройте существующее хранилище через `Файл -> Открыть`.
3. Добавляйте, редактируйте и удаляйте записи через меню `Правка` или двойной клик по строке.
4. Используйте контекстное меню строки для копирования логина, пароля, URL, связки `логин:пароль` или создания sharing-пакета.
5. Настройте таймаут очистки буфера обмена и уведомления через `Вид -> Настройки`.
6. Просматривайте аудит через `Вид -> Журнал`; там доступны фильтры, проверка целостности и экспорт.
7. Используйте `Файл -> Экспорт` для encrypted JSON, CSV или Bitwarden JSON.
8. Используйте `Файл -> Импорт` для encrypted JSON, CSV, Bitwarden JSON и LastPass CSV; доступен dry-run preview.

## Sprint 6

### Импорт и экспорт

- `encrypted_json` шифруется отдельным экспортным ключом, который не совпадает с мастер-ключом хранилища.
- Password-based export использует PBKDF2-HMAC-SHA256, 100000 итераций и AES-GCM.
- Public-key export использует hybrid encryption: RSA-OAEP для ключа и AES-GCM для данных.
- Для encrypted package сохраняются metadata, ciphertext hash, payload hash и HMAC/signature-проверка.
- CSV plaintext разрешается только явно, как режим миграции.
- Import поддерживает `dry-run`, `merge`, `replace`, duplicate handling `skip/update/create`, лимит размера файла 10 MB и timeout 30 секунд.
- Импортируемые поля валидируются и очищаются от script/javascript/control content.

### Sharing и QR

- Можно создать encrypted sharing package для отдельной записи через пароль или публичный ключ.
- Sharing package содержит только выбранную запись, permissions, recipient, expiration от 1 до 30 дней и отдельное шифрование.
- QR-сервис формирует payload для public keys, encrypted entries и share payloads, добавляет checksum, nonce, expiration и разбивает большие данные на chunks.
- QR codes не содержат plaintext-пароли; в QR payload передаются только зашифрованные packages или публичные данные.

## Структура проекта

```text
crypto/
|-- main.py
|-- README.md
|-- favicons/
|-- src/
|   |-- check_log.py
|   |-- requirements.txt
|   |-- core/
|   |   |-- audit/
|   |   |-- clipboard/
|   |   |-- crypto/
|   |   |-- import_export/
|   |   |   |-- exporter.py
|   |   |   |-- importer.py
|   |   |   |-- sharing_service.py
|   |   |   |-- key_exchange.py
|   |   |   |-- crypto_utils.py
|   |   |   `-- formats/
|   |   |       |-- csv_format.py
|   |   |       `-- password_manager.py
|   |   `-- vault/
|   |-- database/
|   |   |-- backup.py
|   |   |-- db.py
|   |   `-- models.py
|   `-- gui/
|       |-- main_window.py
|       `-- widgets/
|           |-- export_dialog.py
|           |-- import_dialog.py
|           |-- share_dialog.py
|           `-- ...
`-- tests/
    |-- test_import_export_sprint6.py
    `-- ...
```

## Тестирование

```bash
.venv\Scripts\python.exe -m unittest discover tests -v
```

## Технологии

- GUI: PySide6.
- База данных: SQLite.
- Шифрование записей: AES-256-GCM из `cryptography`.
- Хеширование мастер-пароля: Argon2id из `argon2-cffi`.
- Получение ключа шифрования: PBKDF2-HMAC-SHA256.
- Export/sharing encryption: AES-GCM, PBKDF2-HMAC-SHA256, RSA-OAEP.
- Буфер обмена: `pyperclip`, `pywin32` для Windows, `pyobjc` для macOS.
- Тесты: `unittest`.

## Статус реализации

Версия `0.6.0` включает базовое GUI-хранилище, криптографию, безопасный буфер обмена, смену мастер-пароля, резервное копирование, аудит, защищенный импорт/экспорт, sharing-пакеты, публичные ключи и QR payload chunking. Сетевые time-limited links и camera scanning не добавлены как отдельный сетевой/камерный слой; текущая реализация Sprint 6 работает в офлайн-модели через файлы и QR payload data.
