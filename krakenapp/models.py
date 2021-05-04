import datetime
import os
from common.fields import JsonField
from common.models import CommonModel, Entity, EntityQuerySet
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension
from django.db import models
from django.db.models import Case, Count, F, OuterRef, Subquery, Sum, Value, When
from django.utils.timezone import now

from krakenapp.enums import REASONS, TYPES, ZONES


class PlayerManager(UserManager):
    def with_rates(self):
        return self.annotate(
            bonus=Case(When(capital__isnull=False, then=1), default=0),
        ).annotate(
            taxes=Sum('territories__taxes') + F('bonus'),
            prods=Sum('territories__prods') + F('bonus'),
            count=Count('territories'),
        )


def upload_to(instance, filename):
    filename, ext = os.path.splitext(filename)
    return os.path.join('images', f'{instance.id:03}.{int(datetime.datetime.now().timestamp())}{ext}')


def validate_image_size(image):
    try:
        limit = 150
        file_size = image.file.size
        if file_size > limit * 1024:
            raise ValidationError("L'image ne doit pas faire plus de %s kB." % limit)
    except FileNotFoundError:
        pass


class Player(AbstractUser):
    full_name = models.CharField(
        max_length=200, blank=True, verbose_name="nom",
        help_text="Si renseigné, ce nom s'affichera à la place de votre pseudo sur les cartes et le portail.")
    color = models.CharField(
        max_length=20, blank=True, verbose_name="couleur",
        help_text="Couleur qui sera utilisée pour représenter vos territoires et/ou revendications.")
    image = models.ImageField(
        blank=True, null=True, verbose_name="image", upload_to=upload_to,
        validators=[validate_image_file_extension, validate_image_size])
    capital = models.OneToOneField(
        'Territory', on_delete=models.SET_NULL, blank=True, null=True, related_name='+', verbose_name="capitale")
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
    extra = JsonField(blank=True, default=dict, verbose_name="extra")
    objects = PlayerManager()

    def __str__(self):
        if self.full_name:
            return self.full_name
        return super().__str__()

    class Meta(AbstractUser.Meta):
        verbose_name = "joueur"
        verbose_name_plural = "joueurs"
        ordering = ('full_name', )


class ClaimQuerySet(EntityQuerySet):
    def get_ordered(self):
        return self.annotate(
            power=Value(10) - F('reason') + F('weight'),
            points=Sum('player__claims__reason'),
            claims=Count('player__claims'),
        ).order_by('zone', '-power', 'points', 'claims', 'id')

    def with_count(self):
        subquery = Claim.objects.values('zone').filter(zone=OuterRef('zone')).annotate(count=Count('id'))
        return self.annotate(count=Subquery(subquery.values('count')))


class Claim(Entity):
    player = models.ForeignKey(
        'Player', on_delete=models.CASCADE, related_name='claims', verbose_name="joueur")
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
        'Player', blank=True, null=True, on_delete=models.SET_NULL,
        related_name='territories', verbose_name="joueur")
    claim = models.OneToOneField(
        'Claim', blank=True, null=True, on_delete=models.SET_NULL,
        related_name='territory', verbose_name="revendication")
    zone = models.CharField(max_length=10, choices=ZONES, verbose_name="zone")
    troops = models.PositiveSmallIntegerField(default=0, verbose_name="troupes")
    forts = models.PositiveSmallIntegerField(default=0, verbose_name="forts")
    prods = models.PositiveSmallIntegerField(default=0, verbose_name="casernes")
    taxes = models.PositiveSmallIntegerField(default=0, verbose_name="taxes")
    limit = models.PositiveSmallIntegerField(default=10, verbose_name="limite")
    extra = JsonField(blank=True, default=dict, verbose_name="extra")

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
        'Player', on_delete=models.CASCADE, related_name='actions', verbose_name="joueur")
    date = models.DateField(blank=True, verbose_name="date")
    type = models.CharField(max_length=1, choices=TYPES, verbose_name="type")
    source = models.ForeignKey(
        'Territory', on_delete=models.CASCADE, related_name='+', verbose_name="source",
        help_text="Sélectionnez la province voisine d'où vont partir les troupes pour arriver à destination.")
    target = models.ForeignKey(
        'Territory', on_delete=models.CASCADE, related_name='+', verbose_name="cible",
        help_text="Sélectionner la province de destination des troupes impliquées dans l'action.")
    amount = models.PositiveSmallIntegerField(
        default=1, verbose_name="quantité",
        help_text="Indiquez la quantité de troupes qui sera impliquée.<br>Pour prendre le contrôle d'une province, "
                  "il faut au moins une unité excédentaire survivante pour occuper la province.<br>"
                  "<strong>Attention !</strong> Si vos troupes sont réduites par une attaque, "
                  "la réserve sera utilisée pour compenser les pertes.")
    defender = models.ForeignKey(
        'Player', blank=True, null=True, on_delete=models.SET_NULL, related_name='attacks', verbose_name="défenseur")
    details = JsonField(blank=True, default=dict, verbose_name="détails")
    creation_date = models.DateTimeField(auto_now_add=True, verbose_name="date de planification")
    done = models.BooleanField(default=False, verbose_name="traité")

    def __str__(self):
        return f'[{self.date}] {self.get_type_display()} de {self.source} vers {self.target} par {self.player}'

    def clean(self):
        if self.pk:
            return
        self.date = self.date or now().date()
        if self.type == 'A' and self.target.player_id:
            checks = Player.objects.filter(id=self.target.player_id, auto=False).annotate(
                count_troops=Sum('territories__troops'), count_actions=Count('actions')
            ).values_list('count_troops', 'count_actions').first()
            if checks and not any(checks):
                raise ValidationError({
                    '__all__': f"Ce joueur n'a pas encore renforcé ses territoires, il n'est donc "
                               f"pas encore possible de planifier une action hostile envers lui."})
        if 0 > self.amount or self.amount > self.source.troops:
            raise ValidationError({
                'amount': f"Le nombre de troupes sélectionné est incorrect, "
                          f"il doit être compris entre 1 et {self.source.troops or 1}."})

    class Meta:
        verbose_name = "action"
        verbose_name_plural = "actions"
        unique_together = ('date', 'player', 'source')
        ordering = ('-date', 'player')


class Exchange(CommonModel):
    sender = models.ForeignKey(
        'Player', on_delete=models.CASCADE, related_name='sent', verbose_name="expéditeur")
    sender_money = models.PositiveSmallIntegerField(default=0, verbose_name="argent envoyé")
    sender_troops = models.PositiveSmallIntegerField(default=0, verbose_name="troupes envoyées")
    receiver = models.ForeignKey(
        'Player', on_delete=models.CASCADE, related_name='received', verbose_name="destinataire",
        help_text="Le destinataire ne peut être qu'un joueur avec qui vous avez des frontières communes.")
    receiver_money = models.PositiveSmallIntegerField(default=0, verbose_name="argent reçu")
    receiver_troops = models.PositiveSmallIntegerField(default=0, verbose_name="troupes reçues")
    creation_date = models.DateTimeField(auto_now_add=True, verbose_name="date de proposition")
    accepted = models.BooleanField(null=True, verbose_name="accepté")
    done = models.BooleanField(default=False, verbose_name="traité")

    def __str__(self):
        return f'[{self.creation_date.date()}] {self.sender} - {self.receiver}'

    class Meta:
        verbose_name = "échange"
        verbose_name_plural = "échanges"
