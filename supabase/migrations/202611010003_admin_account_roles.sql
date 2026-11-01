-- Add a global account role selectable by an existing administrator.
-- The first administrator remains protected by the backend email allowlist.
begin;

alter table public.profiles
    add column if not exists is_admin boolean not null default false;

create or replace function private.create_profile_for_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (
        id, username, display_name, avatar_key, is_admin, must_change_password
    )
    values (
        new.id,
        coalesce(nullif(new.raw_user_meta_data ->> 'username', ''), split_part(new.email, '@', 1)),
        coalesce(nullif(new.raw_user_meta_data ->> 'display_name', ''), split_part(new.email, '@', 1)),
        coalesce(nullif(new.raw_user_meta_data ->> 'avatar_key', ''), 'avatar_01'),
        coalesce((new.raw_user_meta_data ->> 'is_admin')::boolean, false),
        coalesce((new.raw_user_meta_data ->> 'must_change_password')::boolean, true)
    )
    on conflict (id) do nothing;
    return new;
end;
$$;

revoke all on function private.create_profile_for_auth_user() from public, anon, authenticated;

commit;
