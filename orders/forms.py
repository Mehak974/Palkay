from django import forms
from .models import Address, Order


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'full_name', 'phone', 'address_line_1', 'address_line_2',
            'city', 'state', 'zip_code', 'is_default',
        ]
        widgets = {
            'full_name':      forms.TextInput(attrs={'placeholder': 'Full name', 'class': 'form-input'}),
            'phone':          forms.TextInput(attrs={'placeholder': '+1 (555) 000-0000', 'class': 'form-input'}),
            'address_line_1': forms.TextInput(attrs={'placeholder': 'Street address', 'class': 'form-input'}),
            'address_line_2': forms.TextInput(attrs={'placeholder': 'Apt, suite, unit (optional)', 'class': 'form-input'}),
            'city':           forms.TextInput(attrs={'class': 'form-input'}),
            'state':          forms.TextInput(attrs={'class': 'form-input', 'maxlength': 2}),
            'zip_code':       forms.TextInput(attrs={'placeholder': 'ZIP code', 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.user or not self.user.is_authenticated:
            self.fields.pop('is_default')


class GuestCheckoutForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com', 'class': 'form-input'}),
        help_text='Order confirmation will be sent here.'
    )


class OrderNotesForm(forms.Form):
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Any special delivery instructions? (optional)',
            'class': 'form-input',
        })
    )
