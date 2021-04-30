from common.forms import get_model_form
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Hidden, Submit
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.forms import TextInput, HiddenInput

from krakenapp.models import Action, Claim, Player


class UserRegisterForm(UserCreationForm):
    helper = FormHelper()
    helper.form_method = 'post'
    helper.add_input(Submit('submit', "Créer mon compte", css_class="btn-success"))

    class Meta:
        model = Player
        fields = ('username', 'password1', 'password2')


ClaimForm = get_model_form(Claim, exclude=('weight', ), widgets={
    'player': HiddenInput(),
    'zone': HiddenInput(),
})
helper = FormHelper()
helper.form_method = 'post'
helper.add_input(Submit('submit', "Revendiquer", css_class="btn-success"))
helper.add_input(Submit('delete', "Abandonner", css_class="btn-danger"))
ClaimForm.helper = helper

helper = FormHelper()
helper.form_method = 'post'
helper.add_input(Submit('submit', "Se connecter"))
AuthenticationForm.helper = helper

UserEditForm = get_model_form(Player, fields=('full_name', 'image', 'color', 'ready', 'auto'), widgets={
    'color': TextInput(attrs={'type': 'color', 'style': 'width: 5em'}),
})
helper = FormHelper()
helper.form_method = 'post'
helper.add_input(Submit('submit', "Modifier"))
helper.add_input(Hidden('type', 'player'))
UserEditForm.helper = helper

ActionForm = get_model_form(Action, fields=('player', 'date', 'type', 'source', 'target', 'amount'), widgets={
    'player': HiddenInput(),
    'date': HiddenInput(),
    'type': HiddenInput(),
    'target': HiddenInput(),
}, error_messages={
    '__all__': {
        'unique_together': "Le territoire sélectionné est déjà à l'origine d'une action de votre part.",
    }
})
helper = FormHelper()
helper.form_method = 'post'
helper.add_input(Submit('submit', "Valider"))
ActionForm.helper = helper
