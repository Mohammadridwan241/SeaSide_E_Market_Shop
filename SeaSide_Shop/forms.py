from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User 
from django.contrib.auth.password_validation import validate_password

from .models import Product, Rating, Order


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


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
            }),
        }

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if not first_name:
            raise forms.ValidationError('First name is required.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if not last_name:
            raise forms.ValidationError('Last name is required.')
        return last_name

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if not email:
            raise forms.ValidationError('Email address is required.')

        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This email address is already in use.')

        return email


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'stock', 'available', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'available':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class ProductUpdateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['price', 'stock']
        widgets = {
            'price': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0.01', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '1'}),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Price must be greater than 0.')
        return price

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise forms.ValidationError('Stock cannot be negative.')
        return stock


class FrontendOrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'payment_status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'payment_status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }
