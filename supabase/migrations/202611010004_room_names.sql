-- Persist display names for rooms, including their natural-finish history.
begin;

alter table public.user_room_history
    add column if not exists room_name text not null default 'Sala anterior';

commit;
