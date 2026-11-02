alter table public.user_trophies
    add column if not exists pokemon_ids integer[] not null default '{}';
