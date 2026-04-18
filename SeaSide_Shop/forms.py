from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User 

from .models import Rating, Order


CITY_CHOICES = [
    ('', 'Select city'),
    ('Chattogram', 'Chattogram'),
    ('Outside Chattogram', 'Outside Chattogram'),
]

class RegistrationForm(UserCreationForm):
    class Meta:
        model = User 
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating' : forms.Select(choices=[(i,i) for i in range(1,6)]),
            'comment' : forms.Textarea(attrs={'rows' : 4})
        }

class CheckoutForm(forms.ModelForm):
    city = forms.ChoiceField(
        choices=CITY_CHOICES,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].required = True

    class Meta:
        model = Order 
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'postal_code', 'city', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3, 'required': False}),
        }
