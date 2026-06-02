import sqlite3
import json
import os

db_path = input("Введите полный путь к вашему .db файлу: ")

if not os.path.exists(db_path):
    print("Файл не найден")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT sequence_number, entry_data FROM audit_log ORDER BY sequence_number")
rows = cursor.fetchall()

print(f"\nНайдено записей: {len(rows)}\n")

for seq, entry_data in rows:
    print(f"=== Запись #{seq} ===")
    if entry_data:
        data = json.loads(entry_data)
        print(f"  previous_hash: {data.get('previous_hash', 'НЕТ')[:20]}...")
        print(f"  entry_hash: {data.get('entry_hash', 'НЕТ')[:20]}...")
        print(f"  event_type: {data.get('event_type')}")
    else:
        print("  entry_data: ПУСТО!")
    print()

conn.close()