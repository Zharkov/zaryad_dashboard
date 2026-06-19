#!/usr/bin/env python3
"""
Управление пользователями ЗАРЯД.

Использование:
  python manage_admins.py list
  python manage_admins.py add <логин> <пароль>
  python manage_admins.py add <логин> <пароль> accountant
  python manage_admins.py delete <логин>
  python manage_admins.py passwd <логин> <новый_пароль>

Роли:
  admin      — полный доступ (по умолчанию)
  accountant — только просмотр и скачивание Excel
"""
import sys
from db.conn import db_migrate
from db.admin_users import list_admins, add_admin, delete_admin, change_password


def main():
    db_migrate()
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "list":
        admins = list_admins()
        if not admins:
            print("Нет пользователей в БД.")
        else:
            print(f"{'Логин':<20} {'Роль':<12} {'Создан'}")
            print("-" * 48)
            for a in admins:
                print(f"{a['username']:<20} {a['role']:<12} {a['created_at'][:10]}")

    elif cmd == "add":
        if len(args) < 3:
            print("Использование: python manage_admins.py add <логин> <пароль> [accountant]")
            sys.exit(1)
        role = args[3] if len(args) > 3 else "admin"
        ok, msg = add_admin(args[1], args[2], role)
        if ok:
            print(f"✓ Добавлен: {args[1]} (роль: {role})")
        else:
            print(f"✗ Ошибка: {msg}")

    elif cmd == "delete":
        if len(args) < 2:
            print("Использование: python manage_admins.py delete <логин>")
            sys.exit(1)
        if input(f"Удалить пользователя «{args[1]}»? [y/N] ").strip().lower() != "y":
            print("Отменено.")
            return
        ok = delete_admin(args[1])
        print(f"✓ Удалён: {args[1]}" if ok else f"✗ Не найден: {args[1]}")

    elif cmd == "passwd":
        if len(args) < 3:
            print("Использование: python manage_admins.py passwd <логин> <новый_пароль>")
            sys.exit(1)
        ok = change_password(args[1], args[2])
        print(f"✓ Пароль изменён: {args[1]}" if ok else f"✗ Не найден: {args[1]}")

    else:
        print(f"Неизвестная команда: {cmd}")
        print("Запусти без аргументов чтобы увидеть справку.")
        sys.exit(1)


if __name__ == "__main__":
    main()
