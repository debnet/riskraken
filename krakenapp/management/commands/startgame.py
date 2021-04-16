from random import randint
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from krakenapp.enums import ZONES
from krakenapp.models import Action, Claim, Player, Territory


class Command(BaseCommand):
    help = "Démarre une nouvelle partie"

    @atomic
    def handle(self, *args, **options):
        Action.objects.all().delete()
        Territory.objects.all().delete()
        Player.objects.update(reserve=20, money=10)
        claimed = set()
        territories = []
        for claim in Claim.objects.get_ordered():
            if claim.zone in claimed:
                continue
            claimed.add(claim.zone)
            territories.append(Territory(
                zone=claim.zone,
                player_id=claim.player_id,
                owner_id=claim.player_id,
                troops=0,
                limit=10))
        for zone, name in ZONES:
            if zone in claimed:
                continue
            troops = randint(3, 10)
            territories.append(Territory(
                zone=zone,
                troops=troops,
                limit=10))
        territories = sorted(territories, key=lambda t: t.zone)
        Territory.objects.bulk_create(territories)
