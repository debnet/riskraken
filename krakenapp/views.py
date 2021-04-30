import datetime
import folium

from common.utils import render_to
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import redirect, get_object_or_404
from django.utils.html import escape
from django.views.decorators.cache import cache_page, never_cache

from krakenapp.enums import COSTS, NEIGHBOURS, ZONES
from krakenapp.forms import ActionForm, ClaimForm, UserEditForm, UserRegisterForm
from krakenapp.models import Action, Claim, Player, Territory
from krakenapp.utils import get_claims, get_territories, get_zones

MAPS_CONFIG = dict(
    location=(47, 3), zoom_start=6, min_zoom=6,
    tiles="CartoDBDark_Matter", prefer_canvas=True, disable_3d=False,
    # max_bounds=True, min_lat=41, max_lat=52, min_lng=-4, max_lng=10
)


@never_cache
@login_required
@render_to('portal.html')
def portal(request):
    player_id = request.user.id
    if request.user.is_superuser and 'user' in request.GET:
        player_id = request.GET['user']
    player = Player.objects.with_rates().get(id=player_id)
    claims = player.claims.with_count().order_by('reason')
    territories = player.territories.order_by('zone')
    actions = Action.objects.select_related('player', 'source', 'target', 'defender').filter(
        Q(player=player) | Q(defender=player, done=True), date__gte=datetime.date.today() - datetime.timedelta(days=5)
    ).order_by('-date', '-type')
    form = UserEditForm(instance=player)
    if request.method == 'POST':
        allow_redirect = True
        if 'improve' in request.POST:
            try:
                update, territory = request.POST.get('improve').split('_')
                territory = territories.filter(id=territory).first()
                if not territory:
                    raise AssertionError("ce territoire ne vous appartient pas")
                level = getattr(territory, update, 0)
                cost = COSTS.get(update)(level)
                if player.money < cost:
                    raise AssertionError("vous n'avez pas assez d'argent pour les travaux")
                setattr(territory, update, level + 1)
                upgrades = territory.extra.setdefault('upgrades', [])
                upgrades.append(dict(date=datetime.date.today(), type=update, cost=cost, level=level + 1))
                territory.save(update_fields=(update, 'extra', ))
                player.money -= cost
                player.save(update_fields=('money', ))
                messages.success(request, "Votre territoire a été amélioré avec succès !")
            except AssertionError as e:
                messages.warning(request, f"Impossible d'améliorer cette province car {e} !")
            except:
                pass
        elif 'troops' in request.POST:
            try:
                reserve = player.reserve
                for territory in territories:
                    value = int(request.POST[territory.zone])
                    if value < territory.troops:
                        raise AssertionError("vous ne pouvez pas retirer des troops déjà présentes")
                    if value > territory.limit:
                        raise AssertionError("vous ne pouvez pas dépasser la limite")
                    reserve -= (value - territory.troops)
                    territory.troops = value
                if 0 > reserve > player.reserve:
                    raise AssertionError("vous n'avez pas assez de troops en réserve")
                Territory.objects.bulk_update(territories, fields=('troops', ))
                player.reserve = reserve
                player.save(update_fields=('reserve', ))
                messages.success(request, "Vos territoires ont été renforcés avec succès !")
            except AssertionError as e:
                messages.warning(request, f"Vos territoires n'ont pas pu être renforcés car {e} !")
            except:
                pass
        elif 'delete' in request.POST:
            Action.objects.filter(player=player, id=request.POST['delete']).delete()
            messages.success(request, "Votre action planifiée a été supprimée avec succès !")
        elif 'capital' in request.POST:
            territory = Territory.objects.filter(
                player=player, player__capital__isnull=True, id=request.POST['capital']
            ).first()
            if territory:
                player.capital = territory
                player.save(update_fields=('capital', ))
                messages.success(request, f"Votre nouvelle capitale a été installée à <strong>{territory}</strong> !")
            else:
                messages.warning(request, "Le territoire sélectionné ne peut être défini comme votre capitale.")
        else:
            form = UserEditForm(request.POST, request.FILES, instance=player)
            if not form.is_valid():
                allow_redirect = False
            else:
                form.save()
                messages.success(request, "Vos informations ont été modifiées avec succès !")
        if allow_redirect:
            return redirect('front:portal')
    last_claim = Claim.objects.aggregate(date=Max('modification_date'))['date'] or 0
    return {
        'player': player,
        'claims': claims,
        'territories': territories,
        'actions': actions,
        'form': form,
        'last_claim': last_claim,
    }


@cache_page(3600)
@login_required
@render_to('map.html')
def map_claims(request):
    claims, world = get_claims()
    maps = folium.Map(**MAPS_CONFIG)
    for player, zones in claims.items():
        style = lambda x, player=player: {
            "fillColor": (player.color or "white") if player else "transparent",
            "color": (player.color or "lightgrey") if player else "white",
            "weight": 1.00,
            "opacity": 0.25}
        popup = folium.GeoJsonPopup(
            fields=("name", "province", "region", "claims", "url"),
            aliases=("Nom", "Province", "Région", "Prétendants", "Action"))
        folium.GeoJson(
            zones,
            tooltip=escape(str(player)) if player else None,
            style_function=style,
            popup=popup,
            name=escape(str(player or "Non revendiqués")),
            show='stats' not in request.GET,
        ).add_to(maps)
    folium.LayerControl().add_to(maps)
    maps = maps.get_root()
    maps.render()
    return {'maps': maps}


