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
Запуск
bash
python -m src
```
## Структура проекта
```bash
crypto/
├── src/
│   ├── core/
│   │   ├── crypto/
│   │   │   ├── __init__.py
│   │   │   ├── abstract.py
│   │   │   ├── authentication.py
│   │   │   ├── key_derivation.py
│   │   │   ├── key_storage.py
│   │   │   └── placeholder.py
│   │   ├── audit_manager.py
│   │   ├── config.py
│   │   ├── events.py
│   │   ├── key_manager.py
│   │   └── state_manager.py
│   ├── database/
│   │   ├── backup.py
│   │   ├── db.py
│   │   └── models.py
│   └── gui/
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── audit_log_dialog.py
│       │   ├── change_password_dialog.py
│       │   ├── entry_dialog.py
│       │   ├── login_dialog.py
│       │   ├── password_entry.py
│       │   └── setup_wizard.py
│       └── main_window.py
├── tests/
│   ├── test_authentication.py
│   ├── test_integration.py
│   ├── test_key_derivation.py
│   └── test_key_storage.py
├── README.md
├── requirements.txt
└── main.py
```
## Тестирование

```bash
python -m unittest discover tests
```
## Спринты

✅ Спринт 1: Фундамент

✅ Спринт 2: Управление ключами
