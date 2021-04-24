from common.admin import create_admin, CommonAdmin
from django.contrib.auth.admin import UserAdmin

from krakenapp.models import Action, Claim,  Player, Territory


class PlayerAdmin(UserAdmin):
    list_display = ('id', 'username', 'full_name', 'reserve', 'money', 'auto', 'ready', )
    list_display_links = ('username', )
    fieldsets = UserAdmin.fieldsets + (
        ("Kraken", {'fields': ('full_name', 'color', 'reserve', 'money', 'auto', 'ready', )}), )
    filter_horizontal = ('groups', 'user_permissions', )
    search_fields = UserAdmin.search_fields + ('full_name', )

    def get_form(self, request, obj=None, change=False, **kwargs):
        from django.forms import TextInput
        widgets = kwargs.get("widgets", {})
        widgets.update(color=TextInput(attrs={"type": "color"}))
        kwargs["widgets"] = widgets
        return super().get_form(request, obj=obj, change=change, **kwargs)


class ClaimAdmin(CommonAdmin):
    def get_list_display(self, request):
        data = list(super().get_list_display(request))
        data.insert(-2, 'has_infos')
        return data

    def has_infos(self, obj):
        return bool(obj.infos.strip())

    has_infos.short_description = 'info'
    has_infos.admin_order_field = 'infos'
    has_infos.boolean = True


create_admin(
    Player, baseclass=PlayerAdmin, date_hierarchy='creation_date',
    list_display=('username', 'full_name', 'reserve', 'money', 'auto', 'ready', ))
create_admin(Claim, baseclass=ClaimAdmin, list_filter=('player', 'creation_date', 'modification_date'))
create_admin(
    Territory, ordering=('zone', ), search_fields=('zone', ),
    list_filter=('player', ), list_display=('zone', 'player', 'troops', 'forts', 'prods', 'taxes', 'limit'))
create_admin(Action, autocomplete_fields=('player', 'defender', 'source', 'target', ))
