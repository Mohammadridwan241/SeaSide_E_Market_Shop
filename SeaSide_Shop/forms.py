from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User 
from django.contrib.auth.password_validation import validate_password

from .models import Rating, Order


CITY_CHOICES = [
    ('', 'Select city'),
    ('Chattogram', 'Chattogram'),
    ('Outside Chattogram', 'Outside Chattogram'),
]

PAYMENT_METHOD_CHOICES = [
    ('cod', 'Cash on Delivery'),
    ('sslcommerz', 'Pay Online with SSLCommerz'),
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
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        required=True,
        widget=forms.RadioSelect,
        initial='cod',
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


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )


class PasswordResetCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-digit code'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')

        if password1:
            validate_password(password1)

        return cleaned_data
