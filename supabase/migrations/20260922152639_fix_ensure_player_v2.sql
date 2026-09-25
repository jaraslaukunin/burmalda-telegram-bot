begin;

drop function if exists public.ensure_player(bigint, text, text, text);

create function public.ensure_player(
    p_telegram_id bigint,
    p_username text default null,
    p_first_name text default null,
    p_language text default 'ru'
)
returns table (
    player_is_new boolean,
    player_id bigint,
    player_acorns integer,
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
    v_starter_definition_id smallint;
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
    into v_starter_definition_id
    from public.bird_definitions as bd
    where bd.is_starter = true
      and bd.is_enabled = true
    limit 1;

    if v_starter_definition_id is null then
        raise exception 'Starter bird is not configured';
    end if;

    if not exists (
        select 1
        from public.profiles as pr
        where pr.telegram_id = p_telegram_id
    ) then
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
        );

        v_is_new := true;
    else
        update public.profiles as pr
        set
            username = nullif(trim(p_username), ''),
            first_name = coalesce(
                nullif(trim(p_first_name), ''),
                pr.first_name
            ),
            last_seen_at = now()
        where pr.telegram_id = p_telegram_id;
    end if;

    if not exists (
        select 1
        from public.user_birds as ub
        where ub.telegram_id = p_telegram_id
          and ub.bird_definition_id = v_starter_definition_id
    ) then
        insert into public.user_birds (
            telegram_id,
            bird_definition_id,
            is_active,
            obtained_from
        )
        values (
            p_telegram_id,
            v_starter_definition_id,
            true,
            'starter'
        );
    end if;

    -- Если стартовая птица есть, но ни одной активной нет,
    -- делаем её активной.
    if not exists (
        select 1
        from public.user_birds as ub
        where ub.telegram_id = p_telegram_id
          and ub.is_active = true
    ) then
        update public.user_birds as ub
        set is_active = true
        where ub.telegram_id = p_telegram_id
          and ub.bird_definition_id = v_starter_definition_id;
    end if;

    select
        pr.acorns,
        ub.id,
        bd.code,
        case
            when p_language = 'en' then bd.title_en
            else bd.title_ru
        end,
        ub.level,
        ub.xp
    into
        v_acorns,
        v_bird_id,
        v_bird_code,
        v_bird_title,
        v_bird_level,
        v_bird_xp
    from public.profiles as pr
    join public.user_birds as ub
        on ub.telegram_id = pr.telegram_id
       and ub.is_active = true
    join public.bird_definitions as bd
        on bd.id = ub.bird_definition_id
    where pr.telegram_id = p_telegram_id
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

revoke all on function public.ensure_player(bigint, text, text, text)
from public;

grant execute on function public.ensure_player(bigint, text, text, text)
to service_role;

commit;