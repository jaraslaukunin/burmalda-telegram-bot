begin;

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
    from public.profiles as pr
    where pr.telegram_id = p_telegram_id
      and pr.is_banned = false
    for update;

    if not found then
        return query
        select
            false,
            'player_not_found',
            0,
            0,
            0,
            0,
            0,
            0,
            null::timestamptz;
        return;
    end if;

    select dc.claimed_at
    into v_last_claim
    from public.daily_claims as dc
    where dc.telegram_id = p_telegram_id
    order by dc.claimed_at desc
    limit 1;

    if v_last_claim is not null
       and v_last_claim + interval '24 hours' > now() then
        v_next_claim_at := v_last_claim + interval '24 hours';

        select pr.acorns
        into v_balance
        from public.profiles as pr
        where pr.telegram_id = p_telegram_id;

        return query
        select
            false,
            'cooldown',
            0,
            0,
            v_balance,
            0,
            0,
            0,
            v_next_claim_at;
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
    from public.user_birds as ub
    join public.bird_definitions as bd
        on bd.id = ub.bird_definition_id
    where ub.telegram_id = p_telegram_id
      and ub.is_active = true
    for update of ub;

    if v_active_bird_id is null then
        return query
        select
            false,
            'active_bird_not_found',
            0,
            0,
            0,
            0,
            0,
            0,
            null::timestamptz;
        return;
    end if;

    if v_effect_type = 'daily_bonus' then
        v_bonus := floor(v_effect_value)::integer;
    end if;

    v_reward := v_reward + v_bonus;

    update public.profiles as pr
    set
        acorns = pr.acorns + v_reward,
        last_seen_at = now()
    where pr.telegram_id = p_telegram_id
    returning pr.acorns into v_balance;

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
        v_xp_result.result_level,
        v_xp_result.result_xp,
        v_xp_result.result_levels_gained,
        now() + interval '24 hours';
end;
$$;

revoke all on function public.claim_daily(bigint) from public;

grant execute on function public.claim_daily(bigint)
to service_role;

commit;