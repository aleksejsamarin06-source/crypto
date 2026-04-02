# CryptoSafe Manager

Менеджер паролей с шифрованием на стороне клиента.

## Возможности

- 🔐 Безопасное хранение паролей
- 🔑 Мастер-пароль с Argon2
- 📁 Работа с несколькими базами данных
- 📝 Журнал действий
- 🔄 Смена мастер-пароля с перешифрованием
- ⏱️ Автоблокировка при неактивности

## Установка

```bash
# Клонирование
git clone https://github.com/aleksejsamarin06-source/crypto.git
cd crypto

# Виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Зависимости
pip install -r requirements.txt
# Запуск
bash
python -m src
```
## Структура проекта
```bash
crypto_project/                   # Корневая папка проекта
├── src/                          # Исходный код
│   ├── core/                     # Бизнес-логика и ядро приложения
│   │   ├── crypto/               # Криптографические операции
│   │   │   ├── __init__.py
│   │   │   ├── abstract.py       # Абстрактный класс шифрования
│   │   │   ├── authentication.py # Проверка пароля, вход, сессии
│   │   │   ├── key_derivation.py # Argon2, PBKDF2 - формирование ключей
│   │   │   ├── key_storage.py    # Безопасное кэширование ключей
│   │   │   └── placeholder.py    # XOR заглушка (для первого спринта)
│   │   ├── audit_manager.py      # Запись действий в журнал
│   │   ├── config.py             # Настройки приложения
│   │   ├── events.py             # Система событий
│   │   ├── key_manager.py        # Управление ключами шифрования
│   │   └── state_manager.py      # Состояние приложения
│   ├── database/                 # Работа с базой данных
│   │   ├── backup.py             # Резервное копирование
│   │   ├── db.py                 # Подключение к SQLite, создание таблиц
│   │   └── models.py             # Модели данных
│   └── gui/                      # Пользовательский интерфейс
│       ├── widgets/              # виджеты
│       │   ├── __init__.py
│       │   ├── audit_log_dialog.py # Просмотр журнала действий
│       │   ├── change_password_dialog.py # Смена мастер-пароля
│       │   ├── entry_dialog.py     # Добавление/редактирование записи
│       │   ├── login_dialog.py     # Окно входа при открытии существующей бд
│       │   ├── password_entry.py   # Поле с кнопкой показать/скрыть
│       │   └── setup_wizard.py     # Мастер первого запуска
│       └── main_window.py          # Главное окно программы
├── tests/                          # Тесты
│   ├── test_authentication.py      # Тесты входа и задержек
│   ├── test_integration.py         # Интеграционные тесты
│   ├── test_key_derivation.py      # Тесты Argon2 и PBKDF2
│   └── test_key_storage.py         # Тесты кэширования ключей
├── README.md                       # Документация
├── requirements.txt                # Зависимости
└── main.py                         # Точка входа
```
## Тестирование

```bash
python -m unittest discover tests
```
## Спринты

✅ Спринт 1: Фундамент

✅ Спринт 2: Управление ключами
