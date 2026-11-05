-- Persistent type metadata used to build DNA Splicers fusion odds.
alter table if exists public.pokemon_pool_cards
  add column if not exists type1 text,
  add column if not exists type2 text;

alter table if exists public.legendarios
  add column if not exists type1 text,
  add column if not exists type2 text;

create index if not exists pokemon_pool_cards_fusion_types_idx
  on public.pokemon_pool_cards (type1, type2);

create index if not exists legendarios_fusion_types_idx
  on public.legendarios (type1, type2);
