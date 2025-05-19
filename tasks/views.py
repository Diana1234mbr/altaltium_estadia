from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError

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
            return redirect('welcome')
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
    return render(request, 'welcome.html')
