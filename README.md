<div align="center">

# 🍂 Бурмалда: Жёлудь-Ленд

**Игровой Telegram-бот на aiogram 3 и Supabase: виртуальные жёлуди, птички-бурмалдички, слоты и гнёзда.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://aiogram.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-burmalda--telegram--bot-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jaraslaukunin/burmalda-telegram-bot)

**[Возможности](#возможности)** · [Игровая механика](#игровая-механика) · [Технологии](#технологии) · [Быстрый старт](#быстрый-старт) · [Структура проекта](#структура-проекта) · [База данных](#база-данных) · [Лицензия](#лицензия)

</div>

---

## О проекте

**Бурмалда: Жёлудь-Ленд** — некоммерческий игровой Telegram-бот. Игрок получает 100 виртуальных желудей и стартовую птичку, играет в слоты, кубик и «Орёл или жёлудь», собирает коллекцию бурмалдичек, открывает гнёзда и соревнуется в рейтинге.

Жёлуди — только внутриигровая валюта: бот прямо сообщает, что депозитов, реальных ставок и вывода средств нет. Вся экономика и игровая логика живут в PostgreSQL (Supabase) в виде RPC-функций, поэтому баланс, ставки, начисления и уровни меняются атомарно и не зависят от состояния Python-процесса.

Бот работает через long polling, интерфейс — reply-клавиатура и inline-кнопки, а результаты игр приходят не текстом, а сгенерированными картинками 1080×1080 (Pillow).

## Возможности

| Раздел | Что умеет |
| :-- | :-- |
| 👤 Профиль | Баланс желудей, число сыгранных игр, активная птичка, её уровень, XP и редкость |
| 🎁 Ежедневка | 50 желудей + бонус активной птички и 10 XP; раз в календарный день по Минску |
| 🎮 Игры | Слот, кубик и «Орёл или жёлудь»; ставки 10 / 25 / 50; карточка результата с балансом и опытом |
| 🐦 Птички | Коллекция бурмалдичек, карточка птицы, описание, эффект и смена активной |
| 📦 Гнёзда | Покупка за 250 желудей, случайная птичка из пула, компенсация за дубликат |
| 🏆 Топ | Рейтинг топ-10 по желудям и отдельно по уровню птицы |
| 🎟 Промокод | Ввод кода в чате, награды: жёлуди, XP и гнёзда, лимит активаций |
| 🛠 Админка | Статистика, карточка игрока, начисление желудей и XP, выдача гнёзд и птиц, создание промокодов |
| 📜 Правила | Короткая памятка о виртуальности валюты и прокачке птички |

Команды администратора: `/admin` — панель, `/player TELEGRAM_ID` — карточка игрока, `/promo КОД ЖЁЛУДИ XP ГНЁЗДА ЛИМИТ` — создание промокода (лимит `0` — безлимитный).

## Игровая механика

| Игра | Механика | Выплата |
| :-- | :-- | :-- |
| 🎰 Бурмалда-Слот | 3 барабана, 5 равновероятных символов (🍂 🐦 🌰 🪵 🔥) | пара — ×2, три одинаковых — ×8 |
| 🎲 Жёлудь-Кубик | Бросок кубика 1–6 | 5 или 6 — ×2.5 |
| 🪙 Орёл или жёлудь | Игрок выбирает сторону | Угадал — ×2 |

**Опыт птички.** За игру начисляется `5 + min(ставка, 50)` XP, увеличенное на бонус птички и на бонус уровня (до +20%). Переход на 2-й уровень стоит 100 XP, каждый следующий — на 50 XP дороже. Уровни дают визуальные тиры: `rookie → uncommon → rare → epic → legendary → supreme` (с 5, 10, 25, 50 и 100 уровня).

**Птички.** В справочнике 7 бурмалдичек с редкостями от `common` до `mythic`. Эффекты: процент к опыту, прибавка желудей к ежедневке, шанс бонусного дропа или косметика. Стартовая — «Птенец Бурмалдички».

**Гнёзда.** Гнездо стоит 250 желудей, редкость разыгрывается по таблице:

| Редкость | Шанс | Компенсация за дубликат |
| :-- | --: | --: |
| 🌌 mythic | 0.5% | 5000 🌰 |
| 👑 legendary | 3% | 1000 🌰 |
| 🔥 epic | 11% | 250 🌰 |
| 🦉 rare | 25% | 75 🌰 |
| 🐦 common | 60.5% | 25 🌰 |

## Технологии

- **Python 3.12** — язык бота; в Docker используется образ `python:3.12-slim`.
- **aiogram 3** — асинхронный фреймворк: роутеры по разделам, inline-клавиатуры, long polling, HTML-разметка сообщений.
- **Supabase (PostgreSQL)** — база данных и вся игровая логика в RPC-функциях; бот обращается к ней через официальный `supabase` Python-клиент под `service_role`.
- **Pillow** — генерация PNG-карточек игр и меню.
- **python-dotenv** — конфигурация из `.env`.
- **Docker / Docker Compose** — упаковка и запуск бота с монтированием ассетов только на чтение.

## Быстрый старт

### Требования

- Python 3.12+
- проект Supabase (Postgres) с применёнными миграциями из `supabase/migrations`
- токен бота от [@BotFather](https://t.me/BotFather) и свой Telegram ID
- опционально Docker и Supabase CLI

### Установка и запуск

```bash
git clone https://github.com/jaraslaukunin/burmalda-telegram-bot.git
cd burmalda-telegram-bot

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # и заполнить значения
python -m app.main
```

Применить схему к своему проекту Supabase:

```bash
supabase link --project-ref <PROJECT_REF>
supabase db push
```

Запуск в Docker:

```bash
docker compose up -d --build
docker compose logs -f burmalda-bot
```

`docker-compose.yml` читает переменные из `.env` и монтирует `./assets` в контейнер как `/app/assets:ro`.

### Переменные окружения

Все переменные обязательны — `app/config.py` проверяет их при старте и падает с понятной ошибкой, если чего-то не хватает.

| Переменная | Назначение |
| :-- | :-- |
| `BOT_TOKEN` | Токен Telegram-бота |
| `SUPABASE_URL` | URL проекта Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role ключ для доступа к таблицам и RPC |
| `ADMIN_TELEGRAM_ID` | Telegram ID администратора для `/admin`, `/player` и `/promo` |

## Структура проекта

```text
burmalda-telegram-bot/
├── app/
│   ├── main.py              # Bot, Dispatcher, порядок подключения роутеров
│   ├── config.py            # чтение .env и валидация конфигурации
│   ├── handlers/            # start, games, profile, daily, birds, nests, leaderboard, promocodes, admin
│   ├── db/                  # supabase.py (клиент) и repository.py (вызовы RPC)
│   ├── services/            # economy.py и game_images.py — отрисовка карточек
│   ├── keyboards/           # reply-меню главного экрана
│   └── games/               # модули игр (сейчас пусты)
├── assets/
│   ├── slot/icons/          # 5 PNG-символов для барабанов слота
│   └── generated/           # пустая папка, кодом не используется
├── supabase/
│   ├── config.toml          # конфигурация локального Supabase
│   └── migrations/          # 12 SQL-миграций: схема, каталоги, RPC
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## База данных

Схема собрана миграциями Supabase CLI. Основные таблицы:

| Группа | Таблицы |
| :-- | :-- |
| Игроки | `profiles`, `bans`, `admin_audit_log` |
| Птицы | `bird_definitions` (каталог), `user_birds` (коллекция, одна активная на игрока) |
| Игры | `game_catalog`, `game_sessions`, `game_history` |
| Награды | `daily_claims`, `user_nests`, `user_quests` |
| Промокоды | `promocodes`, `promocode_redemptions` |

Ключевые RPC-функции: `ensure_player`, `claim_daily`, `play_slots`, `play_dice`, `play_coin`, `finish_game`, `buy_nest`, `open_nest`, `get_player_birds`, `set_active_bird`, `get_leaderboard`, `redeem_promocode` и админские `admin_*`.

На таблицах включён RLS: доступ у `anon` и `authenticated` отозван, работает только `service_role`, то есть бот обращается к базе server-side.

## Особенности реализации

- Ставка, баланс, выплата, опыт и уровень меняются в одной транзакции внутри `finish_game`, поэтому гонок между нажатиями кнопок нет; в обработчике дополнительно стоит блокировка повторной игры для одного пользователя.
- Карточки игр рисуются на сервере: фон-градиент, рамки, символы из `assets/slot/icons` и футер с балансом, опытом и уровнем.
- Шрифты для картинок заданы абсолютными путями к Arial в macOS, поэтому на Linux (в том числе в Docker) Pillow откатывается на встроенный шрифт — текст на карточках будет мельче. Это известное ограничение, а не ошибка конфигурации.
- `app/games/`, `app/services/cooldowns.py` и `app/services/users.py` пусты: игровая логика уже перенесена в SQL, а карточки рисует `game_images.py`.

## Лицензия

Проект распространяется под лицензией [**MIT**](LICENSE): код можно использовать, изменять и распространять, в том числе коммерчески, при сохранении текста лицензии и указания авторства.

---

<div align="center">

[github.com/jaraslaukunin/burmalda-telegram-bot](https://github.com/jaraslaukunin/burmalda-telegram-bot)

Если проект показался интересным — поставьте ⭐

</div>
