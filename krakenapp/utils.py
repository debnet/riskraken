import json

from django.urls import reverse
from django.utils.html import escape

from krakenapp.enums import NEIGHBOURS
from krakenapp.models import Claim, Territory


def get_zones():
    with open('world.geojson', 'r', encoding='utf-8') as file:
        world = json.load(file)
    return world, {zone['properties']['code']: zone for zone in world['features']}


def get_claims():
    world, zones = get_zones()
    claims, claimed = {}, {}
    for claim in Claim.objects.select_related('player').get_ordered():
        claimed.setdefault(claim.zone, []).append(escape(str(claim.player)))
        if len(claimed[claim.zone]) > 1:
            continue
        claims.setdefault(claim.player, []).append(zones[claim.zone])
    for code, zone in zones.items():
        url = reverse('front:claim', args=(code, ))
        zone['properties'].update(url=f'<a href="{url}">Revendiquer</a>')
        if code not in claimed:
            claims.setdefault(None, []).append(zone)
        players = "---"
        if code in claimed:
            claimants = claimed.get(code, [])
            if len(claimants) > 1:
                players = '<ul class="m-0 pl-3">' + ''.join(f'<li>{claimant}</li>' for claimant in claimants) + '</ul>'
            else:
                players = claimants[0]
        zone['properties'].update(claims=players)
    claims = {player: {"type": "FeatureCollection", "features": zones} for player, zones in claims.items()}
    return claims, world


def get_territories(player):
    world, zones = get_zones()
    territories, owned = {}, set()
    queryset = Territory.objects.select_related('player')
    for territory in queryset:
        zone = zones[territory.zone]
        territories.setdefault(territory.player, []).append(zone)
        zone['properties'].update(
            url='---',
            image=(
                f'<img src="{territory.player.image.url}" style="max-width: 100px; max-height: 50px;">'
                if territory.player and territory.player.image else ''),
            troops=f'{territory.troops} / {territory.limit}',
            forts=territory.forts,
            taxes=territory.taxes,
            prods=territory.prods,
            owner=escape(str(territory.player or '---')))
        if territory.player == player:
            owned.add(territory.zone)
            url = reverse('front:move', args=(territory.zone, ))
            zone['properties'].update(url=f'<a href="{url}">Déplacer</a>')
    for zone in owned:
        for neighbour in NEIGHBOURS[zone]:
            if neighbour in owned:
                continue
            url = reverse('front:attack', args=(neighbour, ))
            zones[neighbour]['properties'].update(url=f'<a href="{url}">Attaquer</a>')
    territories = {player: {"type": "FeatureCollection", "features": zones} for player, zones in territories.items()}
    return territories, world
