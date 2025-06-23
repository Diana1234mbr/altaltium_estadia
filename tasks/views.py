from fpdf import FPDF
from django.db.models import Count
from io import BytesIO
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import Http404, JsonResponse, HttpResponse
from .models import Estados, Municipios, Colonias, CodigosPostales, AlcaldiaVistas, Propiedades, GraficaAlcaldia
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import matplotlib
matplotlib.use('Agg')  # ← Usa un backend que NO requiere interfaz gráfica
import matplotlib.pyplot as plt
import io
import base64

# Decorador para verificar si es admin
def admin_required(user):
    return user.is_staff or user.is_superuser

# Registro de usuarios
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

# Estimaciones de propiedades
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
                valor_inicial=valor_inicial
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

# Inicio de sesión
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
            if user.is_staff or user.is_superuser:
                return redirect('gentelella_page', page='index')  # Dashboard admin
            else:
                return redirect('welcome')  # Usuario normal
        else:
            return render(request, 'signin.html', {
                "form": AuthenticationForm(),
                "error": "Usuario o contraseña incorrectos."
            })

# Cerrar sesión
def signout(request):
    logout(request)
    return redirect('signin')

import matplotlib.pyplot as plt
import io
import base64
from django.shortcuts import render
from .models import GraficaAlcaldia
from django.db.models import Avg

