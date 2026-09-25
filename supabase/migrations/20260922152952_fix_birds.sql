begin;

drop function if exists public.add_bird_xp(bigint, integer);

create function public.add_bird_xp(
    p_user_bird_id bigint,
    p_xp integer
)
returns table (
    result_level integer,
    result_xp integer,
    result_total_xp bigint,
    result_levels_gained integer,
    result_tier text
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

    select
        ub.level,
        ub.xp,
        ub.total_xp
    into
        v_level,
        v_xp,
        v_total_xp
    from public.user_birds as ub
    where ub.id = p_user_bird_id
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

    update public.user_birds as ub
    set
        level = v_level,
        xp = v_xp,
        total_xp = v_total_xp
    where ub.id = p_user_bird_id;

    return query
    select
        v_level,
        v_xp,
        v_total_xp,
        v_levels_gained,
        public.bird_tier(v_level);
end;
$$;

revoke all on function public.add_bird_xp(bigint, integer) from public;

grant execute on function public.add_bird_xp(bigint, integer)
to service_role;

commit;