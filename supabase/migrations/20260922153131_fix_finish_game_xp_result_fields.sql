begin;

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

    select exists (
        select 1
        from public.game_catalog as gc
        where gc.code = p_game_code
          and gc.is_enabled = true
    )
    into v_game_exists;

    if not v_game_exists then
        return query
        select false, 'game_not_available', 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    select pr.acorns
    into v_balance_before
    from public.profiles as pr
    where pr.telegram_id = p_telegram_id
      and pr.is_banned = false
    for update;

    if not found then
        return query
        select false, 'player_not_found', 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    if v_balance_before < p_bet then
        return query
        select false,
               'not_enough_acorns',
               v_balance_before,
               v_balance_before,
               0, 0, 0, 0, 0, '';
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
    from public.user_birds as ub
    join public.bird_definitions as bd
        on bd.id = ub.bird_definition_id
    where ub.telegram_id = p_telegram_id
      and ub.is_active = true
    for update of ub;

    if v_active_bird_id is null then
        return query
        select false, 'active_bird_not_found', 0, 0, 0, 0, 0, 0, 0, '';
        return;
    end if;

    v_xp_base := 5 + least(p_bet, 50);

    if v_effect_type = 'xp_bonus' then
        v_xp_multiplier := v_xp_multiplier + (v_effect_value / 100);
    end if;

    v_xp_multiplier := v_xp_multiplier
        + (least(greatest(v_bird_level - 1, 0), 20) / 100.0);

    v_xp_awarded := floor(v_xp_base * v_xp_multiplier)::integer;

    update public.profiles as pr
    set
        acorns = pr.acorns - p_bet + p_payout,
        games_played = pr.games_played + 1,
        last_seen_at = now()
    where pr.telegram_id = p_telegram_id
    returning pr.acorns into v_balance_after;

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
        v_xp_result.result_level,
        v_xp_result.result_xp,
        v_xp_result.result_levels_gained,
        v_xp_result.result_tier;
end;
$$;

revoke all on function public.finish_game(
    bigint,
    text,
    integer,
    integer,
    jsonb
) from public;

grant execute on function public.finish_game(
    bigint,
    text,
    integer,
    integer,
    jsonb
) to service_role;

commit;