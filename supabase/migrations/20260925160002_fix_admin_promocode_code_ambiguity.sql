begin;

drop function if exists public.admin_create_promocode(
    bigint,
    text,
    integer,
    integer,
    integer,
    integer,
    timestamptz
);

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
    promo_code text,
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
    v_existing_id bigint;
begin
    perform public.assert_burmalda_admin(p_admin_telegram_id);

    v_code := upper(trim(p_code));

    -- Русские/английские буквы, цифры, дефис и нижнее подчёркивание.
    if v_code !~ '^[A-ZА-ЯЁ0-9_-]{3,32}$' then
        raise exception
            'Промокод: 3–32 символа. Разрешены русские/английские буквы, цифры, _ и -';
    end if;

    if coalesce(p_reward_acorns, 0) < 0
       or coalesce(p_reward_xp, 0) < 0
       or coalesce(p_reward_nests, 0) < 0 then
        raise exception 'Награды не могут быть отрицательными';
    end if;

    if coalesce(p_reward_acorns, 0) = 0
       and coalesce(p_reward_xp, 0) = 0
       and coalesce(p_reward_nests, 0) = 0 then
        raise exception 'В промокоде должна быть хотя бы одна награда';
    end if;

    if p_max_uses is not null and p_max_uses <= 0 then
        raise exception 'Лимит активаций должен быть больше нуля';
    end if;

    if p_expires_at is not null and p_expires_at <= now() then
        raise exception 'Дата окончания должна быть в будущем';
    end if;

    select pc.id
    into v_existing_id
    from public.promocodes as pc
    where pc.code = v_code
    for update;

    if v_existing_id is null then
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
        );
    else
        update public.promocodes as pc
        set
            reward_acorns = coalesce(p_reward_acorns, 0),
            reward_xp = coalesce(p_reward_xp, 0),
            reward_nests = coalesce(p_reward_nests, 0),
            max_uses = p_max_uses,
            expires_at = p_expires_at,
            is_active = true
        where pc.id = v_existing_id;
    end if;

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

revoke all on function public.admin_create_promocode(
    bigint,
    text,
    integer,
    integer,
    integer,
    integer,
    timestamptz
) from public;

grant execute on function public.admin_create_promocode(
    bigint,
    text,
    integer,
    integer,
    integer,
    integer,
    timestamptz
) to service_role;

commit;