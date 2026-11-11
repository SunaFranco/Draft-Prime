-- Migración: Crear tabla pokemon_moves para almacenar progresivamente los movimientos y sus datos de combate
CREATE TABLE IF NOT EXISTS public.pokemon_moves (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'Normal',
    category TEXT NOT NULL DEFAULT 'physical', -- 'physical', 'special', 'status'
    base_power INTEGER NOT NULL DEFAULT 0,
    accuracy REAL NOT NULL DEFAULT 1.0,
    priority INTEGER NOT NULL DEFAULT 0,
    pp INTEGER NOT NULL DEFAULT 15,
    drain_percent REAL NOT NULL DEFAULT 0.0,
    recoil_percent REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índice por tipo para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_pokemon_moves_type ON public.pokemon_moves(type);

-- RLS (Row Level Security)
ALTER TABLE public.pokemon_moves ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura pública de movimientos" ON public.pokemon_moves;
CREATE POLICY "Permitir lectura pública de movimientos"
    ON public.pokemon_moves FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Permitir inserción de movimientos" ON public.pokemon_moves;
CREATE POLICY "Permitir inserción de movimientos"
    ON public.pokemon_moves FOR INSERT
    WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir actualización de movimientos" ON public.pokemon_moves;
CREATE POLICY "Permitir actualización de movimientos"
    ON public.pokemon_moves FOR UPDATE
    USING (true);
