begin;

-- ============================================================
-- БУРМАЛДА: расширение существующей игровой схемы.
-- Старые tables profiles + game_history сохраняем.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Расширяем существующий профиль игрока.
-- xp и level пока НЕ удаляем: они остаются для совместимости.
-- Главный прогресс птиц будет в user_birds.
-- ------------------------------------------------------------
alter table public.profiles
    add column if not exists language text not null default 'ru'
        check (language in ('ru', 'en')),
    add column if not exists games_played integer not null default 0
        check (games_played >= 0),
    add column if not exists joined_at timestamptz not null default now(),
    add column if not exists last_seen_at timestamptz not null default now(),
    add column if not exists is_banned boolean not null default false;

update public.profiles
set joined_at = coalesce(joined_at, created_at),
    last_seen_at = coalesce(last_seen_at, updated_at, created_at);

create index if not exists profiles_acorns_desc_idx
on public.profiles (acorns desc);

create index if not exists profiles_joined_at_desc_idx
on public.profiles (joined_at desc);

-- ------------------------------------------------------------
-- 2. Триггер для updated_at.
-- ------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;

create trigger profiles_set_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

-- ------------------------------------------------------------
-- 3. Справочник птичек-бурмалдичек.
-- ------------------------------------------------------------
create table if not exists public.bird_definitions (
    id smallint generated always as identity primary key,
    code text not null unique,
    title_ru text not null,
    title_en text not null,
    emoji text not null default '🐦',
    rarity text not null
        check (rarity in (
            'common',
            'rare',
            'epic',
            'legendary',
            'mythic'
        )),
    description_ru text not null,
    description_en text not null,
    effect_type text not null default 'xp_bonus'
        check (effect_type in (
            'xp_bonus',
            'daily_bonus',
            'bonus_drop',
            'cosmetic'
        )),
    effect_value numeric(8, 2) not null default 0,
    sort_order smallint not null default 0,
    is_starter boolean not null default false,
    is_enabled boolean not null default true,
    created_at timestamptz not null default now()
);

create unique index if not exists bird_definitions_one_starter_idx
on public.bird_definitions (is_starter)
where is_starter;

-- ------------------------------------------------------------
-- 4. Коллекция птиц игрока.
-- Только одна активная птица на каждого игрока.
-- Одна птица одного типа в коллекции: дубликат компенсируется.
-- ------------------------------------------------------------
create table if not exists public.user_birds (
    id bigint generated always as identity primary key,
    telegram_id bigint not null
        references public.profiles(telegram_id)
        on delete cascade,
    bird_definition_id smallint not null
        references public.bird_definitions(id)
        on delete restrict,
    nickname text,
    level integer not null default 1
        check (level >= 1),
    xp integer not null default 0
        check (xp >= 0),
    total_xp bigint not null default 0
        check (total_xp >= 0),
    is_active boolean not null default false,
    obtained_from text not null default 'starter'
        check (obtained_from in (
            'starter',
            'nest',
            'shop',
            'event',
            'admin'
        )),
    obtained_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (telegram_id, bird_definition_id)
);

create index if not exists user_birds_telegram_id_idx
on public.user_birds (telegram_id);

create index if not exists user_birds_level_desc_idx
on public.user_birds (level desc);

create unique index if not exists user_birds_one_active_idx
on public.user_birds (telegram_id)
where is_active;

drop trigger if exists user_birds_set_updated_at on public.user_birds;

create trigger user_birds_set_updated_at
before update on public.user_birds
for each row
execute function public.set_updated_at();

