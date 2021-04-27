from common.admin import create_admin, CommonAdmin, EntityAdmin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from krakenapp.models import Action, Claim, Player, Territory


@admin.register(Player)
class PlayerAdmin(UserAdmin):
    list_display = ('id', 'full_name', 'capital', 'reserve', 'money', 'auto', 'ready', )
    list_display_links = ('id', 'full_name', )
    fieldsets = UserAdmin.fieldsets + (
        ("Risk", {'fields': ('full_name', 'color', 'capital', 'reserve', 'money', 'auto', 'ready', 'extra', )}), )
    filter_horizontal = ('groups', 'user_permissions', )
    search_fields = UserAdmin.search_fields + ('full_name', )
    autocomplete_fields = ('capital', )
    date_hierarchy = 'last_login'

    def get_form(self, request, obj=None, *args, **kwargs):
        from django.forms import TextInput
        widgets = kwargs.get('widgets', {})
        widgets.update(color=TextInput(attrs={'type': 'color'}))
        kwargs['widgets'] = widgets
        form = super().get_form(request, obj=obj, **kwargs)
        field = form.base_fields['capital']
        field.queryset = field.queryset.filter(player=obj)
        return form


class ClaimAdmin(EntityAdmin):
    def get_list_display(self, request):
        data = list(super().get_list_display(request))
        data.insert(-2, 'has_infos')
        return data

    def has_infos(self, obj):
        return bool(obj.infos.strip())

    has_infos.short_description = 'info'
    has_infos.admin_order_field = 'infos'
    has_infos.boolean = True


class TerritoryAdmin(EntityAdmin):
    pass


class ActionAdmin(CommonAdmin):
    pass


create_admin(
    Claim, baseclass=ClaimAdmin,
    list_filter=('creation_date', 'modification_date', 'player', ))
create_admin(
    Territory, baseclass=TerritoryAdmin,
    ordering=('zone', ), search_fields=('zone', ), list_filter=('player', ),
    list_display=('zone', 'player', 'troops', 'forts', 'prods', 'taxes', 'limit', ))
create_admin(
    Action, baseclass=ActionAdmin,
    list_filter=('date', 'creation_date', 'type', 'done', 'player', 'defender', ),
    autocomplete_fields=('player', 'defender', 'source', 'target', ))
