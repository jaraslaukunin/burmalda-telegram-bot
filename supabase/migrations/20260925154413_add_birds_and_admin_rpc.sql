begin;

-- ============================================================
-- Список птиц игрока.
-- ============================================================
create or replace function public.get_player_birds(
    p_telegram_id bigint,
    p_language text default 'ru'
)
returns table (
    user_bird_id bigint,
    bird_code text,
    bird_title text,
    bird_emoji text,
    bird_rarity text,
    bird_description text,
    bird_level integer,
    bird_xp integer,
    bird_total_xp bigint,
    is_active boolean,
    effect_type text,
    effect_value numeric
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_language not in ('ru', 'en') then
        p_language := 'ru';
    end if;

    return query
    select
        ub.id,
        bd.code,
        case
            when p_language = 'en' then bd.title_en
            else bd.title_ru
        end,
        bd.emoji,
        bd.rarity,
        case
            when p_language = 'en' then bd.description_en
            else bd.description_ru
        end,
        ub.level,
        ub.xp,
        ub.total_xp,
        ub.is_active,
        bd.effect_type,
        bd.effect_value
    from public.user_birds as ub
    join public.bird_definitions as bd
        on bd.id = ub.bird_definition_id
    where ub.telegram_id = p_telegram_id
    order by ub.is_active desc, ub.level desc, ub.obtained_at asc;
end;
$$;

-- ============================================================
-- Активная птичка. Переопределяем с нормальными алиасами,
-- чтобы не было конфликтов с именами полей RETURNS TABLE.
-- ============================================================
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
    from public.profiles as pr
    where pr.telegram_id = p_telegram_id
      and pr.is_banned = false
    for update;

    if not found then
        return query
        select false, 'player_not_found', 0::bigint, '', 0, 0;
        return;
    end if;

    perform 1
    from public.user_birds as ub
    where ub.id = p_user_bird_id
      and ub.telegram_id = p_telegram_id
    for update;

    if not found then
        return query
        select false, 'bird_not_found', 0::bigint, '', 0, 0;
        return;
    end if;

    update public.user_birds as ub
    set is_active = false
    where ub.telegram_id = p_telegram_id
      and ub.is_active = true;

    update public.user_birds as ub
    set is_active = true
    where ub.id = p_user_bird_id
      and ub.telegram_id = p_telegram_id;

    select
        bd.code,
        ub.level,
        ub.xp
    into
        v_bird_code,
        v_bird_level,
        v_bird_xp
    from public.user_birds as ub
    join public.bird_definitions as bd
        on bd.id = ub.bird_definition_id
    where ub.id = p_user_bird_id;

    return query
    select
        true,
        'updated',
        p_user_bird_id,
        v_bird_code,
        v_bird_level,
        v_bird_xp;
end;
$$;

-- ============================================================
-- Админ: статистика бота.
-- ============================================================
create or replace function public.admin_get_stats()
returns table (
    players_count bigint,
    active_players_24h bigint,
    games_count bigint,
    total_acorns bigint,
    birds_count bigint,
    banned_count bigint
)
language sql
security definer
set search_path = public
as $$
    select
        (select count(*) from public.profiles),
        (
            select count(*)
            from public.profiles
            where last_seen_at >= now() - interval '24 hours'
        ),
        (select count(*) from public.game_sessions),
        (select coalesce(sum(acorns), 0) from public.profiles),
        (select count(*) from public.user_birds),
        (
            select count(*)
            from public.bans
            where is_active = true
              and (expires_at is null or expires_at > now())
        );
$$;

-- ============================================================
-- Админ: выдать/списать XP у выбранной активной птицы.
-- ============================================================
create or replace function public.admin_adjust_bird_xp(
    p_target_telegram_id bigint,
    p_amount integer,
    p_admin_telegram_id bigint,
    p_reason text default null
)
returns table (
    ok boolean,
    bird_level integer,
    bird_xp integer,
    levels_gained integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_active_bird_id bigint;
    v_xp_result record;
begin
    if p_amount <= 0 then
        raise exception 'XP amount must be positive';
    end if;

    select ub.id
    into v_active_bird_id
    from public.user_birds as ub
    where ub.telegram_id = p_target_telegram_id
      and ub.is_active = true
    for update;

    if v_active_bird_id is null then
        return query
        select false, 0, 0, 0;
        return;
    end if;

    select *
    into v_xp_result
    from public.add_bird_xp(v_active_bird_id, p_amount);

    insert into public.admin_audit_log (
        admin_telegram_id,
        target_telegram_id,
        action,
        payload
    )
    values (
        p_admin_telegram_id,
        p_target_telegram_id,
        'adjust_bird_xp',
        jsonb_build_object(
            'amount', p_amount,
            'reason', p_reason
        )
    );

    return query
    select
        true,
        v_xp_result.result_level,
        v_xp_result.result_xp,
        v_xp_result.result_levels_gained;
end;
$$;

revoke all on function public.get_player_birds(bigint, text) from public;
revoke all on function public.set_active_bird(bigint, bigint) from public;
revoke all on function public.admin_get_stats() from public;
revoke all on function public.admin_adjust_bird_xp(bigint, integer, bigint, text) from public;

grant execute on function public.get_player_birds(bigint, text) to service_role;
grant execute on function public.set_active_bird(bigint, bigint) to service_role;
grant execute on function public.admin_get_stats() to service_role;
grant execute on function public.admin_adjust_bird_xp(bigint, integer, bigint, text) to service_role;

commit;