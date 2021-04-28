from common.api.serializers import CommonModelSerializer
from common.api.utils import (
    auto_view, create_api, disable_relation_fields, to_model_serializer, create_model_serializer)
from django.urls import path
from rest_framework import serializers

from krakenapp.models import Action, Claim, Player, Territory

disable_relation_fields(Player, Action, Claim, Territory)
router, all_serializers, all_viewsets = create_api(Player, Action, Claim, Territory)


@to_model_serializer(Claim, exclude=('current_user', ))
class ClaimSerializer(CommonModelSerializer):
    power = serializers.IntegerField()
    points = serializers.IntegerField()
    claims = serializers.IntegerField()
    player = create_model_serializer(Player, exclude=('password', 'groups', 'user_permissions', ))()


@auto_view(['GET'], serializer=ClaimSerializer, many=True)
def claims_by_power(request):
    return Claim.objects.get_ordered()


namespace = 'krakenapp-api'
app_name = 'krakenapp'
urlpatterns = [
    path('claim/power/', claims_by_power, name='claims_by_power'),
] + router.urls
urls = (urlpatterns, namespace, app_name)
