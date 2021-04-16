from common.api.utils import create_api, disable_relation_fields

from krakenapp.models import Action, Claim, Player, Territory

disable_relation_fields(Player, Action, Claim, Territory)
router, all_serializers, all_viewsets = create_api(Player, Action, Claim, Territory)

namespace = 'krakenapp-api'
app_name = 'krakenapp'
urlpatterns = [] + router.urls
urls = (urlpatterns, namespace, app_name)
