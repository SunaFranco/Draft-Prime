-- Store PokéAPI sprite IDs that appear inline beside a profile trophy.
begin;

alter table public.trophies
    add column if not exists pokemon_ids integer[] not null default '{}';

commit;
