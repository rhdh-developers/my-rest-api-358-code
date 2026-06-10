import re
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["pokeapi"])


def _id_from_url(url: str) -> Optional[int]:
    match = re.search(r"/(\d+)/?$", url)
    return int(match.group(1)) if match else None


def _english_text(entries: list[dict], field: str) -> Optional[str]:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get(field, "").replace("\n", " ").replace("\f", " ")
    return None


async def _get_json(client: httpx.AsyncClient, path: str) -> dict:
    try:
        response = await client.get(path)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found in PokeAPI") from exc
        raise HTTPException(status_code=502, detail="Error from PokeAPI") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not reach PokeAPI") from exc
    return response.json()


def _client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


class NamedResource(BaseModel):
    id: Optional[int] = None
    name: str


class PokemonListResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list[NamedResource]


class PokemonDetail(BaseModel):
    id: int
    name: str
    height: int
    weight: int
    base_experience: Optional[int] = None
    types: list[str]
    abilities: list[str]
    stats: dict[str, int]
    sprite: Optional[str] = None


class TypeDetail(BaseModel):
    id: int
    name: str
    pokemon: list[str]
    double_damage_from: list[str]
    double_damage_to: list[str]
    half_damage_from: list[str]
    half_damage_to: list[str]
    no_damage_from: list[str]
    no_damage_to: list[str]


class AbilityDetail(BaseModel):
    id: int
    name: str
    effect: Optional[str] = None
    pokemon: list[str]


class MoveDetail(BaseModel):
    id: int
    name: str
    power: Optional[int] = None
    pp: Optional[int] = None
    accuracy: Optional[int] = None
    damage_class: Optional[str] = None
    type: str
    effect: Optional[str] = None


class SpeciesDetail(BaseModel):
    id: int
    name: str
    generation: str
    is_legendary: bool
    is_mythical: bool
    habitat: Optional[str] = None
    flavor_text: Optional[str] = None
    evolution_chain_url: Optional[str] = None


@router.get("/pokemon", response_model=PokemonListResponse)
async def list_pokemon(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    client = _client(request)
    data = await _get_json(client, f"/pokemon?limit={limit}&offset={offset}")
    results = [
        NamedResource(id=_id_from_url(item["url"]), name=item["name"])
        for item in data["results"]
    ]
    return PokemonListResponse(
        count=data["count"], next=data["next"], previous=data["previous"], results=results
    )


@router.get("/pokemon/{name_or_id}", response_model=PokemonDetail)
async def get_pokemon(name_or_id: str, request: Request):
    client = _client(request)
    data = await _get_json(client, f"/pokemon/{name_or_id.lower()}")
    return PokemonDetail(
        id=data["id"],
        name=data["name"],
        height=data["height"],
        weight=data["weight"],
        base_experience=data.get("base_experience"),
        types=[t["type"]["name"] for t in data["types"]],
        abilities=[a["ability"]["name"] for a in data["abilities"]],
        stats={s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
        sprite=data.get("sprites", {}).get("front_default"),
    )


@router.get("/pokemon-species/{name_or_id}", response_model=SpeciesDetail)
async def get_pokemon_species(name_or_id: str, request: Request):
    client = _client(request)
    data = await _get_json(client, f"/pokemon-species/{name_or_id.lower()}")
    return SpeciesDetail(
        id=data["id"],
        name=data["name"],
        generation=data["generation"]["name"],
        is_legendary=data["is_legendary"],
        is_mythical=data["is_mythical"],
        habitat=(data.get("habitat") or {}).get("name"),
        flavor_text=_english_text(data.get("flavor_text_entries", []), "flavor_text"),
        evolution_chain_url=(data.get("evolution_chain") or {}).get("url"),
    )


@router.get("/type/{name_or_id}", response_model=TypeDetail)
async def get_type(name_or_id: str, request: Request):
    client = _client(request)
    data = await _get_json(client, f"/type/{name_or_id.lower()}")
    relations = data["damage_relations"]
    return TypeDetail(
        id=data["id"],
        name=data["name"],
        pokemon=[p["pokemon"]["name"] for p in data["pokemon"]],
        double_damage_from=[t["name"] for t in relations["double_damage_from"]],
        double_damage_to=[t["name"] for t in relations["double_damage_to"]],
        half_damage_from=[t["name"] for t in relations["half_damage_from"]],
        half_damage_to=[t["name"] for t in relations["half_damage_to"]],
        no_damage_from=[t["name"] for t in relations["no_damage_from"]],
        no_damage_to=[t["name"] for t in relations["no_damage_to"]],
    )


@router.get("/ability/{name_or_id}", response_model=AbilityDetail)
async def get_ability(name_or_id: str, request: Request):
    client = _client(request)
    data = await _get_json(client, f"/ability/{name_or_id.lower()}")
    return AbilityDetail(
        id=data["id"],
        name=data["name"],
        effect=_english_text(data.get("effect_entries", []), "effect"),
        pokemon=[p["pokemon"]["name"] for p in data["pokemon"]],
    )


@router.get("/move/{name_or_id}", response_model=MoveDetail)
async def get_move(name_or_id: str, request: Request):
    client = _client(request)
    data = await _get_json(client, f"/move/{name_or_id.lower()}")
    return MoveDetail(
        id=data["id"],
        name=data["name"],
        power=data.get("power"),
        pp=data.get("pp"),
        accuracy=data.get("accuracy"),
        damage_class=(data.get("damage_class") or {}).get("name"),
        type=data["type"]["name"],
        effect=_english_text(data.get("effect_entries", []), "effect"),
    )