def analisis(request):
    # Obtener todas las alcaldías únicas y sus promedios desde la base de datos
    alcaldias = GraficaAlcaldia.objects.values('grafica_alcaldia').distinct()
    promedios = []
    labels = []

    for alcaldia in alcaldias:
        alcaldia_nombre = alcaldia['grafica_alcaldia']
        if alcaldia_nombre:  # Asegurarse de que no sea None
            # Calcular el promedio de grafica_promedio para esa alcaldía
            promedio = GraficaAlcaldia.objects.filter(grafica_alcaldia=alcaldia_nombre).aggregate(promedio=Avg('grafica_promedio'))
            if promedio['promedio'] is not None:
                promedios.append(float(promedio['promedio']))
                labels.append(alcaldia_nombre)

    if not promedios:
        return render(request, 'analisis.html', {'error': 'No hay datos disponibles para las alcaldías.'})

    # Crear la gráfica de pastel
    plt.figure(figsize=(10, 10))
    plt.pie(promedios, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title('Promedio de Datos por Alcaldía')

    # Guardar la gráfica en un buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    # Convertir la gráfica a base64
    grafica_base64 = base64.b64encode(buffer.getvalue()).decode()
    buffer.close()

    # Pasar la gráfica a la plantilla
    return render(request, 'analisis.html', {'grafica': grafica_base64})

# Olvidé contraseña
def forgot_password(request):
    return render(request, 'forgotpassword.html')

# Página de bienvenida
def welcome(request):
    images_auth = ["casa5.png", "casa6.png", "casa1.png", "casa2.png", "casa3.png", "casa4.png"]
    images_guest = ["Altatium.png", "forbes.png"]
    context = {
        "images_auth": images_auth,
        "images_guest": images_guest
    }
    return render(request, "welcome.html", context)

# Vistas de alcaldías
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

# Obtener colonias por municipio (AJAX)
def obtener_colonias(request):
    municipio_id = request.GET.get('municipio_id')
    if not municipio_id:
        return JsonResponse({'error': 'ID de municipio no proporcionado'}, status=400)
    try:
        colonias = Colonias.objects.filter(id_municipio=municipio_id).values('id_colonia', 'nombre')
        return JsonResponse(list(colonias), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# Obtener códigos postales por municipio (AJAX)

def obtener_municipios(request):
    estado_id = request.GET.get('estado_id')
    if not estado_id:
        return JsonResponse({'error': 'ID de estado no proporcionado'}, status=400)
    try:
        municipios = Municipios.objects.filter(id_estado=estado_id).values('id_municipio', 'nombre')
        return JsonResponse(list(municipios), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)



def obtener_codigos_postales(request):
    colonia_id = request.GET.get('colonia_id')
    if not colonia_id:
        return JsonResponse({'error': 'ID de colonia no proporcionado'}, status=400)
    try:
        codigos_postales = CodigosPostales.objects.filter(id_colonia=colonia_id).values('id_codigo_postal', 'codigo')
        return JsonResponse(list(codigos_postales), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# Vista principal para panel admin
@login_required
@user_passes_test(admin_required)
def gentelella_view(request, page):
    try:
        context = {}

        # ================= COLONIAS ===================
        if page == "cal_colonia":
            colonias = Colonias.objects.all()
            municipios = Municipios.objects.all()
            estados = Estados.objects.all()

            if 'eliminar' in request.GET:
                try:
                    Colonias.objects.filter(id_colonia=request.GET['eliminar']).delete()
                    messages.success(request, "Colonia eliminada correctamente.")
                except Colonias.DoesNotExist:
                    messages.error(request, f"No se encontró la colonia con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_colonia')

            if request.method == 'POST' and 'editar' not in request.GET:
                nombre = request.POST.get('nombre')
                id_municipio = request.POST.get('id_municipio')
                id_estado = request.POST.get('id_estado')
                promedio_precio = request.POST.get('promedio_precio', None)

                if nombre and id_municipio and id_estado:
                    try:
                        municipio = Municipios.objects.get(id_municipio=id_municipio)
                        estado = Estados.objects.get(id_estado=id_estado)
                        Colonias.objects.create(
                            nombre=nombre,
                            id_municipio=municipio,
                            id_estado=estado,
                            promedio_precio=promedio_precio
                        )
                        messages.success(request, "Colonia creada correctamente.")
                    except Municipios.DoesNotExist:
                        messages.error(request, "Municipio no encontrado.")
                    except Estados.DoesNotExist:
                        messages.error(request, "Estado no encontrado.")
                    except IntegrityError:
                        messages.error(request, "Ya existe una colonia con ese nombre en el municipio seleccionado.")
                else:
                    messages.error(request, "Faltan datos para crear la colonia.")

                return redirect('gentelella_page', page='cal_colonia')

            context.update({
                'colonias': colonias,
                'municipios': municipios,
                'estados': estados,
            })

        # ================= EDITAR COLONIA ===================
        elif page == "editar_colonia":
            context['municipios'] = Municipios.objects.all()
            context['estados'] = Estados.objects.all()

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
                    id_estado = request.POST.get('id_estado')
                    promedio_precio = request.POST.get('promedio_precio', None)
                    if nombre and id_municipio and id_estado:
                        municipio = Municipios.objects.get(id_municipio=id_municipio)
                        estado = Estados.objects.get(id_estado=id_estado)
                        colonia.nombre = nombre
                        colonia.id_municipio = municipio
                        colonia.id_estado = estado
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
                    messages.error(request, "Ya existe una colonia con ese nombre.")
                except ValueError:
                    messages.error(request, "El precio promedio debe ser un número válido.")
                return redirect('gentelella_page', page='editar_colonia', editar=id_colonia)

        # ================= ESTADOS ===================
        elif page == "cal_estado":
            estados = Estados.objects.all()
            context['estados'] = estados

            if 'eliminar' in request.GET:
                try:
                    estado = Estados.objects.get(id_estado=request.GET['eliminar'])
                    estado.delete()
                    messages.success(request, "Estado eliminado correctamente.")
                except Estados.DoesNotExist:
                    messages.error(request, f"No se encontró el estado con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_estado')

            if request.method == 'POST' and 'editar' not in request.GET:
                nombre = request.POST.get('nombre')
                if nombre:
                    try:
                        Estados.objects.create(nombre=nombre)
                        messages.success(request, "Estado creado correctamente.")
                    except IntegrityError:
                        messages.error(request, "Ya existe un estado con ese nombre.")
                else:
                    messages.error(request, "Faltan datos para crear el estado.")
                return redirect('gentelella_page', page='cal_estado')

        # ================= EDITAR ESTADO ===================
        elif page == "editar_estado":
            if 'editar' in request.GET:
                try:
                    estado_editar = Estados.objects.get(id_estado=request.GET['editar'])
                    context['estado_editar'] = estado_editar
                except Estados.DoesNotExist:
                    messages.error(request, f"No se encontró el estado con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_estado')

            if request.method == 'POST':
                id_estado = request.POST.get('id_estado')
                nombre = request.POST.get('nombre')
                try:
                    estado = Estados.objects.get(id_estado=id_estado)
                    if nombre:
                        estado.nombre = nombre
                        estado.save()
                        messages.success(request, "Estado actualizado correctamente.")
                        return redirect('gentelella_page', page='cal_estado')
                    else:
                        messages.error(request, "El nombre del estado no puede estar vacío.")
                except Estados.DoesNotExist:
                    messages.error(request, f"No se encontró el estado con ID {id_estado}.")
                except IntegrityError:
                    messages.error(request, "Ya existe un estado con ese nombre.")
                return redirect('gentelella_page', page='editar_estado', editar=id_estado)

        # ================= MUNICIPIOS ===================
        elif page == "cal_municipio":
            municipios = Municipios.objects.select_related('id_estado').all()
            estados = Estados.objects.all()
            context['municipios'] = municipios
            context['estados'] = estados

            if 'eliminar' in request.GET:
                try:
                    municipio = Municipios.objects.get(id_municipio=request.GET['eliminar'])
                    municipio.delete()
                    messages.success(request, "Municipio eliminado correctamente.")
                except Municipios.DoesNotExist:
                    messages.error(request, f"No se encontró el municipio con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_municipio')

            if request.method == 'POST' and 'editar' not in request.GET:
                nombre = request.POST.get('nombre')
                id_estado = request.POST.get('id_estado')
                if nombre and id_estado:
                    try:
                        estado = Estados.objects.get(id_estado=id_estado)
                        Municipios.objects.create(nombre=nombre, id_estado=estado)
                        messages.success(request, "Municipio creado correctamente.")
                    except Estados.DoesNotExist:
                        messages.error(request, "Estado no encontrado.")
                    except IntegrityError:
                        messages.error(request, "Ya existe un municipio con ese nombre en el estado seleccionado.")
                else:
                    messages.error(request, "Faltan datos para crear el municipio.")
                return redirect('gentelella_page', page='cal_municipio')

        # ================= EDITAR MUNICIPIO ===================
        elif page == "editar_municipio":
            context['estados'] = Estados.objects.all()
            if 'editar' in request.GET:
                try:
                    municipio_editar = Municipios.objects.get(id_municipio=request.GET['editar'])
                    context['municipio_editar'] = municipio_editar
                except Municipios.DoesNotExist:
                    messages.error(request, f"No se encontró el municipio con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_municipio')

            if request.method == 'POST':
                id_municipio = request.POST.get('id_municipio')
                nombre = request.POST.get('nombre')
                id_estado = request.POST.get('id_estado')
                try:
                    municipio = Municipios.objects.get(id_municipio=id_municipio)
                    if nombre and id_estado:
                        estado = Estados.objects.get(id_estado=id_estado)
                        municipio.nombre = nombre
                        municipio.id_estado = estado
                        municipio.save()
                        messages.success(request, "Municipio actualizado correctamente.")
                        return redirect('gentelella_page', page='cal_municipio')
                    else:
                        messages.error(request, "Faltan datos para actualizar el municipio.")
                except Municipios.DoesNotExist:
                    messages.error(request, f"No se encontró el municipio con ID {id_municipio}.")
                except Estados.DoesNotExist:
                    messages.error(request, "Estado no encontrado.")
                except IntegrityError:
                    messages.error(request, "Ya existe un municipio con ese nombre.")
                return redirect('gentelella_page', page='editar_municipio', editar=id_municipio)

        # ================= CÓDIGOS POSTALES ===================
        elif page == "cal_cp":
            codigos = CodigosPostales.objects.select_related('id_colonia').all()
            colonias = Colonias.objects.all()
            municipios = Municipios.objects.all()
            estados = Estados.objects.all()

            context['codigos'] = codigos
            context['colonias'] = colonias
            context['municipios'] = municipios
            context['estados'] = estados

            if 'eliminar' in request.GET:
                try:
                    codigo = CodigosPostales.objects.get(id_codigo_postal=request.GET['eliminar'])
                    codigo.delete()
                    messages.success(request, "Código eliminado correctamente.")
                except CodigosPostales.DoesNotExist:
                    messages.error(request, f"No se encontró el código con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_cp')

            if request.method == 'POST' and 'editar' not in request.GET:
                codigo_valor = request.POST.get('codigo')  # Cambiado de 'nombre' a 'codigo'
                id_colonia = request.POST.get('id_colonia')
                id_municipio = request.POST.get('id_municipio')
                id_estado = request.POST.get('id_estado')

                # Validar campos obligatorios
                errors = []
                if not codigo_valor:
                    errors.append("El código postal es obligatorio.")
                if not id_colonia:
                    errors.append("La colonia es obligatoria.")
                if len(codigo_valor) > 5:
                    errors.append("El código postal no puede exceder 5 caracteres.")

                if errors:
                    for error in errors:
                        messages.error(request, error)
                    return redirect('gentelella_page', page='cal_cp')

                try:
                    # Obtener instancias de modelos
                    colonia = Colonias.objects.get(id_colonia=id_colonia)
                    municipio = Municipios.objects.get(id_municipio=id_municipio) if id_municipio else None
                    estado = Estados.objects.get(id_estado=id_estado) if id_estado else None

                    # Crear el código postal
                    CodigosPostales.objects.create(
                        codigo=codigo_valor,
                        id_colonia=colonia,
                        id_municipio=municipio,
                        id_estado=estado
                    )
                    messages.success(request, "Código postal creado correctamente.")
                except Colonias.DoesNotExist:
                    messages.error(request, "La colonia seleccionada no existe.")
                except Municipios.DoesNotExist:
                    messages.error(request, "El municipio seleccionado no existe.")
                except Estados.DoesNotExist:
                    messages.error(request, "El estado seleccionado no existe.")
                except IntegrityError:
                    messages.error(request, "Ya existe un código postal con ese valor para la colonia seleccionada.")
                except ValueError as e:
                    messages.error(request, f"Error en los datos proporcionados: {str(e)}")
                return redirect('gentelella_page', page='cal_cp')

        # ================= EDITAR CÓDIGO POSTAL ===================
        elif page == "editar_cp":
            context['colonias'] = Colonias.objects.all()
            context['municipios'] = Municipios.objects.all()
            context['estados'] = Estados.objects.all()

            if 'editar' in request.GET:
                try:
                    codigo_editar = CodigosPostales.objects.get(id_codigo_postal=request.GET['editar'])
                    context['codigo_editar'] = codigo_editar
                except CodigosPostales.DoesNotExist:
                    messages.error(request, f"No se encontró el código con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_cp')

            if request.method == 'POST':
                id_codigo_postal = request.POST.get('id_codigo_postal')
                codigo_valor = request.POST.get('codigo')
                id_colonia = request.POST.get('id_colonia')
                id_municipio = request.POST.get('id_municipio')
                id_estado = request.POST.get('id_estado')

                try:
                    codigo_postal = CodigosPostales.objects.get(id_codigo_postal=id_codigo_postal)
                    if codigo_valor and id_colonia and id_municipio and id_estado:
                        colonia = Colonias.objects.get(id_colonia=id_colonia)
                        municipio = Municipios.objects.get(id_municipio=id_municipio)
                        estado = Estados.objects.get(id_estado=id_estado)

                        codigo_postal.codigo = codigo_valor
                        codigo_postal.id_colonia = colonia
                        codigo_postal.id_municipio = municipio
                        codigo_postal.id_estado = estado
                        codigo_postal.save()
                        messages.success(request, "Código postal actualizado correctamente.")
                        return redirect('gentelella_page', page='cal_cp')
                    else:
                        messages.error(request, "Faltan datos para actualizar el código.")
                except (CodigosPostales.DoesNotExist, Colonias.DoesNotExist, Municipios.DoesNotExist, Estados.DoesNotExist):
                    messages.error(request, "Datos inválidos.")
                except IntegrityError:
                    messages.error(request, "Ya existe un código con ese valor.")
                return redirect('gentelella_page', page='editar_cp', editar=id_codigo_postal)

        # ================= PROPIEDADES ===================
        elif page == "cal_estimaciones":
            propiedades = Propiedades.objects.select_related('id_estado', 'id_municipio', 'id_colonia', 'id_codigo_postal').all()
            context['propiedades'] = propiedades
            context['estados'] = Estados.objects.all()
            context['municipios'] = Municipios.objects.all()
            context['colonias'] = Colonias.objects.all()
            context['codigos_postales'] = CodigosPostales.objects.all()

            # Eliminar propiedad
            if 'eliminar' in request.GET:
                try:
                    propiedad = Propiedades.objects.get(id_propiedad=request.GET['eliminar'])
                    propiedad.delete()
                    messages.success(request, "Propiedad eliminada correctamente.")
                except Propiedades.DoesNotExist:
                    messages.error(request, f"No se encontró la propiedad con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_estimaciones')

            # Crear propiedad
            if request.method == 'POST' and 'editar' not in request.GET:
                try:
                    nueva = Propiedades(
                        tipo_propiedad=request.POST.get('tipo_propiedad'),
                        calle=request.POST.get('calle'),
                        id_estado_id=request.POST.get('id_estado'),
                        id_municipio_id=request.POST.get('id_municipio'),
                        id_colonia_id=request.POST.get('id_colonia'),
                        id_codigo_postal_id=request.POST.get('id_codigo_postal'),
                        recamaras=int(request.POST.get('recamaras', 0)),
                        sanitarios=float(request.POST.get('sanitarios', 0)),
                        estacionamiento=int(request.POST.get('estacionamiento', 0)),
                        terreno=request.POST.get('terreno') or 0,
                        construccion=request.POST.get('construccion') or 0,
                        estado_conservacion=request.POST.get('estado_conservacion') or "",
                        comentarios=request.POST.get('comentarios') or "",
                        valor_aprox=request.POST.get('valor_aprox') or None,
                        valor_judicial=request.POST.get('valor_judicial') or None,
                        valor_comercial=request.POST.get('valor_comercial') or None,
                        valor_inicial=request.POST.get('valor_inicial') or None,
                    )
                    nueva.save()
                    messages.success(request, "Propiedad creada correctamente.")
                except Exception as e:
                    messages.error(request, f"Error al crear la propiedad: {str(e)}")
                return redirect('gentelella_page', page='cal_estimaciones')

            # Generar reporte PDF de todas las propiedades
            if 'generar_reporte_todos' in request.GET:
                print("Generando reporte de todas las propiedades...")
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="reporte_todas_propiedades.pdf"'
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="Reporte de Todas las Propiedades", ln=True, align='C')
                for prop in propiedades:
                    pdf.cell(200, 10, txt=f"ID: {prop.id_propiedad} - Tipo: {prop.tipo_propiedad} - Calle: {prop.calle}", ln=True)
                response.write(pdf.output(dest='S').encode('latin-1'))
                print("Reporte generado exitosamente.")
                return response

            # Generar reporte PDF de una propiedad individual
            if 'generar_reporte_individual' in request.GET and 'id_propiedad' in request.GET:
                print(f"Generando reporte individual para propiedad ID: {request.GET['id_propiedad']}")
                try:
                    propiedad_id = request.GET['id_propiedad']
                    propiedad = Propiedades.objects.get(id_propiedad=propiedad_id)
                    response = HttpResponse(content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="reporte_propiedad_{propiedad_id}.pdf"'
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt=f"Reporte de Propiedad ID: {propiedad.id_propiedad}", ln=True, align='C')
                    pdf.cell(200, 10, txt=f"Tipo: {propiedad.tipo_propiedad}", ln=True)
                    pdf.cell(200, 10, txt=f"Calle: {propiedad.calle}", ln=True)
                    response.write(pdf.output(dest='S').encode('latin-1'))
                    print(f"Reporte individual generado para ID: {propiedad_id}")
                    return response
                except Propiedades.DoesNotExist:
                    messages.error(request, f"No se encontró la propiedad con ID {propiedad_id}.")
                    return redirect('gentelella_page', page='cal_estimaciones')

        # ================= EDITAR ESTIMACIÓN ===================
        elif page == "editar_estimacion":
            if 'editar' in request.GET:
                try:
                    propiedad_editar = Propiedades.objects.get(id_propiedad=request.GET['editar'])
                    context['propiedad_editar'] = propiedad_editar
                    context['estados'] = Estados.objects.all()
                    context['municipios'] = Municipios.objects.all()
                    context['colonias'] = Colonias.objects.all()
                    context['codigos_postales'] = CodigosPostales.objects.all()
                except Propiedades.DoesNotExist:
                    messages.error(request, f"No se encontró la propiedad con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_estimaciones')

            if request.method == 'POST':
                try:
                    id_propiedad = request.POST.get('id_propiedad')
                    propiedad = Propiedades.objects.get(id_propiedad=id_propiedad)

                    # Obtener instancias de los modelos relacionados usando los IDs
                    id_estado = request.POST.get('id_estado')
                    id_municipio = request.POST.get('id_municipio')
                    id_colonia = request.POST.get('id_colonia')
                    id_codigo_postal = request.POST.get('id_codigo_postal')

                    propiedad.tipo_propiedad = request.POST.get('tipo_propiedad')
                    propiedad.calle = request.POST.get('calle')
                    propiedad.id_estado = Estados.objects.get(id_estado=id_estado) if id_estado else None
                    propiedad.id_municipio = Municipios.objects.get(id_municipio=id_municipio) if id_municipio else None
                    propiedad.id_colonia = Colonias.objects.get(id_colonia=id_colonia) if id_colonia else None
                    propiedad.id_codigo_postal = CodigosPostales.objects.get(id_codigo_postal=id_codigo_postal) if id_codigo_postal else None
                    propiedad.recamaras = int(request.POST.get('recamaras', 0))
                    propiedad.sanitarios = float(request.POST.get('sanitarios', 0))
                    propiedad.estacionamiento = int(request.POST.get('estacionamiento', 0))
                    propiedad.terreno = request.POST.get('terreno') or 0
                    propiedad.construccion = request.POST.get('construccion') or 0
                    propiedad.estado_conservacion = request.POST.get('estado_conservacion') or ""
                    propiedad.comentarios = request.POST.get('comentarios') or ""
                    propiedad.valor_aprox = request.POST.get('valor_aprox') or None
                    propiedad.valor_judicial = request.POST.get('valor_judicial') or None
                    propiedad.valor_comercial = request.POST.get('valor_comercial') or None
                    propiedad.valor_inicial = request.POST.get('valor_inicial') or None

                    propiedad.save()
                    messages.success(request, "Propiedad actualizada correctamente.")
                    return redirect('gentelella_page', page='cal_estimaciones')
                except Propiedades.DoesNotExist:
                    messages.error(request, f"No se encontró la propiedad con ID {id_propiedad}.")
                except Estados.DoesNotExist:
                    messages.error(request, "Estado no encontrado.")
                except Municipios.DoesNotExist:
                    messages.error(request, "Municipio no encontrado.")
                except Colonias.DoesNotExist:
                    messages.error(request, "Colonia no encontrada.")
                except CodigosPostales.DoesNotExist:
                    messages.error(request, "Código postal no encontrado.")
                except Exception as e:
                    messages.error(request, f"Error al actualizar la propiedad: {str(e)}")
                return redirect('gentelella_page', page='editar_estimacion', editar=id_propiedad)

        # ================= USUARIOS ===================
        elif page == "cal_usuarios":
            try:
                usuarios = User.objects.all()
                print(f"DEBUG: Usuarios recuperados: {list(usuarios)}")
                print(f"DEBUG: Número de usuarios: {usuarios.count()}")
            except Exception as e:
                print(f"DEBUG: Error al recuperar usuarios: {str(e)}")
                usuarios = []

            if 'eliminar' in request.GET:
                try:
                    usuario = User.objects.get(id=request.GET['eliminar'])
                    usuario.delete()
                    messages.success(request, "Usuario eliminado correctamente.")
                except User.DoesNotExist:
                    messages.error(request, f"No se encontró el usuario con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_usuarios')

            if request.method == 'POST' and 'editar' not in request.GET:
                username = request.POST.get('username')
                first_name = request.POST.get('nombre')
                email = request.POST.get('email')
                password1 = request.POST.get('password1')
                password2 = request.POST.get('password2')

                if username and first_name and email and password1 and password2:
                    if password1 == password2:
                        try:
                            User.objects.create(
                                username=username,
                                first_name=first_name,
                                email=email,
                                password=make_password(password1),
                                is_active=True,
                                date_joined=timezone.now()
                            )
                            messages.success(request, "Usuario creado correctamente.")
                        except IntegrityError:
                            messages.error(request, "El nombre de usuario o correo ya existe.")
                    else:
                        messages.error(request, "Las contraseñas no coinciden.")
                else:
                    messages.error(request, "Faltan datos para crear el usuario.")

                return redirect('gentelella_page', page='cal_usuarios')

            context.update({
                'usuarios': usuarios,
            })
            print(f"DEBUG: Contexto enviado: {context}")

        # ================= EDITAR USUARIO ===================
        elif page == "editar_usuario":
            if 'editar' in request.GET:
                try:
                    usuario_editar = User.objects.get(id=request.GET['editar'])
                    context['usuario_editar'] = usuario_editar
                except User.DoesNotExist:
                    messages.error(request, f"No se encontró el usuario con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_usuarios')

            if request.method == 'POST':
                id_usuario = request.POST.get('id_usuario')
                try:
                    usuario = User.objects.get(id=id_usuario)
                    username = request.POST.get('username')
                    first_name = request.POST.get('nombre')
                    email = request.POST.get('email')
                    password1 = request.POST.get('password1')
                    password2 = request.POST.get('password2')

                    if username and first_name and email:
                        usuario.username = username
                        usuario.first_name = first_name
                        usuario.email = email
                        if password1 and password2 and password1 == password2:
                            usuario.password = make_password(password1)
                        elif password1 or password2:
                            messages.error(request, "Las contraseñas no coinciden o están incompletas.")
                            return redirect('gentelella_page', page='editar_usuario', editar=id_usuario)
                        usuario.save()
                        messages.success(request, "Usuario actualizado correctamente.")
                        return redirect('gentelella_page', page='cal_usuarios')
                    else:
                        messages.error(request, "Faltan datos para actualizar el usuario.")
                except User.DoesNotExist:
                    messages.error(request, f"No se encontró el usuario con ID {id_usuario}.")
                except IntegrityError:
                    messages.error(request, "El nombre de usuario o correo ya existe.")
                return redirect('gentelella_page', page='editar_usuario', editar=id_usuario)

        # ================= INDEX (Dashboard) ===================
        elif page == 'index':
            # Contadores para el dashboard
            total_usuarios = User.objects.count()
            total_estados = Estados.objects.count()
            total_municipios = Municipios.objects.count()
            total_colonias = Colonias.objects.count()
            total_cp = CodigosPostales.objects.count()
            total_propiedades = Propiedades.objects.count()

            # Gráfico: Estados con más municipios
            estados_municipios = Estados.objects.annotate(
                total=Count('municipios')  # Usa 'municipios' si tienes related_name
            ).order_by('-total')[:10]

            estados = [e.nombre for e in estados_municipios]
            totales = [e.total for e in estados_municipios]

            # Generar gráfico con Matplotlib
            plt.figure(figsize=(8, 4))
            plt.barh(estados, totales, color='skyblue')
            plt.title('Top Estados con Más Municipios')
            plt.xlabel('Cantidad de Municipios')
            plt.tight_layout()
            plt.gca().invert_yaxis()

            # Guardar gráfico en memoria
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            grafico_base64 = base64.b64encode(image_png).decode('utf-8')
            plt.close()

            # Actualizar contexto
            context.update({
                'total_usuarios': total_usuarios,
                'total_estados': total_estados,
                'total_municipios': total_municipios,
                'total_colonias': total_colonias,
                'total_cp': total_cp,
                'total_propiedades': total_propiedades,
                'grafico_base64': grafico_base64,
            })

        # Renderizar la plantilla correspondiente
        return render(request, f'gentelella/{page}.html', context)

    except Exception as e:
        print(f"Error: {str(e)}")
        messages.error(request, f"Error inesperado: {str(e)}")
        return render(request, 'gentelella/page_404.html', status=404)
    
#Vista para la documentación 

def vista_documentacion(request):
    return render(request, 'documentacion/doc.html')