from django.template import Library
from django.utils.safestring import mark_safe

from krakenapp.enums import COSTS

register = Library()


@register.filter(name='reformat')
def reformat(value):
    return mark_safe(value.replace(' (', '<br /><small>').replace(')', '</small>'))


@register.simple_tag(name='check_update')
def check_update(territory, type, level, money):
    cost = COSTS.get(type)
    if not cost:
        return level
    cost = cost(level)
    if cost > money:
        return mark_safe(
            f'<strong title="Coût d\'amélioration : {cost}<br>(il manque {cost - money})" '
            f'data-toggle="tooltip" data-html="true">{level}</strong>')
    return mark_safe(
        f'<button type="submit" class="btn btn-sm btn-primary font-weight-bold" title="Coût d\'amélioration : {cost}" '
        f'name="improve" value="{type}_{territory}" data-toggle="tooltip">{level} <i class="fa fa-plus"></i></button>')
