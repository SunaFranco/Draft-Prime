begin;

alter table public.trophies
    add column if not exists pokemon_ids integer[] not null default '{}';

insert into public.trophies (id, title, description, icon_key, pokemon_ids)
values (
    'prime_subasta_1',
    'PRIME SUBASTA 1',
    'Trofeo PRIME SUBASTA 1',
    '🏅',
    array[493, 142, 452, 904, 28, 330]
)
on conflict (id) do update set
    title = excluded.title,
    description = excluded.description,
    icon_key = excluded.icon_key,
    pokemon_ids = excluded.pokemon_ids;

do $$
declare
    target_user_id uuid;
begin
    select id into target_user_id
    from public.profiles
    where lower(username) = lower('Nesshinst');

    if target_user_id is null then
        raise exception 'No se encontró el perfil Nesshinst.';
    end if;

    insert into public.user_trophies (user_id, trophy_id, source_session_id)
    select target_user_id, 'prime_subasta_1', null
    where not exists (
        select 1
        from public.user_trophies
        where user_id = target_user_id
          and trophy_id = 'prime_subasta_1'
    );
end;
$$;

commit;
