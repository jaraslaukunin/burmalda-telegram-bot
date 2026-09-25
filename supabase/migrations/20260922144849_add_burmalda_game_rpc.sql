begin;

-- ============================================================
-- БУРМАЛДА: атомарная игровая логика через PostgreSQL RPC.
-- Все функции вызываются только Python-ботом через service_role.
-- ============================================================

-- ------------------------------------------------------------
-- Вспомогательная функция: сколько XP нужно на следующий уровень.
-- Уровень 1 -> 2: 100 XP; 2 -> 3: 150 XP; ...
-- ------------------------------------------------------------
create or replace function public.xp_required_for_next_level(
    p_level integer
)
returns integer
language sql
immutable
set search_path = public
as $$
    select 100 + greatest(p_level - 1, 0) * 50;
$$;

-- ------------------------------------------------------------
-- Вспомогательная функция: визуальный статус птицы.
-- Максимального уровня нет, tiers заканчиваются на 100.
-- ------------------------------------------------------------
create or replace function public.bird_tier(
    p_level integer
)
returns text
language sql
immutable
set search_path = public
as $$
    select case
        when p_level >= 100 then 'supreme'
        when p_level >= 50 then 'legendary'
        when p_level >= 25 then 'epic'
        when p_level >= 10 then 'rare'
        when p_level >= 5 then 'uncommon'
        else 'rookie'
    end;
$$;

