#!/usr/bin/env bash
# start.sh
pip install -r requirements.txt

# Применяем миграции при каждом запуске
echo "Applying database migrations..."
python manage.py makemigrations users --noinput
python manage.py makemigrations products --noinput
python manage.py makemigrations orders --noinput
python manage.py makemigrations --noinput
python manage.py makemigrations --noinput
python manage.py migrate --noinput

#обновляем статические файлы
python manage.py collectstatic --clear --noinput

# Создаём суперпользователя, если его нет (для первого запуска)
echo "Checking for superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    print("Creating superuser...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Superuser created successfully!")
else:
    print("Superuser already exists")
EOF
