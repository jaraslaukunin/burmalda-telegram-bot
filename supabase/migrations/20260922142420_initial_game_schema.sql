create table public.profiles (
    telegram_id bigint primary key,
    username text,
    first_name text not null default 'Игрок',
    acorns integer not null default 100 check (acorns >= 0),
    xp integer not null default 0 check (xp >= 0),
    level integer not null default 1 check (level >= 1),
    last_daily_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.game_history (
    id bigint generated always as identity primary key,
    telegram_id bigint not null references public.profiles(telegram_id) on delete cascade,
    game_type text not null,
    bet integer not null default 0 check (bet >= 0),
    payout integer not null default 0 check (payout >= 0),
    result jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index game_history_telegram_id_created_at_idx
on public.game_history (telegram_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.game_history enable row level security;

revoke all on table public.profiles from anon, authenticated;
revoke all on table public.game_history from anon, authenticated;

grant select, insert, update, delete on table public.profiles to service_role;
grant select, insert, update, delete on table public.game_history to service_role;
grant usage, select on sequence public.game_history_id_seq to service_role;