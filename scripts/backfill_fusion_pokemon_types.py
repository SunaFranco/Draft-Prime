"""Populate Supabase pool type columns used by the Pokémon fusion feature.

Run after applying the pokemon_fusion_types migration:
    python -m scripts.backfill_fusion_pokemon_types
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import ssl
import urllib.parse
import urllib.request

from backend import database
from backend.modes.subasta_pokemon import poke_api


def main() -> None:
    client = database.supabase_client
    if client is None:
        raise SystemExit("Configura SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY antes de ejecutar este script.")

    response = (
        client.table("pokemon_pools")
        .select("auction_type, pokemon_pool_cards(pokemon_name, type1, type2)")
        .execute()
    )
    names = {
        card["pokemon_name"]
        for pool in response.data or []
        if str(pool.get("auction_type", "")).strip().lower() in ("normal", "legendary")
        for card in pool.get("pokemon_pool_cards", []) or []
        if card.get("pokemon_name") and not card.get("type1")
    }
    legendary = client.table("legendarios").select("nombre, type1, type2").execute()
    names.update(
        row["nombre"] for row in legendary.data or []
        if row.get("nombre") and not row.get("type1")
    )
    names = sorted(names, key=str.casefold)
    print(f"Actualizando tipos de {len(names)} Pokémon...")

    def fetch_types(name: str):
        slug = poke_api.get_male_pokemon_slug(name)
        url = f"{poke_api.POKEAPI_BASE_URL}/{urllib.parse.quote(slug)}"
        request = urllib.request.Request(url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        types = [entry["type"]["name"].capitalize() for entry in data.get("types", [])]
        return name, types[0] if types else None, types[1] if len(types) > 1 else None

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(fetch_types, name): name for name in names}
        for future in as_completed(futures):
            name = futures[future]
            try:
                _, type1, type2 = future.result()
                if type1:
                    client.table("pokemon_pool_cards").update({"type1": type1, "type2": type2}).eq("pokemon_name", name).execute()
                    client.table("legendarios").update({"type1": type1, "type2": type2}).eq("nombre", name).execute()
            except Exception as error:
                print(f"No se pudieron actualizar tipos para {name}: {error}")

    print("Backfill de tipos finalizado.")


if __name__ == "__main__":
    main()
