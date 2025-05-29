from .decorators import admin_required
from .models import AlcaldiaVista
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import Http404

def signup(request): #Registros de usuarios
    if request.method == 'GET':
        return render(request, 'signup.html', {"form": UserCreationForm})
    else:
        if request.POST["password1"] == request.POST["password2"]:
            try:
                user = User.objects.create_user(
                    username=request.POST["username"],
                    password=request.POST["password1"],
                    email=request.POST["email"],
                    first_name=request.POST["nombre"]
                )
                user.save()
                login(request, user)
                return redirect('signin')
            except IntegrityError:
                return render(request, 'signup.html', {
                    "form": UserCreationForm,
                    "error": "El nombre de usuario ya existe."
                })
        return render(request, 'signup.html', {
            "form": UserCreationForm,
            "error": "Las contraseñas no coinciden."
        })

def estimaciones(request):
    return render(request, 'estimaciones.html')

def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html', {"form": AuthenticationForm()})
    else:
        input_value = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=input_value, password=password)

        if user is None:
            try:
                user_obj = User.objects.get(email=input_value)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)

            # 🔒 Redirección según tipo de usuario
            if user.is_staff or user.is_superuser:
                return redirect('gentelella_page', page='index')  # Dashboard admin
            else:
                return redirect('welcome')  # Usuario normal
        else:
            return render(request, 'signin.html', {
                "form": AuthenticationForm(),
                "error": "Usuario o contraseña incorrectos."
            })


def signout(request):
    logout(request)
    return redirect('signin')


def forgot_password(request):
    return render(request, 'forgotpassword.html')

def welcome(request):
    images_auth = ["casa5.png", "casa6.png", "casa1.png", "casa2.png", "casa3.png", "casa4.png"]
    images_guest = ["Altatium.png", "forbes.png"]
    context = {
        "images_auth": images_auth,
        "images_guest": images_guest
    }
    return render(request, "welcome.html", context)

# alcaldias 

def vista_benito_juarez(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Benito Juárez')
    return render(request, 'alcaldias/benito.html', {'datos': datos})

def vista_alvaro(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Álvaro Obregón')
    return render(request, 'alcaldias/alvaro.html', {'datos': datos})

def vista_coyoacan(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Coyoacán')
    return render(request, 'alcaldias/coyoacan.html', {'datos': datos})

def vista_xochimilco(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Xochimilco')
    return render(request, 'alcaldias/xochimilco.html', {'datos': datos})  

def vista_azcapotzalco(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Azcapotzalco')
    return render(request, 'alcaldias/azcapotzalco.html', {'datos': datos})  

def vista_cuajimalpa(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Cuajimalpa de Morelos')
    return render(request, 'alcaldias/cuajimalpa.html', {'datos': datos}) 

def vista_cuauhtemoc(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Cuauhtémoc')
    return render(request, 'alcaldias/cuauhtemoc.html', {'datos': datos}) 

def vista_miguel(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Miguel Hidalgo')
    return render(request, 'alcaldias/miguel.html', {'datos': datos}) 

def vista_gustavo(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Gustavo A. Madero')
    return render(request, 'alcaldias/gustavo.html', {'datos': datos}) 

def vista_iztacalco(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Iztacalco')
    return render(request, 'alcaldias/iztacalco.html', {'datos': datos}) 

def vista_iztapalapa(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Iztapalapa')
    return render(request, 'alcaldias/iztapalapa.html', {'datos': datos}) 

def vista_magda(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='La Magdalena Contreras')
    return render(request, 'alcaldias/magda.html', {'datos': datos}) 

def vista_milpa(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Milpa Alta')
    return render(request, 'alcaldias/milpa.html', {'datos': datos}) 

def vista_tlahuac(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Tláhuac')
    return render(request, 'alcaldias/tlahuac.html', {'datos': datos}) 

def vista_tlalpan(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Tlalpan')
    return render(request, 'alcaldias/tlalpan.html', {'datos': datos}) 

def vista_venustiano(request):
    datos = AlcaldiaVista.objects.filter(Alcaldia__iexact='Venustiano Carranza')
    return render(request, 'alcaldias/venustiano.html', {'datos': datos}) 

# fin de alcaldias 

def admin_required(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(admin_required)
def gentelella_view(request, page):
    try:
        return render(request, f'gentelella/{page}.html')
    except:
        return render(request, 'gentelella/page_404.html', status=404)