@cache_page(3600)
@login_required
@render_to('map.html')
def map_forces(request):
    territories, world = get_territories(request.user)
    maps = folium.Map(**MAPS_CONFIG)
    for player, zones in territories.items():
        style = lambda x, player=player: {
            "fillColor": (player.color or "white") if player else "transparent",
            "color":  (player.color or "lightgrey") if player else "white",
            "weight": 1.00,
            "opacity": 0.25}
        popup = folium.GeoJsonPopup(
            fields=("image", "name", "province", "region", "owner", "troops", "forts", "taxes", "prods", "url"),
            aliases=("", "Nom", "Province", "Région", "Propriétaire", "Troupes", "Forts", "Taxes", "Casernes", "Action"))
        tooltip = escape(str(player)) if player else None
        if player and player.image:
            tooltip = (
                f'<img src="{player.image.url}" style="max-width: 50px; max-height: 25px; '
                f'margin-right: 5px;"><span class="align-middle">{tooltip}</span>')
        folium.GeoJson(
            zones,
            tooltip=tooltip,
            style_function=style,
            popup=popup,
            name=escape(str(player)) if player else "Indépendant",
            show='stats' not in request.GET,
        ).add_to(maps)
    folium.LayerControl().add_to(maps)
    maps = maps.get_root()
    maps.render()
    return {'maps': maps}


@cache_page(3600)
@login_required
@render_to('map.html')
def map_stats(request, type):
    world, zones = get_zones()
    maps = folium.Map(**MAPS_CONFIG)
    if type == 'claims':
        folium.Choropleth(
            geo_data=world,
            data=dict(Claim.objects.values_list('zone').order_by('zone').annotate(count=Count('id'))),
            key_on='properties.code',
            color='white',
            fill_color='YlOrRd',
            fill_opacity=0.50,
            line_opacity=1.00,
            nan_fill_opacity=0.00,
            nan_fill_color='grey',
        ).add_to(maps)
    elif type in ('troops', 'forts', 'taxes', 'prods'):
        folium.Choropleth(
            geo_data=world,
            data=dict(Territory.objects.values_list('zone', type)),
            key_on='properties.code',
            color='white',
            fill_color='RdYlGn',
            fill_opacity=0.50,
            line_opacity=1.00,
            nan_fill_opacity=0.00,
            nan_fill_color='grey',
        ).add_to(maps)
    maps = maps.get_root()
    maps.render()
    return {'maps': maps}


@never_cache
@login_required
@render_to('claim.html')
def claim(request, zone):
    zones = dict(ZONES)
    if zone not in zones:
        messages.warning(request, "Cette province n'existe pas !")
        return redirect('front:portal')
        # raise Http404("Cette province n'existe pas !")
    claim = Claim.objects.filter(player=request.user, zone=zone).first()
    if request.method == 'POST':
        form = ClaimForm(request.POST, instance=claim)
        if request.POST.get('delete'):
            Claim.objects.filter(player=request.user, zone=zone).delete()
            messages.success(request, "Revendication supprimée avec succès !")
            return redirect('front:portal')
        elif form.is_valid():
            form.save()
            messages.success(
                request,
                f"Vous avez revendiqué <strong>{form.instance.get_zone_display()}</strong> "
                f"au prétexte de <i>\"{form.instance.get_reason_display().lower()}\"</i> !")
            return redirect('front:portal')
    else:
        form = ClaimForm(instance=claim, initial={'player': request.user, 'zone': zone})
    return {'form': form, 'zone': zones[zone]}


@never_cache
@login_required
@render_to('action.html')
def action(request, zone):
    action_type = request.resolver_match.url_name[0].upper()
    territory = Territory.objects.select_related('player')
    if action_type == 'A':
        territory = territory.exclude(player=request.user)
    elif action_type == 'M':
        territory = territory.filter(player=request.user)
    territory = get_object_or_404(territory, zone=zone)
    neighbours = Territory.objects.filter(player=request.user, zone__in=NEIGHBOURS[zone])
    if not neighbours:
        messages.warning(request, "Aucune province voisine n'est disponible pour cette action !")
        return redirect('front:portal')
        # raise Http404("Aucune province voisine n'est disponible pour cette action !")
    initial = {'date': datetime.date.today(), 'player': request.user, 'target': territory, 'type': action_type}
    if request.method == 'POST':
        form = ActionForm(request.POST)
        form.fields['source'].queryset = neighbours
        form.fields['source'].empty_label = None
        if form.is_valid():
            form.save()
            messages.success(request, "Votre action a été enregistrée avec succès !")
            return redirect('front:portal')
    else:
        form = ActionForm(initial=initial)
        form.fields['source'].queryset = neighbours
        form.fields['source'].empty_label = None
    return {'form': form, 'target': territory, 'action': action_type}


@render_to('register.html')
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            player = form.save()
            login(request=request, user=player)
            return redirect('front:portal')
    else:
        form = UserRegisterForm()
    return {'form': form}


@never_cache
@login_required
@render_to('info.html')
def info(request):
    attacker, defender = request.GET.get('attacker'), request.GET.get('defender')
    attacker = Territory.objects.select_related('player').filter(id=attacker).first() if attacker else None
    defender = Territory.objects.select_related('player').filter(id=defender).first() if defender else None
    return {'attacker': attacker, 'defender': defender}
