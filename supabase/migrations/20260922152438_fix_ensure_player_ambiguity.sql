begin;

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

    select bd.id
    into v_bird_definition_id
    from public.bird_definitions as bd
    where bd.is_starter = true
      and bd.is_enabled = true
    limit 1;

    if v_bird_definition_id is null then
        raise exception 'Starter bird is not configured';
    end if;

    insert into public.profiles as p (
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
    returning (xmax = 0), p.acorns
    into v_is_new, v_acorns;

    insert into public.user_birds as ub (
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
    from public.user_birds as ub
    join public.bird_definitions as bd
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

revoke all on function public.ensure_player(bigint, text, text, text) from public;
grant execute on function public.ensure_player(bigint, text, text, text)
to service_role;

commit;