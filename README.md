# Multi-Platform Bot

Telegram-бот для кросс-постинга контента в Telegram каналы и VK группы.

## Возможности

- Публикация постов в несколько Telegram каналов одновременно
- Публикация в группы VK (ВКонтакте)
- Поддержка текста и фотографий
- Выбор целевых платформ для каждого поста
- История опубликованных постов
- Административная панель

## Требования

- Python 3.10 или выше
- SQLite (используется по умолчанию) или PostgreSQL
- Telegram Bot Token
- VK User Access Token (для загрузки фотографий)

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/Powarar/multiplatform-bot.git
cd multiplatform-bot
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
```

**Активация:**

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Откройте `.env` и заполните параметры:

```env
BOT_TOKEN=ваш_telegram_bot_token
ADMIN_IDS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///db.sqlite3
VK_USER_TOKEN=vk1.a.ваш_vk_user_token
```

## Получение токенов

### Telegram Bot Token

1. Найдите в Telegram бота [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя бота и его username
4. Скопируйте полученный токен в параметр `BOT_TOKEN`

**Как узнать Admin ID:**
- Откройте бота [@userinfobot](https://t.me/userinfobot)
- Отправьте `/start`
- Скопируйте ваш ID в параметр `ADMIN_IDS`

### VK User Access Token

Для загрузки фотографий в VK используется user access token через Kate Mobile.

**Получение токена:**

1. Откройте в браузере ссылку:

```
https://oauth.vk.com/authorize?client_id=2685278&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=wall,photos,groups,offline&response_type=token&v=5.131
```

2. Авторизуйтесь в VK и разрешите доступ приложению

3. После авторизации VK перенаправит на пустую страницу. В адресной строке найдите параметр `access_token`:

```
https://oauth.vk.com/blank.html#access_token=vk1.a.ТОКЕН&expires_in=0&user_id=123456
```

4. Скопируйте значение между `access_token=` и `&expires_in` (начинается с `vk1.a.`)

5. Вставьте токен в `.env`:

```env
VK_USER_TOKEN=vk1.a.ваш_скопированный_токен
```

**Важно:**
- Параметр `expires_in=0` означает бессрочный токен
- Токен от Kate Mobile не требует создания приложения VK
- Это официальное приложение VK для iOS/Android

## Запуск

```bash
python main.py
```

## Использование

### Команды бота

**Основные команды:**
- `/start` - Начало работы
- `/help` - Справка
- `/add_community` - Добавить Telegram канал или VK группу
- `/my_communities` - Список добавленных сообществ
- `/new_post` - Создать новый пост
- `/my_posts` - История постов

**Для администраторов:**
- `/admin` - Административная панель

### Добавление Telegram канала

1. Создайте канал в Telegram
2. Добавьте бота в администраторы с правами на публикацию
3. В боте: `/add_community` → выберите "Telegram"
4. Отправьте ID канала:
   - Публичный канал: `@channel_name`
   - Приватный канал: `-1001234567890`

**Узнать ID приватного канала:**
- Перешлите любое сообщение из канала боту [@username_to_id_bot](https://t.me/username_to_id_bot)

### Добавление VK группы

1. Откройте вашу группу VK (вы должны быть администратором)
2. В боте: `/add_community` → выберите "VK"
3. Перейдите по ссылке для авторизации
4. Разрешите доступ
5. Скопируйте `access_token` из адресной строки
6. Отправьте токен боту
7. Отправьте ID или короткое имя группы:
   - По ID: `123456789`
   - По имени: `mygroup` или `https://vk.com/mygroup`

### Создание поста

1. `/new_post`
2. Введите текст поста
3. Опционально: отправьте фотографии
4. Нажмите "Далее"
5. Выберите сообщества для публикации
6. Подтвердите

## Структура проекта

```
multiplatform-bot/
├── main.py                 # Точка входа
├── config.py               # Конфигурация
├── database.py             # Инициализация БД
├── models.py               # SQLAlchemy модели
├── requirements.txt        # Зависимости
├── .env.example            # Шаблон переменных окружения
├── handlers/               # Обработчики команд
│   ├── __init__.py
│   ├── start.py            # /start и /help
│   ├── communities.py      # Управление сообществами
│   ├── posts.py            # Создание и публикация постов
│   └── admin.py            # Админ-панель
└── services/               # Бизнес-логика
    ├── __init__.py
    ├── community_service.py
    ├── post_service.py
    └── vk_service.py       # Интеграция с VK API
```

## Технические детали

### Архитектура VK интеграции

Используется два типа токенов:

1. **VK User Token** (`VK_USER_TOKEN` в `.env`) - для загрузки фотографий через `photos.getWallUploadServer`
2. **VK Group Token** (сохраняется при добавлении группы) - для публикации постов через `wall.post`

Это необходимо из-за ограничения VK API: метод загрузки фотографий требует user token, а публикация работает с group token.

### База данных

По умолчанию используется SQLite. Для PostgreSQL измените `DATABASE_URL`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

Установите драйвер:

```bash
pip install asyncpg
```

## Решение проблем

### BOT_TOKEN not found

Проверьте, что файл `.env` создан и содержит параметр `BOT_TOKEN`.

### Бот не является администратором канала

Добавьте бота в администраторы Telegram канала с правами на публикацию сообщений.

### VK: Ошибка 27 при загрузке фото

Убедитесь, что в `.env` указан корректный `VK_USER_TOKEN`, полученный через Kate Mobile. Токен должен начинаться с `vk1.a.`

### Invalid access_token (VK)

Решение:
1. Проверьте, что токен скопирован полностью
2. Убедитесь, что при получении токена были права `wall,photos,groups,offline`
3. Получите новый токен через Kate Mobile

### VK группа не найдена

Проверьте:
- Вы администратор группы
- ID или имя группы указаны правильно
- Группа не заблокирована