-- ------------------------------------------------------------
-- 5. Каталог игр.
-- Сразу создаём основу для расширения, но пока включаем 3 игры.
-- ------------------------------------------------------------
create table if not exists public.game_catalog (
    code text primary key,
    title_ru text not null,
    title_en text not null,
    emoji text not null,
    description_ru text not null,
    description_en text not null,
    min_bird_level integer not null default 1
        check (min_bird_level >= 1),
    min_bet integer not null default 0
        check (min_bet >= 0),
    max_bet integer not null default 100
        check (max_bet >= min_bet),
    is_risk boolean not null default true,
    is_enabled boolean not null default true,
    sort_order smallint not null default 0,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- 6. Новая история игровых сессий.
-- game_history оставляем для совместимости со старым Python-кодом.
-- ------------------------------------------------------------
create table if not exists public.game_sessions (
    id bigint generated always as identity primary key,
    telegram_id bigint not null
        references public.profiles(telegram_id)
        on delete cascade,
    active_bird_id bigint
        references public.user_birds(id)
        on delete set null,
    game_code text not null
        references public.game_catalog(code)
        on delete restrict,
    bet integer not null default 0
        check (bet >= 0),
    payout integer not null default 0
        check (payout >= 0),
    xp_awarded integer not null default 0
        check (xp_awarded >= 0),
    balance_before integer not null
        check (balance_before >= 0),
    balance_after integer not null
        check (balance_after >= 0),
    result jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists game_sessions_player_created_idx
on public.game_sessions (telegram_id, created_at desc);

create index if not exists game_sessions_game_created_idx
on public.game_sessions (game_code, created_at desc);

-- ------------------------------------------------------------
-- 7. История ежедневных наград.
-- ------------------------------------------------------------
create table if not exists public.daily_claims (
    id bigint generated always as identity primary key,
    telegram_id bigint not null
        references public.profiles(telegram_id)
        on delete cascade,
    acorns_awarded integer not null
        check (acorns_awarded >= 0),
    bird_xp_awarded integer not null default 0
        check (bird_xp_awarded >= 0),
    claimed_at timestamptz not null default now()
);

create index if not exists daily_claims_player_claimed_idx
on public.daily_claims (telegram_id, claimed_at desc);

-- ------------------------------------------------------------
-- 8. Безопасные квесты и прогресс.
-- ------------------------------------------------------------
create table if not exists public.user_quests (
    id bigint generated always as identity primary key,
    telegram_id bigint not null
        references public.profiles(telegram_id)
        on delete cascade,
    quest_code text not null,
    title_ru text not null,
    title_en text not null,
    progress integer not null default 0
        check (progress >= 0),
    target integer not null default 1
        check (target > 0),
    reward_acorns integer not null default 0
        check (reward_acorns >= 0),
    reward_xp integer not null default 0
        check (reward_xp >= 0),
    status text not null default 'active'
        check (status in ('active', 'completed', 'claimed', 'expired')),
    expires_at timestamptz,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    claimed_at timestamptz
);

create index if not exists user_quests_player_status_idx
on public.user_quests (telegram_id, status);

-- ------------------------------------------------------------
-- 9. Логи администратора и бан-лист.
-- ------------------------------------------------------------
create table if not exists public.admin_audit_log (
    id bigint generated always as identity primary key,
    admin_telegram_id bigint not null,
    target_telegram_id bigint
        references public.profiles(telegram_id)
        on delete set null,
    action text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists admin_audit_log_created_idx
on public.admin_audit_log (created_at desc);

create table if not exists public.bans (
    telegram_id bigint primary key
        references public.profiles(telegram_id)
        on delete cascade,
    reason text,
    banned_by bigint not null,
    banned_at timestamptz not null default now(),
    expires_at timestamptz,
    is_active boolean not null default true
);

-- ------------------------------------------------------------
-- 10. RLS и доступ только server-side боту.
-- ------------------------------------------------------------
alter table public.bird_definitions enable row level security;
alter table public.user_birds enable row level security;
alter table public.game_catalog enable row level security;
alter table public.game_sessions enable row level security;
alter table public.daily_claims enable row level security;
alter table public.user_quests enable row level security;
alter table public.admin_audit_log enable row level security;
alter table public.bans enable row level security;

revoke all on table public.bird_definitions from anon, authenticated;
revoke all on table public.user_birds from anon, authenticated;
revoke all on table public.game_catalog from anon, authenticated;
revoke all on table public.game_sessions from anon, authenticated;
revoke all on table public.daily_claims from anon, authenticated;
revoke all on table public.user_quests from anon, authenticated;
revoke all on table public.admin_audit_log from anon, authenticated;
revoke all on table public.bans from anon, authenticated;

grant all privileges on table public.bird_definitions to service_role;
grant all privileges on table public.user_birds to service_role;
grant all privileges on table public.game_catalog to service_role;
grant all privileges on table public.game_sessions to service_role;
grant all privileges on table public.daily_claims to service_role;
grant all privileges on table public.user_quests to service_role;
grant all privileges on table public.admin_audit_log to service_role;
grant all privileges on table public.bans to service_role;

grant usage, select on all sequences in schema public to service_role;

-- ------------------------------------------------------------
-- 11. Каталог птичек.
-- on conflict гарантирует, что повторно не появятся дубликаты.
-- ------------------------------------------------------------
insert into public.bird_definitions (
    code, title_ru, title_en, emoji, rarity,
    description_ru, description_en,
    effect_type, effect_value, sort_order, is_starter
)
values
(
    'burmaldichka_chick',
    'Птенец Бурмалдички',
    'Burmaldichka Chick',
    '🐥',
    'common',
    'Твоя первая птичка. Она растёт вместе с тобой.',
    'Your first bird. It grows with you.',
    'xp_bonus',
    2.00,
    1,
    true
),
(
    'forest_burmaldichka',
    'Лесная Бурмалдичка',
    'Forest Burmaldichka',
    '🐦',
    'common',
    'Знает все лесные тропы. Добавляет жёлуди к ежедневной награде.',
    'Knows every forest trail. Adds acorns to daily rewards.',
    'daily_bonus',
    1.00,
    2,
    false
),
(
    'night_burmaldichka',
    'Ночная Бурмалдичка',
    'Night Burmaldichka',
    '🦉',
    'rare',
    'Лучше всего чувствует себя после заката. Даёт повышенный опыт.',
    'Feels best after sunset. Grants more experience.',
    'xp_bonus',
    5.00,
    3,
    false
),
(
    'acorn_guardian',
    'Жёлудь-Страж',
    'Acorn Guardian',
    '🦅',
    'rare',
    'Иногда приносит маленький дополнительный приз.',
    'Sometimes brings a small bonus prize.',
    'bonus_drop',
    3.00,
    4,
    false
),
(
    'firewing_burmaldichka',
    'Огнекрылая Бурмалдичка',
    'Firewing Burmaldichka',
    '🔥',
    'epic',
    'В её крыльях горит азарт. Даёт много опыта.',
    'Its wings burn with spirit. Grants more experience.',
    'xp_bonus',
    10.00,
    5,
    false
),
(
    'supreme_burmaldichka',
    'Верховная Бурмалдичка',
    'Supreme Burmaldichka',
    '👑',
    'legendary',
    'Легенда Бурмалды. Усиливает ежедневную награду.',
    'Legend of Burmalda. Boosts daily rewards.',
    'daily_bonus',
    5.00,
    6,
    false
),
(
    'mythic_burmalda',
    'Мифическая Бурмалда',
    'Mythic Burmalda',
    '🌌',
    'mythic',
    'Уникальная птичка с особой косметикой.',
    'A unique bird with special cosmetics.',
    'cosmetic',
    0.00,
    7,
    false
)
on conflict (code) do update
set
    title_ru = excluded.title_ru,
    title_en = excluded.title_en,
    emoji = excluded.emoji,
    rarity = excluded.rarity,
    description_ru = excluded.description_ru,
    description_en = excluded.description_en,
    effect_type = excluded.effect_type,
    effect_value = excluded.effect_value,
    sort_order = excluded.sort_order,
    is_starter = excluded.is_starter,
    is_enabled = true;

-- ------------------------------------------------------------
-- 12. Каталог игр.
-- Включены slot/dice/coin, остальное уже подготовлено.
-- ------------------------------------------------------------
insert into public.game_catalog (
    code, title_ru, title_en, emoji,
    description_ru, description_en,
    min_bird_level, min_bet, max_bet,
    is_risk, is_enabled, sort_order
)
values
(
    'slots',
    'Бурмалда-Слот',
    'Burmalda Slots',
    '🎰',
    'Собери комбинацию символов и забери награду.',
    'Match symbols and claim a reward.',
    1, 10, 100, true, true, 1
),
(
    'dice',
    'Жёлудь-Кубик',
    'Acorn Dice',
    '🎲',
    'Брось кубик: 5 или 6 приносят выигрыш.',
    'Roll the dice: 5 or 6 brings a win.',
    1, 10, 100, true, true, 2
),
(
    'coin',
    'Орёл или жёлудь',
    'Eagle or Acorn',
    '🪙',
    'Выбери сторону и попробуй угадать.',
    'Pick a side and try to guess it.',
    1, 10, 100, true, true, 3
),
(
    'guess_number',
    'Угадай число',
    'Guess the Number',
    '🎯',
    'Выбери число от 1 до 5.',
    'Choose a number from 1 to 5.',
    3, 10, 100, true, false, 4
),
(
    'wheel',
    'Колесо Бурмалды',
    'Burmalda Wheel',
    '🎡',
    'Крути колесо и лови награды.',
    'Spin the wheel and catch rewards.',
    5, 25, 100, true, false, 5
),
(
    'nest',
    'Гнездо птички',
    'Bird Nest',
    '📦',
    'Открой гнездо за 250 желудей и получи птичку.',
    'Open a nest for 250 acorns and get a bird.',
    3, 250, 250, true, false, 6
),
(
    'forest_walk',
    'Прогулка по лесу',
    'Forest Walk',
    '🌳',
    'Бесплатная прогулка с небольшой наградой.',
    'A free walk with a small reward.',
    1, 0, 0, false, false, 7
),
(
    'forest_riddle',
    'Лесная загадка',
    'Forest Riddle',
    '🧩',
    'Безопасная ежедневная загадка.',
    'A safe daily riddle.',
    1, 0, 0, false, false, 8
),
(
    'boss_event',
    'Битва за жёлудь',
    'Battle for the Acorn',
    '⚔️',
    'Совместный PvE-ивент против лесного босса.',
    'A cooperative PvE event against a forest boss.',
    10, 25, 50, false, false, 9
)
on conflict (code) do update
set
    title_ru = excluded.title_ru,
    title_en = excluded.title_en,
    emoji = excluded.emoji,
    description_ru = excluded.description_ru,
    description_en = excluded.description_en,
    min_bird_level = excluded.min_bird_level,
    min_bet = excluded.min_bet,
    max_bet = excluded.max_bet,
    is_risk = excluded.is_risk,
    is_enabled = excluded.is_enabled,
    sort_order = excluded.sort_order;

commit;