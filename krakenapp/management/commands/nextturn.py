from dataclasses import dataclass, asdict
import datetime as dt
from random import randint
from itertools import chain

from django.core.management.base import BaseCommand
from django.db.models import F
from django.db.transaction import atomic
from django.utils.timezone import now

from krakenapp.enums import COSTS
from krakenapp.models import Action, Player, Territory


@dataclass
class Roll:
    roll: int = 0
    fort: bool = False
    wins: bool = False

    def __lt__(self, other):
        return (self.roll, self.fort, self.wins) < (other.roll, other.fort, other.wins)


class Command(BaseCommand):
    help = "Exécute les actions du jour"

    def add_arguments(self, parser):
        parser.add_argument('--debug', action='store_true', help="Ajoute les nouvelles revendications")

    @atomic
    def handle(self, *args, debug=False, **options):
        if debug:
            for date in Action.objects.values_list('date', flat=True).order_by('date'):
                Action.objects.filter(date=date).update(date=date - dt.timedelta(days=1))
        previous_date = None
        actions = Action.objects.select_related('player').filter(done=False, date__lt=now().date())
        if not actions.exists():
            self.update_players()
        for action in actions.order_by('-type', '-date', 'creation_date'):
            if action.date != previous_date:
                self.update_players(action.date)
            previous_date = action.date
            if action.player_id != action.source.player_id or action.player.auto:
                action.done = True
                action.save()
                continue
            if action.type == 'A':
                reason = f"Attaque #{action.id} du {action.date:%x}"
                action.defender = action.target.player
                attacker_troops = int(min(action.amount, action.source.troops))
                if not attacker_troops:
                    action.done = True
                    action.save()
                is_auto = bool(action.defender and action.defender.auto)
                is_capital = bool(action.defender and action.defender.capital == action.target)
                if is_auto:
                    troops = min(
                        action.defender.reserve,
                        action.target.troops,
                        attacker_troops - action.target.troops)
                    if troops:
                        auto_reason = f"Renforcement automatique à cause de l'attaque #{action.id} du {action.date:%x}"
                        action.target.troops = troops
                        action.target.save(update_fields=('troops', ), _reason=auto_reason)
                        action.defender.reserve -= troops
                        action.defender.save(update_fields=('reserve', ), _reason=auto_reason)
                action.details.update(
                    auto=is_auto,
                    capital=is_capital,
                    conquered=False,
                    attacker=dict(
                        troops=action.source.troops,
                        sent=attacker_troops),
                    defender=dict(
                        troops=action.target.troops,
                        forts=action.target.forts))
                attacker_rolls = sorted(
                    (Roll(roll=randint(1, 6), fort=False) for _ in range(attacker_troops)),
                    reverse=True)
                defender_rolls = sorted(chain(
                    (Roll(roll=randint(1, 6), fort=False) for _ in range(action.target.troops)),
                    (Roll(roll=randint(1, 6), fort=True) for _ in range(action.target.forts))),
                    reverse=True)
                attacker_losses, defender_losses = 0, 0
                for attacker_roll, defender_roll in zip(attacker_rolls, defender_rolls):
                    if attacker_roll.roll > defender_roll.roll:
                        attacker_roll.wins = True
                        if defender_roll.fort:
                            continue
                        action.target.troops -= 1
                        defender_losses += 1
                    else:
                        defender_roll.wins = True
                        action.source.troops -= 1
                        attacker_losses += 1
                attacker_remains, defender_remains = action.amount - attacker_losses, action.target.troops
                action.details['attacker'].update(
                    remains=attacker_remains,
                    losses=attacker_losses)
                action.details['defender'].update(
                    remains=defender_remains,
                    losses=defender_losses)
                if attacker_remains and not defender_remains:
                    attacker_remains = min(action.target.limit, attacker_remains)
                    action.source.troops -= attacker_remains
                    action.target.troops = attacker_remains
                    action.target.player = action.player
                    if is_capital:
                        action.defender.capital = None
                        action.defender.save(
                            update_fields=('capital', ),
                            _reason=f"Perte de la capitale lors de l'{reason.lower()}")
                    action.details.update(conquered=True)
                field_length = min(len(attacker_rolls), len(defender_rolls))
                action.details.update(
                    attacker_rolls=[asdict(roll) for roll in attacker_rolls[:field_length]],
                    defender_rolls=[asdict(roll) for roll in defender_rolls[:field_length]])
                if action.source.modified:
                    action.source.save(_reason=reason)
                if action.target.modified:
                    action.target.save(_reason=reason)
            elif action.type == 'M':
                reason = f"Manoeuvre #{action.id} du {action.date:%x}"
                max_troops = min(action.target.limit - action.target.troops, action.amount)
                action.source.troops -= max_troops
                action.source.save(update_fields=('troops', ), _reason=reason)
                action.target.troops += max_troops
                action.target.save(update_fields=('troops', ), _reason=reason)
                action.details.update(troops=max_troops)
            action.done = True
            action.save()

    def update_players(self, date=None):
        date = date or now().date()
        reason = f"Taxes et conscription du {date:%x}"
        players = Player.objects.with_rates()
        for player in players:
            if player.auto:
                get_taxes_cost, get_prods_cost = COSTS['taxes'], COSTS['prods']
                for territory in Territory.objects.filter(player=player).order_by(
                        F('claim__reason').asc(nulls_last=True), 'taxes', 'prods'):
                    if not player.capital:
                        player.capital = territory
                    taxes_cost, prods_cost = get_taxes_cost(territory.taxes), get_prods_cost(territory.prods)
                    if territory.taxes > territory.prods and player.money >= prods_cost:
                        territory.prods += 1
                        player.money -= prods_cost
                    elif player.money >= taxes_cost:
                        territory.taxes += 1
                        player.money -= taxes_cost
                    if territory.modified:
                        territory.save(_reason="Amélioration automatique")
            player.money += player.taxes
            player.reserve += player.prods
            if player.modified:
                player.save(update_fields=('capital', 'money', 'reserve'), _reason=reason)
        for territory in Territory.objects.filter(player__isnull=True, prods__gt=0):
            territory.troops = min(territory.troops + (territory.prods or territory.taxes), territory.limit)
            if territory.modified:
                territory.save(update_fields=('troops', ), _ignore_log=True)
