from django.contrib import messages
from .decorators import admin_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import Http404
from django.http import JsonResponse
from .models import Estados, Municipios, Colonias, CodigosPostales, AlcaldiaVistas, Propiedades
from django.views.decorators.csrf import csrf_exempt
import json


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
    

# desde aqui

def estimaciones(request):
    if request.method == 'POST':
        # Obtener los datos del formulario
        tipo_propiedad = request.POST.get('tipo_propiedad')
        calle = request.POST.get('calle')
        id_colonia = request.POST.get('colonia')
        id_codigo_postal = request.POST.get('cp')
        recamaras = request.POST.get('recamaras')
        sanitarios = request.POST.get('sanitarios')
        estacionamiento = request.POST.get('estacionamiento')
        terreno = request.POST.get('terreno')
        construccion = request.POST.get('construccion')
        estado_conservacion = request.POST.get('estado_conservacion')
        comentarios = request.POST.get('comentarios', '')  # Opcional, puede ser vacío
        id_municipio = request.POST.get('municipio')
        id_estado = request.POST.get('estado')

        # Validar campos requeridos
        campos_requeridos = [
            tipo_propiedad, calle, id_colonia, id_codigo_postal,
            recamaras, sanitarios, estacionamiento,
            terreno, construccion, estado_conservacion,
            id_municipio, id_estado
        ]

        if not all(campos_requeridos):
            messages.error(request, "Todos los campos obligatorios deben ser llenados.")
            context = {
                'estados': Estados.objects.all(),
                'municipios': Municipios.objects.all(),
                'colonias': Colonias.objects.all(),
                'codigos_postales': CodigosPostales.objects.all(),
                'propiedades': Propiedades.objects.all(),
                'datos_alcaldia': AlcaldiaVistas.objects.all(),
            }
            return render(request, 'estimaciones.html', context)

        try:
            # Convertir tipos de datos
            recamaras = int(recamaras)
            sanitarios = float(sanitarios)
            estacionamiento = int(estacionamiento)
            terreno = float(terreno)
            construccion = float(construccion)
            id_colonia = int(id_colonia)
            id_codigo_postal = int(id_codigo_postal)
            id_municipio = int(id_municipio)
            id_estado = int(id_estado)

            # Obtener colonia y precio promedio
            colonia = Colonias.objects.filter(id_colonia=id_colonia).first()
            if not colonia:
                messages.error(request, "Colonia no encontrada.")
                context = {
                    'estados': Estados.objects.all(),
                    'municipios': Municipios.objects.all(),
                    'colonias': Colonias.objects.all(),
                    'codigos_postales': CodigosPostales.objects.all(),
                    'propiedades': Propiedades.objects.all(),
                    'datos_alcaldia': AlcaldiaVistas.objects.all(),
                }
                return render(request, 'estimaciones.html', context)

            precio_promedio = float(colonia.promedio_precio or 0)

            # Coeficientes por estado de conservación
            coef_conservacion = {
                'Muy bueno': 0.0625,
                'Bueno': 0.0625,
                'Regular': 0.01375,
                'Malo': 0.01855,
                'Muy malo': 1
            }

            # Cálculo 1: valor inicial
            valor_inicial = precio_promedio * construccion

            # Cálculo 2: aplicar coeficiente
            coef = coef_conservacion.get(estado_conservacion, 1)
            valor_aprox = valor_inicial * coef if estado_conservacion != 'Muy malo' else valor_inicial

            # Cálculo 3: valor comercial
            if estado_conservacion == 'Muy bueno':
                valor_comercial = valor_inicial + valor_aprox
            elif estado_conservacion == 'Bueno':
                valor_comercial = valor_inicial - valor_aprox
            elif estado_conservacion == 'Regular':
                valor_comercial = valor_inicial - valor_aprox
            elif estado_conservacion == 'Malo':
                valor_comercial = valor_inicial - valor_aprox
            else:
                valor_comercial = valor_aprox

            # Cálculo 4: valor judicial
            valor_judicial = (2 / 3) * valor_comercial

            # Guardar en base de datos
            propiedad = Propiedades(
                tipo_propiedad=tipo_propiedad,
                calle=calle,
                id_colonia_id=id_colonia,
                id_codigo_postal_id=id_codigo_postal,
                recamaras=recamaras,
                sanitarios=sanitarios,
                estacionamiento=estacionamiento,
                terreno=terreno,
                construccion=construccion,
                estado_conservacion=estado_conservacion,
                comentarios=comentarios,
                valor_aprox=valor_aprox,
                id_municipio_id=id_municipio,
                id_estado_id=id_estado,
                valor_judicial=valor_judicial,
                valor_comercial=valor_comercial,
                valor_inicial=valor_inicial  # Corregido de valor_inicia a valor_inicial
            )
            propiedad.save()

            # Redirigir a la vista de resultados con los datos de la propiedad
            messages.success(request, f"Propiedad registrada y calculada exitosamente.")
            return render(request, 'resultados_estimaciones.html', {'propiedad': propiedad})

        except Exception as e:
            messages.error(request, f"Ocurrió un error: {str(e)}")
            context = {
                'estados': Estados.objects.all(),
                'municipios': Municipios.objects.all(),
                'colonias': Colonias.objects.all(),
                'codigos_postales': CodigosPostales.objects.all(),
                'propiedades': Propiedades.objects.all(),
                'datos_alcaldia': AlcaldiaVistas.objects.all(),
            }
            return render(request, 'estimaciones.html', context)

    # Si es GET, mostrar formulario
    context = {
        'estados': Estados.objects.all(),
        'municipios': Municipios.objects.all(),
        'colonias': Colonias.objects.all(),
        'codigos_postales': CodigosPostales.objects.all(),
        'propiedades': Propiedades.objects.all(),
        'datos_alcaldia': AlcaldiaVistas.objects.all(),
    }
    return render(request, 'estimaciones.html', context)
 

 #hasta aqui



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
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Benito Juárez')
    return render(request, 'alcaldias/benito.html', {'datos': datos})

