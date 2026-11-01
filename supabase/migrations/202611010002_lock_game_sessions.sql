-- The backend accesses room state with the server-only service-role key.
-- Browser clients must never read or mutate private room state directly.
begin;

alter table public.game_sessions enable row level security;
revoke all on table public.game_sessions from anon, authenticated;
grant all on table public.game_sessions to service_role;

commit;
