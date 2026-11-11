-- Migración: Crear tabla pve_battles para persistencia de partidas PVE
CREATE TABLE IF NOT EXISTS public.pve_battles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    preset_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'won', 'lost', 'surrendered'
    turn_number INTEGER NOT NULL DEFAULT 1,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índices para optimizar consultas por usuario y estado
CREATE INDEX IF NOT EXISTS idx_pve_battles_user_id ON public.pve_battles(user_id);
CREATE INDEX IF NOT EXISTS idx_pve_battles_status ON public.pve_battles(status);

-- RLS (Row Level Security)
ALTER TABLE public.pve_battles ENABLE ROW LEVEL SECURITY;

-- Políticas permisivas para lectura y creación por usuarios autenticados o anónimos
CREATE POLICY "Permitir lectura de batallas propias o anónimas"
    ON public.pve_battles FOR SELECT
    USING (true);

CREATE POLICY "Permitir inserción de batallas"
    ON public.pve_battles FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Permitir actualización de batallas"
    ON public.pve_battles FOR UPDATE
    USING (true);
