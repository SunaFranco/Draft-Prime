import json
import re
import sys
from collections import Counter
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
transcript_full = Path(r"C:\Users\garma\.gemini\antigravity\brain\39007d73-a57a-48d9-8d7a-6afeea59618f\.system_generated\logs\transcript_full.jsonl")

card_text = ""
if transcript_full.exists():
    with open(transcript_full, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("type") == "USER_INPUT":
                    c = data.get("content", "")
                    if "[Aitsu]" in c:
                        card_text = c
                        break
            except Exception:
                continue

matches = re.findall(r"\[(.*?)\]\(https://ygoprodeck\.com/card/\?search=\d+\)", card_text)
if not matches:
    print("Error: No se pudieron extraer cartas del historial.")
    sys.exit(1)

counts = Counter(matches)

# Generar archivo SQL
sql_lines = [
    "-- =============================================================================",
    "-- MIGRATION / SCRIPT: Insertar Cube 'GX RAW' y sus cartas en Supabase",
    f"-- Total cartas: {len(matches)} ({len(counts)} únicas)",
    "-- =============================================================================",
    "",
    "DO $$",
    "DECLARE",
    "    v_cube_id uuid;",
    "BEGIN",
    "    -- 1. Obtener ID del cubo si ya existe, o insertar uno nuevo",
    "    SELECT id INTO v_cube_id FROM public.cubes WHERE title = 'GX RAW' LIMIT 1;",
    "",
    "    IF v_cube_id IS NULL THEN",
    "        INSERT INTO public.cubes (title, description, author, is_public)",
    "        VALUES ('GX RAW', 'GX RAW Cube', 'System', true)",
    "        RETURNING id INTO v_cube_id;",
    "    ELSE",
    "        -- Si ya existía, limpiar sus cartas anteriores para evitar duplicados",
    "        DELETE FROM public.cube_cards WHERE cube_id = v_cube_id;",
    "    END IF;",
    "",
    "    -- 2. Insertar las cartas con sus cantidades (qty)",
    "    INSERT INTO public.cube_cards (cube_id, card_name, qty) VALUES"
]

values_list = []
for name, qty in sorted(counts.items()):
    escaped_name = name.replace("'", "''")
    values_list.append(f"        (v_cube_id, '{escaped_name}', {qty})")

sql_lines.append(",\n".join(values_list) + ";")
sql_lines.extend([
    "",
    "    RAISE NOTICE 'Cubo GX RAW creado/actualizado con éxito. ID: %', v_cube_id;",
    "END $$;"
])

output_sql = "\n".join(sql_lines)
output_path = ROOT_DIR / "supabase" / "manual" / "20261113_insert_gx_raw_cube.sql"
output_path.write_text(output_sql, encoding="utf-8")
print(f"[OK] Archivo SQL generado en {output_path} ({len(values_list)} cartas únicas, {len(matches)} total).")

# Opción para subir directamente a Supabase
if "--upload" in sys.argv:
    try:
        import backend.database as db
        if not db.supabase_client:
            print("[ERROR] No se pudo inicializar supabase_client.")
            sys.exit(1)

        print("[INFO] Verificando si 'GX RAW' ya existe en Supabase...")
        res = db.supabase_client.table("cubes").select("id").eq("title", "GX RAW").execute()
        cube_id = None
        if res.data and len(res.data) > 0:
            cube_id = res.data[0]["id"]
            print(f"[INFO] Cubo encontrado con ID {cube_id}. Limpiando cartas antiguas...")
            db.supabase_client.table("cube_cards").delete().eq("cube_id", cube_id).execute()
        else:
            print("[INFO] Creando nuevo cubo 'GX RAW'...")
            c_res = db.supabase_client.table("cubes").insert({
                "title": "GX RAW",
                "description": "GX RAW Cube",
                "author": "System",
                "is_public": True
            }).execute()
            cube_id = c_res.data[0]["id"]
            print(f"[OK] Cubo creado con ID: {cube_id}")

        print(f"[INFO] Insertando {len(counts)} filas en cube_cards...")
        items_to_insert = [
            {"cube_id": cube_id, "card_name": name, "qty": qty}
            for name, qty in counts.items()
        ]
        batch_size = 200
        for i in range(0, len(items_to_insert), batch_size):
            batch = items_to_insert[i:i + batch_size]
            db.supabase_client.table("cube_cards").insert(batch).execute()
            print(f"  -> Insertadas cartas {i+1} a {min(i+len(batch), len(items_to_insert))}")

        print("[SUCCESS] ¡Cubo GX RAW insertado exitosamente en Supabase!")
    except Exception as e:
        print(f"[ERROR] Error al subir a Supabase: {e}")
