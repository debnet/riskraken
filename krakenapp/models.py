from common.fields import JsonField
from common.models import CommonModel, Entity, EntityQuerySet
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, F, OuterRef, Subquery, Sum, Value
from django.utils.timezone import now

from krakenapp.enums import REASONS, TYPES, ZONES


class Player(AbstractUser, Entity):
    full_name = models.CharField(
        max_length=200, blank=True, verbose_name="nom",
        help_text="Si renseigné, ce nom s'affichera à la place de votre pseudo sur les cartes et le portail.")
    color = models.CharField(
        max_length=20, blank=True, verbose_name="couleur",
        help_text="Couleur qui sera utilisée pour représenter vos territoires et/ou revendications.")
    reserve = models.PositiveIntegerField(default=0, verbose_name="renforts")
    money = models.PositiveIntegerField(default=0, verbose_name="argent")
    auto = models.BooleanField(
        default=False, verbose_name="mode automatique",
        help_text="Cochez cette case si vous souhaitez que le jeu prenne les décisions pendant la partie.<br>"
                  "Cependant, toute action planifiée avec ce mode actif ne sera pas prise en compte.")
    ready = models.BooleanField(
        default=False, verbose_name="prêt à jouer",
        help_text="Cochez cette case si vous avez terminé de revendiquer des territoires et que vous êtes prêt à jouer."
                  "<br>Cette option n'a plus d'effet une fois la partie démarrée.")

    def __str__(self):
        if self.full_name:
            return self.full_name
        return super().__str__()

    class Meta(AbstractUser.Meta):
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"


class ClaimQuerySet(EntityQuerySet):
    def get_ordered(self):
        return self.annotate(
            power=Value(10) - F('reason') + F('weight'),
            points=Sum('player__claims__reason'),
            claims=Count('player__claims'),
        ).order_by('zone', 'power', 'points', '-claims', 'id')

    def with_count(self):
        subquery = Claim.objects.values('zone').filter(zone=OuterRef('zone')).annotate(count=Count('id'))
        return self.annotate(count=Subquery(subquery.values('count')))


class Claim(Entity):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name='claims', verbose_name="utilisateur")
    zone = models.CharField(max_length=10, choices=ZONES, verbose_name="zone")
    reason = models.PositiveSmallIntegerField(
        choices=REASONS, verbose_name="motif", help_text=(
            "Certains motifs de revendication ne peuvent être utilisés qu'une seule et unique fois.<br>"
            "Plus une justification est importante, plus votre revendication est forte.<br>"
            "Cependant plus vous avez de revendications, plus le poids de vos justifications baisse."))
    infos = models.TextField(
        blank=True, verbose_name="informations complémentaires", help_text=(
            "Fournissez un complément d'information pour appuyer votre revendication. Par exemple :<ul>"
            "<li>le nom de la commune où vous avez grandi,</li>"
            "<li>vos liens avec votre famille sur place,</li>"
            "<li>la nature du travail que vous y exerciez,</li>"
            "<li>la durée et/ou l'année de résidence dans cette région.</li></ul>"
            "Ces informations permettent d'ajouter du poids à votre revendication si le territoire est disputé."))
    weight = models.SmallIntegerField(default=0, verbose_name="poids")
    objects = ClaimQuerySet.as_manager()

    def __str__(self):
        return self.get_zone_display()

    def clean(self):
        if self.reason in (1, 2, 3):
            queryset = Claim.objects.filter(player=self.player, reason=self.reason)
            queryset = queryset.exclude(id=self.id) if self.id else queryset
            if queryset.exists():
                raise ValidationError({
                    'reason': "Il ne peut y avoir qu'une seule revendication possible avec ce motif !"})

    class Meta:
        verbose_name = "revendication"
        verbose_name_plural = "revendications"
        unique_together = ('zone', 'player')
        ordering = ('zone', 'player')


class Territory(Entity):
    player = models.ForeignKey(
        Player, blank=True, null=True, on_delete=models.SET_NULL, related_name='territories', verbose_name="utilisateur")
    zone = models.CharField(max_length=10, choices=ZONES, verbose_name="zone")
    troops = models.PositiveSmallIntegerField(default=0, verbose_name="troupes")
    forts = models.PositiveSmallIntegerField(default=0, verbose_name="forts")
    prods = models.PositiveSmallIntegerField(default=0, verbose_name="production")
    taxes = models.PositiveSmallIntegerField(default=0, verbose_name="taxes")
    limit = models.PositiveSmallIntegerField(default=10, verbose_name="limite")
    owner = models.ForeignKey(
        Player, blank=True, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name="propriétaire")

    def __str__(self):
        return self.get_zone_display()

    def clean(self):
        if self.troops > self.limit:
            raise ValidationError({
                'troops': f"Le nombre de troupes ({self.troops}) de cette province "
                          f"dépasse la limite autorisée de {self.limit}."})

    class Meta:
        verbose_name = "territoire"
        verbose_name_plural = "territoires"
        unique_together = ('zone', 'player')
        ordering = ('zone', 'player')


class Action(CommonModel):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name='actions', verbose_name="utilisateur")
    date = models.DateField(blank=True, verbose_name="date")
    type = models.CharField(max_length=1, choices=TYPES, verbose_name="type")
    source = models.ForeignKey(
        Territory, on_delete=models.CASCADE, related_name='+', verbose_name="source",
        help_text="Sélectionnez la province voisine d'où vont partir les troupes pour arriver à destination.")
    target = models.ForeignKey(
        Territory, on_delete=models.CASCADE, related_name='+', verbose_name="cible",
        help_text="Sélectionner la province de destination des troupes impliquées dans l'action.")
    amount = models.PositiveSmallIntegerField(
        default=1, verbose_name="quantité",
        help_text="Indiquez la quantité de troupes qui sera impliquée.<br>Pour prendre le contrôle d'une province, "
                  "il faut au moins une unité excédentaire survivante pour occuper la province.<br>"
                  "<strong>Attention !</strong> Si vos troupes sont réduites par une attaque, "
                  "la réserve sera utilisée pour compenser les pertes.")
    defender = models.ForeignKey(
        Player, blank=True, null=True, on_delete=models.SET_NULL, related_name='attacks', verbose_name="défenseur")
    details = JsonField(blank=True, default=dict, verbose_name="détails")
    creation_date = models.DateTimeField(auto_now=True, verbose_name="date de planification")
    done = models.BooleanField(default=False, verbose_name="traité")

    def __str__(self):
        return f'[{self.date}] {self.player} ({self.get_type_display()})'

    def clean(self):
        self.date = self.date or now().date()
        hostile_actions = Action.objects.filter(type='A', target__player__isnull=False)
        player_without_troops = Player.objects.values('id').filter(auto=False).annotate(
            troops=Sum('territories__troops')).filter(troops=0)
        if self.type == 'A' and self.target.player_id and \
                not hostile_actions.exists() and player_without_troops.exists():
            raise ValidationError({
                '__all__': f"Certains joueurs n'ont pas encore renforcé leurs territoires, il n'est donc "
                           f"pas encore possible de planifier une action hostile envers un joueur."})
        if self.amount < 0 or self.amount > self.source.troops:
            raise ValidationError({
                'amount': f"Le nombre de troupes sélectionné est incorrect, "
                          f"il doit être compris entre 1 et {self.source.troops}."})

    class Meta:
        verbose_name = "action"
        verbose_name_plural = "actions"
        unique_together = ('date', 'player', 'source')
        ordering = ('-date', 'player')
