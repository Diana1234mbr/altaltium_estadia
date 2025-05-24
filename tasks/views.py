from .decorators import admin_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError

def signup(request):
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

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

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

ALCALDIAS = {
    1: {
        'id': 1,
        'nombre': 'Benito Juárez',
        'imagen': 'images/benito.png',
        'descripcion': 'Zona céntrica con alto valor inmobiliario.',
        'poblacion': '414,711 habitantes',
        'superficie': '26.63 km²',
        'puntos_interes': [
            'Parque de los Venados',
            'Centro Coyoacán',
            'Mercado Mixcoac',
            'Museo Frida Kahlo (cercano)'
        ],
        'coordenadas': {'lat': 19.4000, 'lng': -99.1667},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    2: {
        'id': 2,
        'nombre': 'Coyoacán',
        'imagen': 'images/Coyoacan.png',
        'descripcion': 'Zona cultural e histórica muy turística.',
        'poblacion': '620,416 habitantes',
        'superficie': '54.12 km²',
        'puntos_interes': [
            'Casa Azul (Frida Kahlo)',
            'Plaza Hidalgo',
            'Museo Nacional de las Intervenciones',
            'Jardín Centenario'
        ],
        'coordenadas': {'lat': 19.3494, 'lng': -99.1625},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    3: {
        'id': 3,
        'nombre': 'Miguel Hidalgo',
        'imagen': 'images/miguel.png',
        'descripcion': 'Ubicación privilegiada con zonas como Polanco.',
        'poblacion': '372,889 habitantes',
        'superficie': '46.33 km²',
        'puntos_interes': [
            'Bosque de Chapultepec',
            'Museo Nacional de Antropología',
            'Polanco',
            'Acuario Inbursa'
        ],
        'coordenadas': {'lat': 19.4296, 'lng': -99.2011},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    4: {
        'id': 4,
        'nombre': 'Azcapotzalco',
        'imagen': 'images/azcapotzalco.png',
        'descripcion': 'Zona industrial y comercial con buen acceso a transporte.',
        'poblacion': '414,711 habitantes',
        'superficie': '33.93 km²',
        'historia': 'Históricamente industrial, ahora con desarrollos habitacionales y comerciales.',
        'puntos_interes': [
            'Parque Tezozómoc',
            'Zona Industrial Azcapotzalco',
            'Plaza Azcapotzalco',
            'Universidad Autónoma Metropolitana'
        ],
        'coordenadas': {'lat': 19.4883, 'lng': -99.1917},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    5: {
        'id': 5,
        'nombre': 'Gustavo A. Madero',
        'imagen': 'images/Gustavo A Madero.png',
        'descripcion': 'Área residencial con crecimiento urbano importante.',
        'poblacion': '1,173,351 habitantes',
        'superficie': '81.19 km²',
        'historia': 'Con gran diversidad cultural y crecimiento poblacional acelerado.',
        'puntos_interes': [
            'Basílica de Guadalupe',
            'Parque Cuitláhuac',
            'Mercado La Villa',
            'Estadio Jesús Martínez "Palillo"'
        ],
        'coordenadas': {'lat': 19.4987, 'lng': -99.1303},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    6: {
        'id': 6,
        'nombre': 'Iztapalapa',
        'imagen': 'images/Iztapalapa.png',
        'descripcion': 'Alcaldía más poblada con diversos desarrollos habitacionales.',
        'poblacion': '1,827,868 habitantes',
        'superficie': '117.67 km²',
        'historia': 'Conocida por su tradición en la Semana Santa y sus grandes barrios.',
        'puntos_interes': [
            'Cerros de la Estrella',
            'Parque Cuitláhuac',
            'Piramide de la Estrella',
            'Centro Cultural Iztapalapa'
        ],
        'coordenadas': {'lat': 19.3556, 'lng': -99.0720},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    7: {
        'id': 7,
        'nombre': 'Iztacalco',
        'imagen': 'images/iztacalco.png',
        'descripcion': 'Zona con actividad industrial y residencial.',
        'poblacion': '404,695 habitantes',
        'superficie': '23.29 km²',
        'historia': 'Con fuerte tradición industrial y comunidades tradicionales.',
        'puntos_interes': [
            'Parque Cuitláhuac',
            'Canal de la Viga',
            'Plaza Solidaridad',
            'Estadio Jesús Martínez "Palillo"'
        ],
        'coordenadas': {'lat': 19.4008, 'lng': -99.0931},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    8: {
        'id': 8,
        'nombre': 'Cuauhtémoc',
        'imagen': 'images/Cuauhtemoc.png',
        'descripcion': 'Centro histórico y financiero de la ciudad.',
        'poblacion': '545,830 habitantes',
        'superficie': '32.41 km²',
        'historia': 'Contiene la mayor parte del centro histórico y zonas comerciales importantes.',
        'puntos_interes': [
            'Zócalo CDMX',
            'Torre Latinoamericana',
            'Palacio de Bellas Artes',
            'Museo del Templo Mayor'
        ],
        'coordenadas': {'lat': 19.4333, 'lng': -99.1406},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    9: {
        'id': 9,
        'nombre': 'Venustiano Carranza',
        'imagen': 'images/venustiano.png',
        'descripcion': 'Zona comercial y habitacional importante.',
        'poblacion': '430,978 habitantes',
        'superficie': '33.43 km²',
        'historia': 'Con áreas residenciales y uno de los principales aeropuertos de la ciudad.',
        'puntos_interes': [
            'Aeropuerto Internacional Benito Juárez',
            'Mercado Morelos',
            'Parque Deportivo Reynosa',
            'Foro Sol'
        ],
        'coordenadas': {'lat': 19.4425, 'lng': -99.0896},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    10: {
        'id': 10,
        'nombre': 'Tláhuac',
        'imagen': 'images/tlahuac.png',
        'descripcion': 'Zona con áreas verdes y proyectos residenciales.',
        'poblacion': '363,257 habitantes',
        'superficie': '83.14 km²',
        'historia': 'Con tradición agrícola y crecimiento urbanístico reciente.',
        'puntos_interes': [
            'Parque Ecológico de Tláhuac',
            'Laguna de Tláhuac',
            'Centro Cultural Tláhuac',
            'Mercado de Tláhuac'
        ],
        'coordenadas': {'lat': 19.2632, 'lng': -98.9673},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    11: {
        'id': 11,
        'nombre': 'Xochimilco',
        'imagen': 'images/xochimilco.png',
        'descripcion': 'Famosa por sus canales y áreas culturales.',
        'poblacion': '415,007 habitantes',
        'superficie': '125.28 km²',
        'historia': 'Patrimonio cultural con sus trajineras y chinampas.',
        'puntos_interes': [
            'Canales de Xochimilco',
            'Jardín Etnobotánico',
            'Museo Dolores Olmedo',
            'Parque Ecológico de Xochimilco'
        ],
        'coordenadas': {'lat': 19.2704, 'lng': -99.1019},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    12: {
        'id': 12,
        'nombre': 'Milpa Alta',
        'imagen': 'images/milpa.png',
        'descripcion': 'Zona rural con tradición agrícola.',
        'poblacion': '137,927 habitantes',
        'superficie': '268.63 km²',
        'historia': 'Preserva tradiciones rurales y festividades autóctonas.',
        'puntos_interes': [
            'Parque Nacional Cumbres del Ajusco',
            'Santuario de la Virgen de los Remedios',
            'Pueblos rurales',
            'Mercado de productos orgánicos'
        ],
        'coordenadas': {'lat': 19.1469, 'lng': -99.0608},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    13: {
        'id': 13,
        'nombre': 'Álvaro Obregón',
        'imagen': 'images/Alvaro Obregon.png',
        'descripcion': 'Zona residencial y comercial de alta plusvalía.',
        'poblacion': '727,034 habitantes',
        'superficie': '90.23 km²',
        'historia': 'Mezcla de zonas urbanas modernas y áreas verdes conservadas.',
        'puntos_interes': [
            'Desierto de los Leones',
            'Parque La Mexicana',
            'Centro Comercial Santa Fe',
            'Universidad Iberoamericana'
        ],
        'coordenadas': {'lat': 19.3560, 'lng': -99.2464},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    14: {
        'id': 14,
        'nombre': 'Tlalpan',
        'imagen': 'images/tlalpan.png',
        'descripcion': 'Área con espacios naturales y urbanización controlada.',
        'poblacion': '646,774 habitantes',
        'superficie': '312.92 km²',
        'historia': 'Conserva grandes áreas boscosas y zonas históricas.',
        'puntos_interes': [
            'Parque Nacional Fuentes Brotantes',
            'Zona Arqueológica de Cuicuilco',
            'Centro Cultural Tlalpan',
            'Mercado de Tlalpan'
        ],
        'coordenadas': {'lat': 19.2540, 'lng': -99.1633},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    15: {
        'id': 15,
        'nombre': 'Magdalena Contreras',
        'imagen': 'images/magdalena.png',
        'descripcion': 'Alcaldía con áreas naturales y desarrollo residencial.',
        'poblacion': '243,123 habitantes',
        'superficie': '73.24 km²',
        'historia': 'Con áreas boscosas protegidas y crecimiento urbano moderado.',
        'puntos_interes': [
            'Parque La Mexicana',
            'Museo Casa de la Bola',
            'Área Natural Protegida Los Dinamos',
            'Centro Histórico'
        ],
        'coordenadas': {'lat': 19.3113, 'lng': -99.2687},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    },
    16: {
        'id': 16,
        'nombre': 'Cuajimalpa',
        'imagen': 'images/cuajimalpa.png',
        'descripcion': 'Zona de desarrollos habitacionales exclusivos y corporativos.',
        'poblacion': '217,686 habitantes',
        'superficie': '89.62 km²',
        'historia': 'Con desarrollo inmobiliario de lujo y parques naturales.',
        'puntos_interes': [
            'Parque Nacional Desierto de los Leones',
            'Centro Comercial Santa Fe',
            'Reserva Ecológica de Cuajimalpa',
            'Zona Empresarial'
        ],
        'coordenadas': {'lat': 19.3623, 'lng': -99.2712},
        'precios': [
            {'colonia': 'Nombre', 'valorm2': 52000, 'promedio': 3700000},
            {'colonia': 'Nombre2', 'valorm2': 47000, 'promedio': 3400000},
        ],
    }
}


def welcome(request):
    images_auth = ["casa5.png", "casa6.png", "casa1.png", "casa2.png", "casa3.png", "casa4.png"]
    images_guest = ["Altatium.png", "forbes.png"]

    alcaldias = list(ALCALDIAS.values())  # Usamos la lista de valores
    context = {
        "images_auth": images_auth,
        "images_guest": images_guest,
        "alcaldias": alcaldias,
    }
    return render(request, "welcome.html", context)

def detalle_alcaldia(request, id):
    alcaldia = ALCALDIAS.get(id)
    if not alcaldia:
        return render(request, '404.html', status=404)
    return render(request, 'detalle_alcaldia.html', {'alcaldia': alcaldia})


def admin_required(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(admin_required)
def gentelella_view(request, page):
    try:
        return render(request, f'gentelella/{page}.html')
    except:
        return render(request, 'gentelella/page_404.html', status=404)

