begin;

-- ============================================================
-- БУРМАЛДА: гнёзда, промокоды и расширенная админка.
-- Админ внутри БД: Jaraslau Kunin.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Гнёзда игрока.
-- Каждый nest — отдельная запись; можно выдавать из админки,
-- получать за ивенты или покупать за жёлуди.
-- ------------------------------------------------------------
create table if not exists public.user_nests (
    id bigint generated always as identity primary key,
    telegram_id bigint not null
        references public.profiles(telegram_id)
        on delete cascade,
    source text not null default 'shop'
        check (source in ('shop', 'promo', 'event', 'admin')),
    is_opened boolean not null default false,
    opened_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists user_nests_player_opened_idx
on public.user_nests (telegram_id, is_opened, created_at desc);

alter table public.user_nests enable row level security;

revoke all on table public.user_nests from anon, authenticated;
grant all privileges on table public.user_nests to service_role;
grant usage, select on sequence public.user_nests_id_seq to service_role;

-- ------------------------------------------------------------
-- 2. Промокоды.
-- reward_*: награда желудями, XP или гнёздами.
-- active / starts_at / expires_at / max_uses — контроль жизни кода.
-- ------------------------------------------------------------
create table if not exists public.promocodes (
    id bigint generated always as identity primary key,
    code text not null unique,
    reward_acorns integer not null default 0
        check (reward_acorns >= 0),
    reward_xp integer not null default 0
        check (reward_xp >= 0),
    reward_nests integer not null default 0
        check (reward_nests >= 0),
    max_uses integer,
    uses_count integer not null default 0
        check (uses_count >= 0),
    is_active boolean not null default true,
    starts_at timestamptz not null default now(),
    expires_at timestamptz,
    created_by bigint not null,
    created_at timestamptz not null default now(),
    check (
        reward_acorns > 0
        or reward_xp > 0
        or reward_nests > 0
    ),
    check (
        max_uses is null
        or max_uses > 0
    )
);

create unique index if not exists promocodes_code_upper_idx
on public.promocodes (upper(code));

-- ------------------------------------------------------------
-- 3. История активаций промокодов.
-- Один игрок может использовать один код один раз.
-- ------------------------------------------------------------
create table if not exists public.promocode_redemptions (
    id bigint generated always as identity primary key,
    promocode_id bigint not null
        references public.promocodes(id)
        on delete cascade,
    telegram_id bigint not null
        references public.profiles(telegram_id)
        on delete cascade,
    redeemed_at timestamptz not null default now(),
    unique (promocode_id, telegram_id)
);

create index if not exists promocode_redemptions_player_idx
on public.promocode_redemptions (telegram_id, redeemed_at desc);

alter table public.promocodes enable row level security;
alter table public.promocode_redemptions enable row level security;

revoke all on table public.promocodes from anon, authenticated;
revoke all on table public.promocode_redemptions from anon, authenticated;

grant all privileges on table public.promocodes to service_role;
grant all privileges on table public.promocode_redemptions to service_role;

grant usage, select on sequence public.promocodes_id_seq to service_role;
grant usage, select on sequence public.promocode_redemptions_id_seq to service_role;

-- ------------------------------------------------------------
-- 4. Служебная проверка администратора.
-- Не полагаемся только на Python: проверяем и в SQL.
-- ------------------------------------------------------------
create or replace function public.assert_burmalda_admin(
    p_admin_telegram_id bigint
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_admin_telegram_id <> 855318466 then
        raise exception 'Admin access denied';
    end if;
end;
$$;

-- ------------------------------------------------------------
-- 5. Найти карточку игрока для админки.
-- ------------------------------------------------------------
create or replace function public.admin_get_player(
    p_admin_telegram_id bigint,
    p_target_telegram_id bigint
)
returns table (
    telegram_id bigint,
    username text,
    first_name text,
    acorns integer,
    games_played integer,
    joined_at timestamptz,
    last_seen_at timestamptz,
    is_banned boolean,
    active_bird_id bigint,
    active_bird_title text,
    active_bird_emoji text,
    active_bird_level integer,
    active_bird_xp integer,
    nests_count bigint
)
language plpgsql
security definer
set search_path = public
as $$
begin
    perform public.assert_burmalda_admin(p_admin_telegram_id);

    return query
    select
        pr.telegram_id,
        pr.username,
        pr.first_name,
        pr.acorns,
        pr.games_played,
        pr.joined_at,
        pr.last_seen_at,
        pr.is_banned,
        ub.id,
        bd.title_ru,
        bd.emoji,
        ub.level,
        ub.xp,
        (
            select count(*)
            from public.user_nests as un
            where un.telegram_id = pr.telegram_id
              and un.is_opened = false
        )
    from public.profiles as pr
    left join public.user_birds as ub
        on ub.telegram_id = pr.telegram_id
       and ub.is_active = true
    left join public.bird_definitions as bd
        on bd.id = ub.bird_definition_id
    where pr.telegram_id = p_target_telegram_id;
end;
$$;

-- ------------------------------------------------------------
-- 6. Выдать гнёзда игроку.
-- ------------------------------------------------------------
create or replace function public.admin_grant_nests(
    p_admin_telegram_id bigint,
    p_target_telegram_id bigint,
    p_amount integer,
    p_reason text default null
)
returns table (
    ok boolean,
    nests_after bigint
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_nests_after bigint;
begin
    perform public.assert_burmalda_admin(p_admin_telegram_id);

    if p_amount <= 0 or p_amount > 100 then
        raise exception 'Nest amount must be between 1 and 100';
    end if;

    perform 1
    from public.profiles as pr
    where pr.telegram_id = p_target_telegram_id
    for update;

    if not found then
        return query select false, 0::bigint;
        return;
    end if;

    insert into public.user_nests (
        telegram_id,
        source
    )
    select
        p_target_telegram_id,
        'admin'
    from generate_series(1, p_amount);

    select count(*)
    into v_nests_after
    from public.user_nests as un
    where un.telegram_id = p_target_telegram_id
      and un.is_opened = false;

    insert into public.admin_audit_log (
        admin_telegram_id,
        target_telegram_id,
        action,
        payload
    )
    values (
        p_admin_telegram_id,
        p_target_telegram_id,
        'grant_nests',
        jsonb_build_object(
            'amount', p_amount,
            'reason', p_reason
        )
    );

    return query select true, v_nests_after;
end;
$$;

-- ------------------------------------------------------------
-- 7. Выдать конкретную птицу игроку.
-- Если такая уже есть, выдаём компенсацию желудями.
-- ------------------------------------------------------------
create or replace function public.admin_grant_bird(
    p_admin_telegram_id bigint,
    p_target_telegram_id bigint,
    p_bird_code text,
    p_reason text default null
)
returns table (
    ok boolean,
    is_duplicate boolean,
    bird_title text,
    compensation_acorns integer,
    balance_after integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_bird_definition_id smallint;
    v_bird_title text;
    v_rarity text;
    v_compensation integer := 0;
    v_is_duplicate boolean := false;
    v_balance integer;
begin
    perform public.assert_burmalda_admin(p_admin_telegram_id);

    select
        bd.id,
        bd.title_ru,
        bd.rarity
    into
        v_bird_definition_id,
        v_bird_title,
        v_rarity
    from public.bird_definitions as bd
    where bd.code = lower(trim(p_bird_code))
      and bd.is_enabled = true;

    if v_bird_definition_id is null then
        raise exception 'Bird definition not found';
    end if;

    perform 1
    from public.profiles as pr
    where pr.telegram_id = p_target_telegram_id
    for update;

    if not found then
        return query select false, false, '', 0, 0;
        return;
    end if;

    select exists (
        select 1
        from public.user_birds as ub
        where ub.telegram_id = p_target_telegram_id
          and ub.bird_definition_id = v_bird_definition_id
    )
    into v_is_duplicate;

    if v_is_duplicate then
        v_compensation := case v_rarity
            when 'common' then 25
            when 'rare' then 75
            when 'epic' then 250
            when 'legendary' then 1000
            when 'mythic' then 5000
            else 0
        end;

        update public.profiles as pr
        set acorns = pr.acorns + v_compensation
        where pr.telegram_id = p_target_telegram_id
        returning pr.acorns into v_balance;
    else
        insert into public.user_birds (
            telegram_id,
            bird_definition_id,
            is_active,
            obtained_from
        )
        values (
            p_target_telegram_id,
            v_bird_definition_id,
            false,
            'admin'
        );

        select pr.acorns
        into v_balance
        from public.profiles as pr
        where pr.telegram_id = p_target_telegram_id;
    end if;

    insert into public.admin_audit_log (
        admin_telegram_id,
        target_telegram_id,
        action,
        payload
    )
    values (
        p_admin_telegram_id,
        p_target_telegram_id,
        'grant_bird',
        jsonb_build_object(
            'bird_code', p_bird_code,
            'is_duplicate', v_is_duplicate,
            'compensation_acorns', v_compensation,
            'reason', p_reason
        )
    );

    return query
    select
        true,
        v_is_duplicate,
        v_bird_title,
        v_compensation,
        v_balance;
end;
$$;

-- ------------------------------------------------------------
-- 8. Купить гнездо за 250 желудей.
-- ------------------------------------------------------------
create or replace function public.buy_nest(
    p_telegram_id bigint
)
returns table (
    ok boolean,
    reason text,
    nests_after bigint,
    balance_after integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance integer;
    v_nests bigint;
    v_price integer := 250;
begin
    select pr.acorns
    into v_balance
    from public.profiles as pr
    where pr.telegram_id = p_telegram_id
      and pr.is_banned = false
    for update;

    if not found then
        return query select false, 'player_not_found', 0::bigint, 0;
        return;
    end if;

    if v_balance < v_price then
        return query select false, 'not_enough_acorns', 0::bigint, v_balance;
        return;
    end if;

    update public.profiles as pr
    set
        acorns = pr.acorns - v_price,
        last_seen_at = now()
    where pr.telegram_id = p_telegram_id
    returning pr.acorns into v_balance;

    insert into public.user_nests (
        telegram_id,
        source
    )
    values (
        p_telegram_id,
        'shop'
    );

    select count(*)
    into v_nests
    from public.user_nests as un
    where un.telegram_id = p_telegram_id
      and un.is_opened = false;

    return query
    select true, 'bought', v_nests, v_balance;
end;
$$;

-- ------------------------------------------------------------
-- 9. Открыть одно гнездо.
-- Редкости:
-- common 60%, rare 25%, epic 11%, legendary 3.5%, mythic 0.5%.
-- Дубликат -> компенсация желудями.
-- ------------------------------------------------------------
create or replace function public.open_nest(
    p_telegram_id bigint
)
returns table (
    ok boolean,
    reason text,
    bird_code text,
    bird_title text,
    bird_emoji text,
    bird_rarity text,
    is_duplicate boolean,
    compensation_acorns integer,
    balance_after integer,
    nests_after bigint
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_nest_id bigint;
    v_roll numeric;
    v_rarity text;
    v_bird_definition_id smallint;
    v_bird_code text;
    v_bird_title text;
    v_bird_emoji text;
    v_duplicate boolean := false;
    v_compensation integer := 0;
    v_balance integer;
    v_nests bigint;
begin
    perform 1
    from public.profiles as pr
    where pr.telegram_id = p_telegram_id
      and pr.is_banned = false
    for update;

    if not found then
        return query
        select false, 'player_not_found', '', '', '', '', false, 0, 0, 0::bigint;
        return;
    end if;

    select un.id
    into v_nest_id
    from public.user_nests as un
    where un.telegram_id = p_telegram_id
      and un.is_opened = false
    order by un.created_at asc
    limit 1
    for update skip locked;

    if v_nest_id is null then
        select pr.acorns
        into v_balance
        from public.profiles as pr
        where pr.telegram_id = p_telegram_id;

        return query
        select false, 'no_nests', '', '', '', '', false, 0, v_balance, 0::bigint;
        return;
    end if;

    v_roll := random() * 100;

    v_rarity := case
        when v_roll < 0.5 then 'mythic'
        when v_roll < 3.5 then 'legendary'
        when v_roll < 14.5 then 'epic'
        when v_roll < 39.5 then 'rare'
        else 'common'
    end;

    select
        bd.id,
        bd.code,
        bd.title_ru,
        bd.emoji
    into
        v_bird_definition_id,
        v_bird_code,
        v_bird_title,
        v_bird_emoji
    from public.bird_definitions as bd
    where bd.rarity = v_rarity
      and bd.is_enabled = true
    order by random()
    limit 1;

    if v_bird_definition_id is null then
        raise exception 'No enabled bird for rarity %', v_rarity;
    end if;

    update public.user_nests
    set
        is_opened = true,
        opened_at = now()
    where id = v_nest_id;

    select exists (
        select 1
        from public.user_birds as ub
        where ub.telegram_id = p_telegram_id
          and ub.bird_definition_id = v_bird_definition_id
    )
    into v_duplicate;

    if v_duplicate then
        v_compensation := case v_rarity
            when 'common' then 25
            when 'rare' then 75
            when 'epic' then 250
            when 'legendary' then 1000
            when 'mythic' then 5000
            else 0
        end;

        update public.profiles as pr
        set acorns = pr.acorns + v_compensation
        where pr.telegram_id = p_telegram_id
        returning pr.acorns into v_balance;
    else
        insert into public.user_birds (
            telegram_id,
            bird_definition_id,
            is_active,
            obtained_from
        )
        values (
            p_telegram_id,
            v_bird_definition_id,
            false,
            'nest'
        );

        select pr.acorns
        into v_balance
        from public.profiles as pr
        where pr.telegram_id = p_telegram_id;
    end if;

    select count(*)
    into v_nests
    from public.user_nests as un
    where un.telegram_id = p_telegram_id
      and un.is_opened = false;

    return query
    select
        true,
        'opened',
        v_bird_code,
        v_bird_title,
        v_bird_emoji,
        v_rarity,
        v_duplicate,
        v_compensation,
        v_balance,
        v_nests;
end;
$$;

-- ------------------------------------------------------------
-- 10. Создать промокод.
-- p_max_uses null = безлимитный.
-- ------------------------------------------------------------
create or replace function public.admin_create_promocode(
    p_admin_telegram_id bigint,
    p_code text,
    p_reward_acorns integer default 0,
    p_reward_xp integer default 0,
    p_reward_nests integer default 0,
    p_max_uses integer default null,
    p_expires_at timestamptz default null
)
returns table (
    ok boolean,
    code text,
    reward_acorns integer,
    reward_xp integer,
    reward_nests integer,
    max_uses integer,
    expires_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_code text;
begin
    perform public.assert_burmalda_admin(p_admin_telegram_id);

    v_code := upper(trim(p_code));

    if v_code !~ '^[A-Z0-9_-]{3,32}$' then
        raise exception 'Promocode must be 3-32 characters: A-Z, 0-9, _ or -';
    end if;

    if coalesce(p_reward_acorns, 0) < 0
       or coalesce(p_reward_xp, 0) < 0
       or coalesce(p_reward_nests, 0) < 0 then
        raise exception 'Rewards cannot be negative';
    end if;

    if coalesce(p_reward_acorns, 0) = 0
       and coalesce(p_reward_xp, 0) = 0
       and coalesce(p_reward_nests, 0) = 0 then
        raise exception 'Promocode must contain at least one reward';
    end if;

    if p_max_uses is not null and p_max_uses <= 0 then
        raise exception 'max_uses must be positive';
    end if;

    if p_expires_at is not null and p_expires_at <= now() then
        raise exception 'expires_at must be in the future';
    end if;

    insert into public.promocodes (
        code,
        reward_acorns,
        reward_xp,
        reward_nests,
        max_uses,
        expires_at,
        created_by
    )
    values (
        v_code,
        coalesce(p_reward_acorns, 0),
        coalesce(p_reward_xp, 0),
        coalesce(p_reward_nests, 0),
        p_max_uses,
        p_expires_at,
        p_admin_telegram_id
    )
    on conflict (code) do update
    set
        reward_acorns = excluded.reward_acorns,
        reward_xp = excluded.reward_xp,
        reward_nests = excluded.reward_nests,
        max_uses = excluded.max_uses,
        expires_at = excluded.expires_at,
        is_active = true;

    insert into public.admin_audit_log (
        admin_telegram_id,
        action,
        payload
    )
    values (
        p_admin_telegram_id,
        'create_promocode',
        jsonb_build_object(
            'code', v_code,
            'reward_acorns', p_reward_acorns,
            'reward_xp', p_reward_xp,
            'reward_nests', p_reward_nests,
            'max_uses', p_max_uses,
            'expires_at', p_expires_at
        )
    );

    return query
    select
        true,
        v_code,
        coalesce(p_reward_acorns, 0),
        coalesce(p_reward_xp, 0),
        coalesce(p_reward_nests, 0),
        p_max_uses,
        p_expires_at;
end;
$$;

-- ------------------------------------------------------------
-- 11. Активировать промокод игроком.
-- ------------------------------------------------------------
create or replace function public.redeem_promocode(
    p_telegram_id bigint,
    p_code text
)
returns table (
    ok boolean,
    reason text,
    reward_acorns integer,
    reward_xp integer,
    reward_nests integer,
    balance_after integer,
    bird_level integer,
    bird_xp integer,
    levels_gained integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_code text;
    v_promocode_id bigint;
    v_reward_acorns integer;
    v_reward_xp integer;
    v_reward_nests integer;
    v_max_uses integer;
    v_uses_count integer;
    v_active_bird_id bigint;
    v_balance integer;
    v_xp_result record;
begin
    v_code := upper(trim(p_code));

    perform 1
    from public.profiles as pr
    where pr.telegram_id = p_telegram_id
      and pr.is_banned = false
    for update;

    if not found then
        return query select false, 'player_not_found', 0, 0, 0, 0, 0, 0, 0;
        return;
    end if;

    select
        pc.id,
        pc.reward_acorns,
        pc.reward_xp,
        pc.reward_nests,
        pc.max_uses,
        pc.uses_count
    into
        v_promocode_id,
        v_reward_acorns,
        v_reward_xp,
        v_reward_nests,
        v_max_uses,
        v_uses_count
    from public.promocodes as pc
    where pc.code = v_code
      and pc.is_active = true
      and pc.starts_at <= now()
      and (pc.expires_at is null or pc.expires_at > now())
    for update;

    if v_promocode_id is null then
        return query select false, 'promocode_not_found', 0, 0, 0, 0, 0, 0, 0;
        return;
    end if;

    if v_max_uses is not null and v_uses_count >= v_max_uses then
        return query select false, 'promocode_limit_reached', 0, 0, 0, 0, 0, 0, 0;
        return;
    end if;

    if exists (
        select 1
        from public.promocode_redemptions as pr
        where pr.promocode_id = v_promocode_id
          and pr.telegram_id = p_telegram_id
    ) then
        return query select false, 'already_redeemed', 0, 0, 0, 0, 0, 0, 0;
        return;
    end if;

    update public.profiles as pr
    set
        acorns = pr.acorns + v_reward_acorns,
        last_seen_at = now()
    where pr.telegram_id = p_telegram_id
    returning pr.acorns into v_balance;

    if v_reward_nests > 0 then
        insert into public.user_nests (
            telegram_id,
            source
        )
        select
            p_telegram_id,
            'promo'
        from generate_series(1, v_reward_nests);
    end if;

    if v_reward_xp > 0 then
        select ub.id
        into v_active_bird_id
        from public.user_birds as ub
        where ub.telegram_id = p_telegram_id
          and ub.is_active = true
        for update;

        if v_active_bird_id is not null then
            select *
            into v_xp_result
            from public.add_bird_xp(v_active_bird_id, v_reward_xp);
        end if;
    end if;

    insert into public.promocode_redemptions (
        promocode_id,
        telegram_id
    )
    values (
        v_promocode_id,
        p_telegram_id
    );

    update public.promocodes as pc
    set uses_count = pc.uses_count + 1
    where pc.id = v_promocode_id;

    return query
    select
        true,
        'redeemed',
        v_reward_acorns,
        v_reward_xp,
        v_reward_nests,
        v_balance,
        coalesce(v_xp_result.result_level, 0),
        coalesce(v_xp_result.result_xp, 0),
        coalesce(v_xp_result.result_levels_gained, 0);
end;
$$;

-- ------------------------------------------------------------
-- 12. Закрываем EXECUTE для public и разрешаем только service_role.
-- ------------------------------------------------------------
revoke all on function public.assert_burmalda_admin(bigint) from public;
revoke all on function public.admin_get_player(bigint, bigint) from public;
revoke all on function public.admin_grant_nests(bigint, bigint, integer, text) from public;
revoke all on function public.admin_grant_bird(bigint, bigint, text, text) from public;
revoke all on function public.buy_nest(bigint) from public;
revoke all on function public.open_nest(bigint) from public;
revoke all on function public.admin_create_promocode(
    bigint, text, integer, integer, integer, integer, timestamptz
) from public;
revoke all on function public.redeem_promocode(bigint, text) from public;

grant execute on function public.admin_get_player(bigint, bigint) to service_role;
grant execute on function public.admin_grant_nests(bigint, bigint, integer, text) to service_role;
grant execute on function public.admin_grant_bird(bigint, bigint, text, text) to service_role;
grant execute on function public.buy_nest(bigint) to service_role;
grant execute on function public.open_nest(bigint) to service_role;
grant execute on function public.admin_create_promocode(
    bigint, text, integer, integer, integer, integer, timestamptz
) to service_role;
grant execute on function public.redeem_promocode(bigint, text) to service_role;

commit;