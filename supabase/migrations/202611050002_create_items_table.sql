-- Migración: Tabla de items y asignación de zonas de farmeo
create table if not exists public.items (
    id serial primary key,
    name text not null unique,
    zone text null,
    category text not null,
    created_at timestamptz default now()
);

create index if not exists idx_items_zone on public.items (zone);

-- Población inicial de items por zona
insert into public.items (name, zone, category)
values
    -- Minas (Afinidad: Tierra, Roca, Acero)
    ('Fire Stone', 'minas', 'evolution_stone'),
    ('Water Stone', 'minas', 'evolution_stone'),
    ('Thunder Stone', 'minas', 'evolution_stone'),
    ('Leaf Stone', 'minas', 'evolution_stone'),
    ('Moon Stone', 'minas', 'evolution_stone'),
    ('Sun Stone', 'minas', 'evolution_stone'),
    ('Shiny Stone', 'minas', 'evolution_stone'),
    ('Dusk Stone', 'minas', 'evolution_stone'),
    ('Dawn Stone', 'minas', 'evolution_stone'),
    ('Ice Stone', 'minas', 'evolution_stone'),
    ('Hard Stone', 'minas', 'held_item'),
    ('Soft Sand', 'minas', 'held_item'),

    -- Bosques (Afinidad: Planta, Bicho, Hada)
    ('Sitrus Berry', 'bosques', 'berry'),
    ('Lum Berry', 'bosques', 'berry'),
    ('Leftovers', 'bosques', 'held_item'),
    ('Miracle Seed', 'bosques', 'held_item'),

    -- Ciudad (Afinidad: Normal, Eléctrico, Fuego)
    ('DNA Splicers', 'ciudad', 'special'),
    ('Capsula Habilidad', 'ciudad', 'special'),
    ('MT Flamethrower', 'ciudad', 'tm'),
    ('MT Thunderbolt', 'ciudad', 'tm'),
    ('MT Ice Beam', 'ciudad', 'tm'),
    ('MT Earthquake', 'ciudad', 'tm'),
    ('MT Energy Ball', 'ciudad', 'tm'),
    ('MT Shadow Ball', 'ciudad', 'tm'),
    ('MT Close Combat', 'ciudad', 'tm'),

    -- Templo (Afinidad: Psíquico, Fantasma, Dragón)
    ('Flame Plate', 'templo', 'plate'),
    ('Splash Plate', 'templo', 'plate'),
    ('Zap Plate', 'templo', 'plate'),
    ('Meadow Plate', 'templo', 'plate'),
    ('Icicle Plate', 'templo', 'plate'),
    ('Fist Plate', 'templo', 'plate'),
    ('Toxic Plate', 'templo', 'plate'),
    ('Earth Plate', 'templo', 'plate'),
    ('Sky Plate', 'templo', 'plate'),
    ('Mind Plate', 'templo', 'plate'),
    ('Insect Plate', 'templo', 'plate'),
    ('Stone Plate', 'templo', 'plate'),
    ('Spooky Plate', 'templo', 'plate'),
    ('Draco Plate', 'templo', 'plate'),
    ('Dread Plate', 'templo', 'plate'),
    ('Iron Plate', 'templo', 'plate'),
    ('Pixie Plate', 'templo', 'plate'),

    -- Montañas Nevadas (Afinidad: Agua, Volador, Hielo)
    ('Damp Rock', 'montanas_nevadas', 'weather'),
    ('Heat Rock', 'montanas_nevadas', 'weather'),
    ('Icy Rock', 'montanas_nevadas', 'weather'),
    ('Smooth Rock', 'montanas_nevadas', 'weather'),
    ('Heavy-Duty Boots', 'montanas_nevadas', 'held_item'),
    ('Safety Goggles', 'montanas_nevadas', 'held_item'),
    ('Never-Melt Ice', 'montanas_nevadas', 'held_item')
on conflict (name) do update set
    zone = excluded.zone,
    category = excluded.category;