def vista_alvaro(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Álvaro Obregón')
    return render(request, 'alcaldias/alvaro.html', {'datos': datos})

def vista_coyoacan(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Coyoacán')
    return render(request, 'alcaldias/coyoacan.html', {'datos': datos})

def vista_xochimilco(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Xochimilco')
    return render(request, 'alcaldias/xochimilco.html', {'datos': datos})  

def vista_azcapotzalco(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Azcapotzalco')
    return render(request, 'alcaldias/azcapotzalco.html', {'datos': datos})  

def vista_cuajimalpa(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Cuajimalpa de Morelos')
    return render(request, 'alcaldias/cuajimalpa.html', {'datos': datos}) 

def vista_cuauhtemoc(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Cuauhtémoc')
    return render(request, 'alcaldias/cuauhtemoc.html', {'datos': datos}) 

def vista_miguel(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Miguel Hidalgo')
    return render(request, 'alcaldias/miguel.html', {'datos': datos}) 

def vista_gustavo(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Gustavo A. Madero')
    return render(request, 'alcaldias/gustavo.html', {'datos': datos}) 

def vista_iztacalco(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Iztacalco')
    return render(request, 'alcaldias/iztacalco.html', {'datos': datos}) 

def vista_iztapalapa(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Iztapalapa')
    return render(request, 'alcaldias/iztapalapa.html', {'datos': datos}) 

def vista_magda(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='La Magdalena Contreras')
    return render(request, 'alcaldias/magda.html', {'datos': datos}) 

def vista_milpa(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Milpa Alta')
    return render(request, 'alcaldias/milpa.html', {'datos': datos}) 

def vista_tlahuac(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Tláhuac')
    return render(request, 'alcaldias/tlahuac.html', {'datos': datos}) 

def vista_tlalpan(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Tlalpan')
    return render(request, 'alcaldias/tlalpan.html', {'datos': datos}) 

def vista_venustiano(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Venustiano Carranza')
    return render(request, 'alcaldias/venustiano.html', {'datos': datos}) 

# fin de alcaldias 

def admin_required(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(admin_required)



 #crud colonia 
def gentelella_view(request, page):
    try:
        context = {}
        if page == "cal_colonia":
            colonias = Colonias.objects.all()
            municipios = Municipios.objects.all()
            if 'eliminar' in request.GET:
                try:
                    Colonias.objects.filter(id_colonia=request.GET['eliminar']).delete()
                    messages.success(request, "Colonia eliminada correctamente.")
                except Colonias.DoesNotExist:
                    messages.error(request, f"No se encontró la colonia con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_colonia')
            if request.method == 'POST' and 'editar' not in request.GET:
                nombre = request.POST.get('nombre')
                promedio_precio = request.POST.get('promedio_precio', None)
                id_municipio = request.POST.get('id_municipio')
                if nombre and id_municipio:
                    try:
                        municipio = Municipios.objects.get(id_municipio=id_municipio)
                        Colonias.objects.create(
                            nombre=nombre,
                            id_municipio=municipio,
                            promedio_precio=promedio_precio
                        )
                        messages.success(request, "Colonia creada correctamente.")
                    except Municipios.DoesNotExist:
                        messages.error(request, "Municipio no encontrado.")
                    except IntegrityError:
                        messages.error(request, "Ya existe una colonia con ese nombre en el municipio seleccionado.")
                else:
                    messages.error(request, "Faltan datos para crear la colonia.")
                return redirect('gentelella_page', page='cal_colonia')
            context = {
    'colonias': colonias,
    'municipios': municipios,}
        elif page == "editar_colonia":
            context['municipios'] = Municipios.objects.all()
            if 'editar' in request.GET:
                try:
                    colonia_editar = Colonias.objects.get(id_colonia=request.GET['editar'])
                    context['colonia_editar'] = colonia_editar
                except Colonias.DoesNotExist:
                    messages.error(request, f"No se encontró la colonia con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_colonia')
            if request.method == 'POST':
                id_colonia = request.POST.get('id_colonia')
                try:
                    colonia = Colonias.objects.get(id_colonia=id_colonia)
                    nombre = request.POST.get('nombre')
                    id_municipio = request.POST.get('id_municipio')
                    promedio_precio = request.POST.get('promedio_precio', None)
                    if nombre and id_municipio:
                        municipio = Municipios.objects.get(id_municipio=id_municipio)
                        colonia.nombre = nombre
                        colonia.id_municipio = municipio
                        colonia.promedio_precio = promedio_precio if promedio_precio else None
                        colonia.save()
                        messages.success(request, "Colonia actualizada correctamente.")
                        return redirect('gentelella_page', page='cal_colonia')
                    else:
                        messages.error(request, "Faltan datos para actualizar la colonia.")
                except Colonias.DoesNotExist:
                    messages.error(request, f"No se encontró la colonia con ID {id_colonia}.")
                except Municipios.DoesNotExist:
                    messages.error(request, "Municipio no encontrado.")
                except IntegrityError:
                    messages.error(request, "Ya existe una colonia con ese nombre en el municipio seleccionado.")
                except ValueError:
                    messages.error(request, "El precio promedio debe ser un número válido.")
                return redirect('gentelella_page', page='editar_colonia', editar=id_colonia)
            return render(request, 'gentelella/editar_colonia.html', context)
        return render(request, f'gentelella/{page}.html', context)
    except Exception as e:
        messages.error(request, f"Error inesperado: {str(e)}")
        return render(request, 'gentelella/page_404.html', status=404)
#crud colonia fin 

# Agregado 31/05/25

def obtener_colonias(request):
    municipio_id = request.GET.get('municipio_id')
    try:
        colonias = Colonias.objects.filter(id_municipio=municipio_id).values('id_colonia', 'nombre')
        return JsonResponse(list(colonias), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def obtener_codigos_postales(request):
    colonia_id = request.GET.get('colonia_id')
    try:
        codigos_postales = CodigosPostales.objects.filter(id_colonia=colonia_id).values('id_codigo_postal', 'codigo')
        return JsonResponse(list(codigos_postales), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    