-- ------------------------------------------------------------
-- Начисляет XP одной птице, повышает уровни в цикле.
-- Возвращает уровень и XP после начисления.
-- ------------------------------------------------------------
create or replace function public.add_bird_xp(
    p_user_bird_id bigint,
    p_xp integer
)
returns table (
    bird_level integer,
    bird_xp integer,
    total_xp bigint,
    levels_gained integer,
    tier text
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_level integer;
    v_xp integer;
    v_total_xp bigint;
    v_required integer;
    v_levels_gained integer := 0;
begin
    if p_xp < 0 then
        raise exception 'XP cannot be negative';
    end if;

    select level, xp, total_xp
    into v_level, v_xp, v_total_xp
    from public.user_birds
    where id = p_user_bird_id
    for update;

    if not found then
        raise exception 'Bird not found';
    end if;

    v_xp := v_xp + p_xp;
    v_total_xp := v_total_xp + p_xp;
    v_required := public.xp_required_for_next_level(v_level);

    while v_xp >= v_required loop
        v_xp := v_xp - v_required;
        v_level := v_level + 1;
        v_levels_gained := v_levels_gained + 1;
        v_required := public.xp_required_for_next_level(v_level);
    end loop;

    update public.user_birds
    set
        level = v_level,
        xp = v_xp,
        total_xp = v_total_xp
    where id = p_user_bird_id;

    return query
    select
        v_level,
        v_xp,
        v_total_xp,
        v_levels_gained,
        public.bird_tier(v_level);
end;
$$;

-- ------------------------------------------------------------
-- Создаёт игрока, если он впервые открыл бота.
-- Старт: 100 желудей + Птенец Бурмалдички, активный.
-- Можно вызывать на каждом /start.
-- ------------------------------------------------------------
create or replace function public.ensure_player(
    p_telegram_id bigint,
    p_username text default null,
    p_first_name text default null,
    p_language text default 'ru'
)
returns table (
    is_new boolean,
    telegram_id bigint,
    acorns integer,
    active_bird_id bigint,
    active_bird_code text,
    active_bird_title text,
    bird_level integer,
    bird_xp integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_is_new boolean := false;
    v_bird_definition_id smallint;
    v_bird_id bigint;
    v_acorns integer;
    v_bird_code text;
    v_bird_title text;
    v_bird_level integer;
    v_bird_xp integer;
begin
    if p_language not in ('ru', 'en') then
        p_language := 'ru';
    end if;

    select id
    into v_bird_definition_id
    from public.bird_definitions
    where is_starter = true
      and is_enabled = true
    limit 1;

    if v_bird_definition_id is null then
        raise exception 'Starter bird is not configured';
    end if;

    insert into public.profiles (
        telegram_id,
        username,
        first_name,
        language,
        acorns,
        joined_at,
        last_seen_at
    )
    values (
        p_telegram_id,
        nullif(trim(p_username), ''),
        coalesce(nullif(trim(p_first_name), ''), 'Игрок'),
        p_language,
        100,
        now(),
        now()
    )
    on conflict (telegram_id) do update
    set
        username = excluded.username,
        first_name = excluded.first_name,
        last_seen_at = now()
    returning (xmax = 0), acorns
    into v_is_new, v_acorns;

    insert into public.user_birds (
        telegram_id,
        bird_definition_id,
        is_active,
        obtained_from
    )
    values (
        p_telegram_id,
        v_bird_definition_id,
        true,
        'starter'
    )
    on conflict (telegram_id, bird_definition_id) do nothing;

    select
        ub.id,
        bd.code,
        case
            when p_language = 'en' then bd.title_en
            else bd.title_ru
        end,
        ub.level,
        ub.xp
    into
        v_bird_id,
        v_bird_code,
        v_bird_title,
        v_bird_level,
        v_bird_xp
    from public.user_birds ub
    join public.bird_definitions bd
        on bd.id = ub.bird_definition_id
    where ub.telegram_id = p_telegram_id
      and ub.is_active = true
    limit 1;

    return query
    select
        v_is_new,
        p_telegram_id,
        v_acorns,
        v_bird_id,
        v_bird_code,
        v_bird_title,
        v_bird_level,
        v_bird_xp;
end;
$$;

-- ------------------------------------------------------------
-- Выдаёт daily: базово 50 желудей + bonus активной птицы.
-- Раз в 24 часа. Также даёт 10 XP активной птице.
-- ------------------------------------------------------------
create or replace function public.claim_daily(
    p_telegram_id bigint
)
returns table (
    ok boolean,
    reason text,
    acorns_awarded integer,
    bird_xp_awarded integer,
    balance_after integer,
    bird_level integer,
    bird_xp integer,
    levels_gained integer,
    next_claim_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_last_claim timestamptz;
    v_active_bird_id bigint;
    v_effect_type text;
    v_effect_value numeric;
    v_bonus integer := 0;
    v_reward integer := 50;
    v_balance integer;
    v_xp_result record;
    v_next_claim_at timestamptz;
begin
    perform 1
    from public.profiles
    where telegram_id = p_telegram_id
      and is_banned = false
    for update;

    if not found then
        return query
        select false, 'player_not_found', 0, 0, 0, 0, 0, 0, null::timestamptz;
        return;
    end if;

    select claimed_at
    into v_last_claim
    from public.daily_claims
    where telegram_id = p_telegram_id
    order by claimed_at desc
    limit 1;

    if v_last_claim is not null
       and v_last_claim + interval '24 hours' > now() then
        v_next_claim_at := v_last_claim + interval '24 hours';

        select acorns into v_balance
        from public.profiles
        where telegram_id = p_telegram_id;

        return query
        select false, 'cooldown', 0, 0, v_balance, 0, 0, 0, v_next_claim_at;
        return;
    end if;

    select
        ub.id,
        bd.effect_type,
        bd.effect_value
    into
        v_active_bird_id,
        v_effect_type,
        v_effect_value
    from public.user_birds ub
    join public.bird_definitions bd
        on bd.id = ub.bird_definition_id
    where ub.telegram_id = p_telegram_id
      and ub.is_active = true
    for update of ub;

    if v_active_bird_id is null then
        return query
        select false, 'active_bird_not_found', 0, 0, 0, 0, 0, 0, null::timestamptz;
        return;
    end if;

    if v_effect_type = 'daily_bonus' then
        v_bonus := floor(v_effect_value)::integer;
    end if;

    v_reward := v_reward + v_bonus;

    update public.profiles
    set acorns = acorns + v_reward
    where telegram_id = p_telegram_id
    returning acorns into v_balance;

    insert into public.daily_claims (
        telegram_id,
        acorns_awarded,
        bird_xp_awarded
    )
    values (
        p_telegram_id,
        v_reward,
        10
    );

    select *
    into v_xp_result
    from public.add_bird_xp(v_active_bird_id, 10);

    return query
    select
        true,
        'claimed',
        v_reward,
        10,
        v_balance,
        v_xp_result.bird_level,
        v_xp_result.bird_xp,
        v_xp_result.levels_gained,
        now() + interval '24 hours';
end;
$$;

-- ------------------------------------------------------------
-- Общая функция завершения игры.
-- Внутренняя, вызывается play_slots/play_dice/play_coin.
-- Списывает ставку, начисляет выплату, начисляет XP и логирует.
-- ------------------------------------------------------------
create or replace function public.finish_game(
    p_telegram_id bigint,
    p_game_code text,
    p_bet integer,
    p_payout integer,
    p_result jsonb
)
returns table (
    ok boolean,
    reason text,
    balance_before integer,
    balance_after integer,
    payout integer,
    xp_awarded integer,
    bird_level integer,
    bird_xp integer,
    levels_gained integer,
    bird_tier text
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance_before integer;
    v_balance_after integer;
    v_active_bird_id bigint;
    v_bird_level integer;
    v_effect_type text;
    v_effect_value numeric;
    v_xp_base integer;
    v_xp_multiplier numeric := 1;
    v_xp_awarded integer;
    v_xp_result record;
    v_game_exists boolean;
begin
    if p_bet < 0 or p_payout < 0 then
        raise exception 'Bet and payout cannot be negative';
    end if;

    select exists(
        select 1
        from public.game_catalog
        where code = p_game_code
          and is_enabled = true
    )
    into v_game_exists;

    if not v_game_exists then
        return query
        select false, 'game_not_available', 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    select acorns
    into v_balance_before
    from public.profiles
    where telegram_id = p_telegram_id
      and is_banned = false
    for update;

    if not found then
        return query
        select false, 'player_not_found', 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    if v_balance_before < p_bet then
        return query
        select false, 'not_enough_acorns', v_balance_before, v_balance_before, 0, 0, 0, 0, 0, '';
        return;
    end if;

    select
        ub.id,
        ub.level,
        bd.effect_type,
        bd.effect_value
    into
        v_active_bird_id,
        v_bird_level,
        v_effect_type,
        v_effect_value
    from public.user_birds ub
    join public.bird_definitions bd
        on bd.id = ub.bird_definition_id
    where ub.telegram_id = p_telegram_id
      and ub.is_active = true
    for update of ub;

    if v_active_bird_id is null then
        return query
        select false, 'active_bird_not_found', 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    -- XP: 5 + min(ставка, 50), бонус птички + бонус уровня (макс. +20%).
    v_xp_base := 5 + least(p_bet, 50);

    if v_effect_type = 'xp_bonus' then
        v_xp_multiplier := v_xp_multiplier + (v_effect_value / 100);
    end if;

    v_xp_multiplier := v_xp_multiplier
        + (least(greatest(v_bird_level - 1, 0), 20) / 100.0);

    v_xp_awarded := floor(v_xp_base * v_xp_multiplier)::integer;

    update public.profiles
    set
        acorns = acorns - p_bet + p_payout,
        games_played = games_played + 1,
        last_seen_at = now()
    where telegram_id = p_telegram_id
    returning acorns into v_balance_after;

    select *
    into v_xp_result
    from public.add_bird_xp(v_active_bird_id, v_xp_awarded);

    insert into public.game_sessions (
        telegram_id,
        active_bird_id,
        game_code,
        bet,
        payout,
        xp_awarded,
        balance_before,
        balance_after,
        result
    )
    values (
        p_telegram_id,
        v_active_bird_id,
        p_game_code,
        p_bet,
        p_payout,
        v_xp_awarded,
        v_balance_before,
        v_balance_after,
        coalesce(p_result, '{}'::jsonb)
    );

    return query
    select
        true,
        'played',
        v_balance_before,
        v_balance_after,
        p_payout,
        v_xp_awarded,
        v_xp_result.bird_level,
        v_xp_result.bird_xp,
        v_xp_result.levels_gained,
        v_xp_result.tier;
end;
$$;

-- ------------------------------------------------------------
-- Слот.
-- Весовая таблица символов + правила:
-- 3 одинаковых: x8
-- две одинаковых: x2
-- иначе 0
-- ------------------------------------------------------------
create or replace function public.play_slots(
    p_telegram_id bigint,
    p_bet integer
)
returns table (
    ok boolean,
    reason text,
    symbols text[],
    balance_before integer,
    balance_after integer,
    payout integer,
    xp_awarded integer,
    bird_level integer,
    bird_xp integer,
    levels_gained integer,
    bird_tier text
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_symbol_1 text;
    v_symbol_2 text;
    v_symbol_3 text;
    v_payout integer := 0;
    v_finish record;
begin
    -- Равные шансы сейчас; позже можно сделать weighted drops.
    v_symbol_1 := (array['🍂', '🐦', '🌰', '🪵', '🔥'])[floor(random() * 5 + 1)];
    v_symbol_2 := (array['🍂', '🐦', '🌰', '🪵', '🔥'])[floor(random() * 5 + 1)];
    v_symbol_3 := (array['🍂', '🐦', '🌰', '🪵', '🔥'])[floor(random() * 5 + 1)];

    if v_symbol_1 = v_symbol_2
       and v_symbol_2 = v_symbol_3 then
        v_payout := p_bet * 8;
    elsif v_symbol_1 = v_symbol_2
       or v_symbol_2 = v_symbol_3
       or v_symbol_1 = v_symbol_3 then
        v_payout := p_bet * 2;
    end if;

    select *
    into v_finish
    from public.finish_game(
        p_telegram_id,
        'slots',
        p_bet,
        v_payout,
        jsonb_build_object(
            'symbols',
            jsonb_build_array(v_symbol_1, v_symbol_2, v_symbol_3)
        )
    );

    return query
    select
        v_finish.ok,
        v_finish.reason,
        array[v_symbol_1, v_symbol_2, v_symbol_3],
        v_finish.balance_before,
        v_finish.balance_after,
        v_finish.payout,
        v_finish.xp_awarded,
        v_finish.bird_level,
        v_finish.bird_xp,
        v_finish.levels_gained,
        v_finish.bird_tier;
end;
$$;

-- ------------------------------------------------------------
-- Кубик.
-- 5/6: выплата x2.5, иначе 0.
-- ------------------------------------------------------------
create or replace function public.play_dice(
    p_telegram_id bigint,
    p_bet integer
)
returns table (
    ok boolean,
    reason text,
    roll integer,
    balance_before integer,
    balance_after integer,
    payout integer,
    xp_awarded integer,
    bird_level integer,
    bird_xp integer,
    levels_gained integer,
    bird_tier text
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_roll integer;
    v_payout integer := 0;
    v_finish record;
begin
    v_roll := floor(random() * 6 + 1)::integer;

    if v_roll >= 5 then
        v_payout := floor(p_bet * 2.5)::integer;
    end if;

    select *
    into v_finish
    from public.finish_game(
        p_telegram_id,
        'dice',
        p_bet,
        v_payout,
        jsonb_build_object('roll', v_roll)
    );

    return query
    select
        v_finish.ok,
        v_finish.reason,
        v_roll,
        v_finish.balance_before,
        v_finish.balance_after,
        v_finish.payout,
        v_finish.xp_awarded,
        v_finish.bird_level,
        v_finish.bird_xp,
        v_finish.levels_gained,
        v_finish.bird_tier;
end;
$$;

-- ------------------------------------------------------------
-- Орёл или жёлудь.
-- Игрок передаёт eagle/acorn; угадал — выплата x2.
-- ------------------------------------------------------------
create or replace function public.play_coin(
    p_telegram_id bigint,
    p_bet integer,
    p_choice text
)
returns table (
    ok boolean,
    reason text,
    choice text,
    result text,
    is_win boolean,
    balance_before integer,
    balance_after integer,
    payout integer,
    xp_awarded integer,
    bird_level integer,
    bird_xp integer,
    levels_gained integer,
    bird_tier text
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_result text;
    v_payout integer := 0;
    v_is_win boolean;
    v_finish record;
begin
    if p_choice not in ('eagle', 'acorn') then
        return query
        select false, 'invalid_choice', p_choice, '', false, 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    v_result := case when random() < 0.5 then 'eagle' else 'acorn' end;
    v_is_win := p_choice = v_result;

    if v_is_win then
        v_payout := p_bet * 2;
    end if;

    select *
    into v_finish
    from public.finish_game(
        p_telegram_id,
        'coin',
        p_bet,
        v_payout,
        jsonb_build_object(
            'choice', p_choice,
            'result', v_result,
            'is_win', v_is_win
        )
    );

    return query
    select
        v_finish.ok,
        v_finish.reason,
        p_choice,
        v_result,
        v_is_win,
        v_finish.balance_before,
        v_finish.balance_after,
        v_finish.payout,
        v_finish.xp_awarded,
        v_finish.bird_level,
        v_finish.bird_xp,
        v_finish.levels_gained,
        v_finish.bird_tier;
end;
$$;

-- ------------------------------------------------------------
-- Смена активной птицы.
-- ------------------------------------------------------------
create or replace function public.set_active_bird(
    p_telegram_id bigint,
    p_user_bird_id bigint
)
returns table (
    ok boolean,
    reason text,
    active_bird_id bigint,
    bird_code text,
    bird_level integer,
    bird_xp integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_bird_code text;
    v_bird_level integer;
    v_bird_xp integer;
begin
    perform 1
    from public.profiles
    where telegram_id = p_telegram_id
      and is_banned = false
    for update;

    if not found then
        return query
        select false, 'player_not_found', 0::bigint, '', 0, 0;
        return;
    end if;

    perform 1
    from public.user_birds
    where id = p_user_bird_id
      and telegram_id = p_telegram_id
    for update;

    if not found then
        return query
        select false, 'bird_not_found', 0::bigint, '', 0, 0;
        return;
    end if;

    update public.user_birds
    set is_active = false
    where telegram_id = p_telegram_id
      and is_active = true;

    update public.user_birds
    set is_active = true
    where id = p_user_bird_id
      and telegram_id = p_telegram_id;

    select
        bd.code,
        ub.level,
        ub.xp
    into
        v_bird_code,
        v_bird_level,
        v_bird_xp
    from public.user_birds ub
    join public.bird_definitions bd
        on bd.id = ub.bird_definition_id
    where ub.id = p_user_bird_id;

    return query
    select true, 'updated', p_user_bird_id, v_bird_code, v_bird_level, v_bird_xp;
end;
$$;

-- ------------------------------------------------------------
-- Топ-10: по желудям или уровню активной птицы.
-- ------------------------------------------------------------
create or replace function public.get_leaderboard(
    p_mode text default 'acorns',
    p_limit integer default 10
)
returns table (
    place bigint,
    telegram_id bigint,
    username text,
    first_name text,
    acorns integer,
    bird_level integer,
    bird_emoji text,
    bird_title text
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_mode not in ('acorns', 'level') then
        raise exception 'Invalid leaderboard mode';
    end if;

    p_limit := greatest(1, least(coalesce(p_limit, 10), 100));

    if p_mode = 'acorns' then
        return query
        select
            row_number() over (
                order by p.acorns desc, ub.level desc, p.joined_at asc
            ) as place,
            p.telegram_id,
            p.username,
            p.first_name,
            p.acorns,
            ub.level,
            bd.emoji,
            bd.title_ru
        from public.profiles p
        join public.user_birds ub
            on ub.telegram_id = p.telegram_id
           and ub.is_active = true
        join public.bird_definitions bd
            on bd.id = ub.bird_definition_id
        where p.is_banned = false
        order by p.acorns desc, ub.level desc, p.joined_at asc
        limit p_limit;
    else
        return query
        select
            row_number() over (
                order by ub.level desc, ub.total_xp desc, p.acorns desc
            ) as place,
            p.telegram_id,
            p.username,
            p.first_name,
            p.acorns,
            ub.level,
            bd.emoji,
            bd.title_ru
        from public.profiles p
        join public.user_birds ub
            on ub.telegram_id = p.telegram_id
           and ub.is_active = true
        join public.bird_definitions bd
            on bd.id = ub.bird_definition_id
        where p.is_banned = false
        order by ub.level desc, ub.total_xp desc, p.acorns desc
        limit p_limit;
    end if;
end;
$$;

-- ------------------------------------------------------------
-- Админская корректировка желудей.
-- SQL-функция перепроверяет, что вызов делает service_role,
-- а проверка твоего Telegram ID останется в Python-хэндлере.
-- ------------------------------------------------------------
create or replace function public.admin_adjust_acorns(
    p_target_telegram_id bigint,
    p_amount integer,
    p_admin_telegram_id bigint,
    p_reason text default null
)
returns table (
    ok boolean,
    balance_after integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance integer;
begin
    if p_amount = 0 then
        raise exception 'Amount cannot be zero';
    end if;

    update public.profiles
    set acorns = acorns + p_amount
    where telegram_id = p_target_telegram_id
      and acorns + p_amount >= 0
    returning acorns into v_balance;

    if v_balance is null then
        return query select false, 0;
        return;
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
        'adjust_acorns',
        jsonb_build_object(
            'amount', p_amount,
            'reason', p_reason
        )
    );

    return query select true, v_balance;
end;
$$;

-- ------------------------------------------------------------
-- Разрешаем service_role вызывать RPC-функции.
-- ------------------------------------------------------------
revoke all on function public.xp_required_for_next_level(integer) from public;
revoke all on function public.bird_tier(integer) from public;
revoke all on function public.add_bird_xp(bigint, integer) from public;
revoke all on function public.ensure_player(bigint, text, text, text) from public;
revoke all on function public.claim_daily(bigint) from public;
revoke all on function public.finish_game(bigint, text, integer, integer, jsonb) from public;
revoke all on function public.play_slots(bigint, integer) from public;
revoke all on function public.play_dice(bigint, integer) from public;
revoke all on function public.play_coin(bigint, integer, text) from public;
revoke all on function public.set_active_bird(bigint, bigint) from public;
revoke all on function public.get_leaderboard(text, integer) from public;
revoke all on function public.admin_adjust_acorns(bigint, integer, bigint, text) from public;

grant execute on function public.ensure_player(bigint, text, text, text) to service_role;
grant execute on function public.claim_daily(bigint) to service_role;
grant execute on function public.play_slots(bigint, integer) to service_role;
grant execute on function public.play_dice(bigint, integer) to service_role;
grant execute on function public.play_coin(bigint, integer, text) to service_role;
grant execute on function public.set_active_bird(bigint, bigint) to service_role;
grant execute on function public.get_leaderboard(text, integer) to service_role;
grant execute on function public.admin_adjust_acorns(bigint, integer, bigint, text) to service_role;

commit;