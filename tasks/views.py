from django.db.models import Avg
from django.urls import reverse
from fpdf import FPDF
from django.db.models import Count
from io import BytesIO
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.db import IntegrityError, connection
from django.http import Http404, JsonResponse, HttpResponse
from .models import Estados, Municipios, Colonias, CodigosPostales, AlcaldiaVistas, Propiedades, GraficaAlcaldia, Usuarios
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.cache import never_cache
import json
import matplotlib
matplotlib.use('Agg')  # ← Usa un backend que NO requiere interfaz gráfica
import matplotlib.pyplot as plt
import os
import base64
import io

# Decorador para verificar si es admin
@never_cache
def admin_required(usuario):
    return usuario.is_staff or usuario.is_superuser

# Registro de usuarios
@never_cache
def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html')
    else:
        if request.POST["password1"] == request.POST["password2"]:
            try:
                nuevo_usuario = Usuarios(
                    username=request.POST["username"],
                    password=request.POST["password1"],  # ⚠️ Texto plano
                    email=request.POST["email"],
                    first_name=request.POST["nombre"],
                    last_name=request.POST.get("apellido", ""),  # opcional
                    is_staff=0,
                    is_superuser=0,
                    is_active=1
                )
                nuevo_usuario.save()
                # Aquí puedes hacer login manual si lo deseas
                return redirect('signin')
            except IntegrityError:
                return render(request, 'signup.html', {
                    "error": "El nombre de usuario ya existe."
                })
        return render(request, 'signup.html', {
            "error": "Las contraseñas no coinciden."
        })


# Estimaciones de propiedades
@never_cache
def estimaciones(request):    
    usuario = None
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            usuario = None    
    
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
                'Muy bueno': 0.08500,
                'Bueno': 1,
                'Regular': 0.08500,
                'Malo': 0.13000,
                'Muy malo': 0.25000
            }

            # Cálculo 1: valor inicial
            valor_inicial = precio_promedio * construccion

            # Cálculo 2: aplicar coeficiente
            coef = coef_conservacion.get(estado_conservacion, 1)
            valor_aprox = valor_inicial * coef if estado_conservacion != 'Bueno' else valor_inicial

            # Cálculo 3: valor comercial
            if estado_conservacion == 'Muy bueno':
                valor_comercial = valor_inicial + valor_aprox
            elif estado_conservacion == 'Muy malo':
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
            return redirect('mostrar_resultado', propiedad_id=propiedad.id_propiedad)


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


    # Generar reporte PDF de una propiedad individual
    if 'generar_reporte_individual' in request.GET and 'id_propiedad' in request.GET:
        print(f"Generando reporte individual para propiedad ID: {request.GET['id_propiedad']}")
        try:            
            propiedad_id = request.GET['id_propiedad']
            propiedad = Propiedades.objects.get(id_propiedad=propiedad_id)

            response = HttpResponse(pdf_output, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="reporte_propiedad_{propiedad_id}.pdf"'
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Título centrado
            pdf.set_font("Arial", 'B', size=14)  # 'B' para negrita
            pdf.cell(200, 10, txt=f"Reporte de Propiedad ID: {propiedad.id_propiedad}", ln=True, align='C')
            pdf.ln(10)  # Salto de línea

            # Configuración de la tabla
            pdf.set_font("Arial", size=10)
            pdf.set_fill_color(200, 220, 255)  # Color de fondo para el encabezado
            pdf.set_text_color(0, 0, 0)  # Color del texto (negro)

            # Encabezados de la tabla
            pdf.cell(50, 10, 'Campo', 1, 0, 'C', 1)  # Ancho 50, alto 10, borde 1, sin salto de línea, centrado, fondo relleno
            pdf.cell(150, 10, 'Valor', 1, 1, 'C', 1)  # Ancho 150, salto de línea
            pdf.set_fill_color(255, 255, 255)  # Color de fondo para las filas de datos (blanco)

            # Datos de la tabla
            pdf.cell(50, 10, 'Valor Comercial', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.valor_comercial or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Valor Judicial', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.valor_judicial or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Calle', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.calle or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Colonia', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.id_colonia or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Municipio', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.id_municipio or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Estado', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.id_estado or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Recámaras', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.recamaras or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Tipo de Propiedad', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.tipo_propiedad or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Sanitarios', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.sanitarios or "N/A"}', 1, 1, 'L')
            pdf.cell(50, 10, 'Valor Aproximado', 1, 0, 'L')
            pdf.cell(150, 10, f'{propiedad.valor_aprox or "N/A"}', 1, 1, 'L')
            

            # Generar el PDF
            response.write(pdf.output(dest='S'))
            print(f"Reporte individual generado para ID: {propiedad_id}")
            return response
        except Propiedades.DoesNotExist:
            print(f"No se encontró la propiedad con ID: {propiedad_id}")
            return HttpResponse("Propiedad no encontrada", status=404)
        except Exception as e:
            print(f"Error al generar el reporte: {str(e)}")
            return HttpResponse(f"Error: {str(e)}", status=500)







    # Si es GET, mostrar formulario
    context = {
        'estados': Estados.objects.all(),
        'municipios': Municipios.objects.all(),
        'colonias': Colonias.objects.all(),
        'codigos_postales': CodigosPostales.objects.all(),
        'propiedades': Propiedades.objects.all(),
        'datos_alcaldia': AlcaldiaVistas.objects.all(),
        'usuario': usuario,
    }
    return render(request, 'estimaciones.html', context)



def mostrar_resultado(request, propiedad_id):
    try:
        propiedad = Propiedades.objects.get(id_propiedad=propiedad_id)
        return render(request, 'resultados_estimaciones.html', {'propiedad': propiedad})
    except Propiedades.DoesNotExist:
        messages.error(request, "La propiedad no existe.")
        return redirect('estimaciones')  # O a donde necesites


# Inicio de sesión
@never_cache
def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html')

    input_value = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()    

    user_obj = None
    try:
        user_obj = Usuarios.objects.get(username=input_value)
    except Usuarios.DoesNotExist:
        try:
            user_obj = Usuarios.objects.get(email=input_value)
        except Usuarios.DoesNotExist:
            user_obj = None

    if user_obj and user_obj.password == password and user_obj.is_active:
        request.session['usuario_id'] = user_obj.id
        

        if user_obj.is_staff or user_obj.is_superuser:
            return redirect('gentelella_page', page='index')  # Dashboard admin
        else:
            return redirect('welcome')

    return render(request, 'signin.html', {
        "error": "Usuario o contraseña incorrectos."
    })



# Cerrar sesión
@never_cache
def signout(request):
    logout(request)
    return redirect('signin')


@never_cache
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
@never_cache
def forgot_password(request):
    return render(request, 'forgotpassword.html')

# Página de bienvenida
@never_cache
def welcome(request):
    usuario_id = request.session.get('usuario_id')
    usuario = None

    if usuario_id:
        try:                        
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            usuario = None

    images_auth = ["casa5.png", "casa6.png", "casa1.png", "casa2.png", "casa3.png", "casa4.png"]
    images_guest = ["Altatium.png", "forbes.png"]

    context = {
        "usuario": usuario,
        "images_auth": images_auth,
        "images_guest": images_guest,
    }

    return render(request, "welcome.html", context)



# Vistas de alcaldías
@never_cache
def vista_benito_juarez(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Benito Juárez')
    return render(request, 'alcaldias/benito.html', {'datos': datos})

@never_cache
def vista_alvaro(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Álvaro Obregón')
    return render(request, 'alcaldias/alvaro.html', {'datos': datos})

@never_cache
def vista_coyoacan(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Coyoacán')
    return render(request, 'alcaldias/coyoacan.html', {'datos': datos})

@never_cache
def vista_xochimilco(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Xochimilco')
    return render(request, 'alcaldias/xochimilco.html', {'datos': datos})

@never_cache
def vista_azcapotzalco(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Azcapotzalco')
    return render(request, 'alcaldias/azcapotzalco.html', {'datos': datos})

@never_cache
def vista_cuajimalpa(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Cuajimalpa de Morelos')
    return render(request, 'alcaldias/cuajimalpa.html', {'datos': datos})

@never_cache
def vista_cuauhtemoc(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Cuauhtémoc')
    return render(request, 'alcaldias/cuauhtemoc.html', {'datos': datos})

@never_cache
def vista_miguel(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Miguel Hidalgo')
    return render(request, 'alcaldias/miguel.html', {'datos': datos})

@never_cache
def vista_gustavo(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Gustavo A. Madero')
    return render(request, 'alcaldias/gustavo.html', {'datos': datos})

@never_cache
def vista_iztacalco(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Iztacalco')
    return render(request, 'alcaldias/iztacalco.html', {'datos': datos})

@never_cache
def vista_iztapalapa(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Iztapalapa')
    return render(request, 'alcaldias/iztapalapa.html', {'datos': datos})

@never_cache
def vista_magda(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='La Magdalena Contreras')
    return render(request, 'alcaldias/magda.html', {'datos': datos})

@never_cache
def vista_milpa(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Milpa Alta')
    return render(request, 'alcaldias/milpa.html', {'datos': datos})

@never_cache
def vista_tlahuac(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Tláhuac')
    return render(request, 'alcaldias/tlahuac.html', {'datos': datos})

@never_cache
def vista_tlalpan(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Tlalpan')
    return render(request, 'alcaldias/tlalpan.html', {'datos': datos})

@never_cache
def vista_venustiano(request):
    datos = AlcaldiaVistas.objects.filter(alcaldia__iexact='Venustiano Carranza')
    return render(request, 'alcaldias/venustiano.html', {'datos': datos})





# Obtener colonias por municipio (AJAX)
@never_cache
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
@never_cache
def obtener_municipios(request):
    estado_id = request.GET.get('estado_id')
    if not estado_id:
        return JsonResponse({'error': 'ID de estado no proporcionado'}, status=400)
    try:
        municipios = Municipios.objects.filter(id_estado=estado_id).values('id_municipio', 'nombre')
        return JsonResponse(list(municipios), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@never_cache
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
@never_cache
def gentelella_view(request, page):
        usuario_id = request.session.get('usuario_id')

        if not usuario_id:
            return redirect('signin')

        context = {}

        try:
            usuario = Usuarios.objects.get(id=usuario_id)
            context['usuario'] = usuario
        except Usuarios.DoesNotExist:
            return redirect('signin')
        except Exception as e:
            print(f"Error: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'gentelella/page_404.html', context, status=404)

        if not (usuario.is_staff or usuario.is_superuser):
            return HttpResponse("No tienes permisos para acceder al panel admin.", status=403)

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

                        # Verificar si ya existe una colonia con ese nombre y municipio
                        if Colonias.objects.filter(nombre=nombre, id_municipio=municipio).exists():
                            messages.error(request, "Ya existe una colonia con ese nombre en el municipio seleccionado.")
                        else:
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
                else:
                    messages.error(request, "Faltan datos para crear la colonia.")

                return redirect('gentelella_page', page='cal_colonia')

            context.update({
                'colonias': colonias,
                'municipios': municipios,
                'estados': estados,
            })

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

                        # Verificar si ya existe otra colonia con ese nombre y municipio
                        if Colonias.objects.filter(nombre=nombre, id_municipio=municipio).exclude(id_colonia=colonia.id_colonia).exists():
                            messages.error(request, "Ya existe una colonia con ese nombre en el municipio seleccionado.")
                        else:
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
                except Estados.DoesNotExist:
                    messages.error(request, "Estado no encontrado.")
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
                nombre = request.POST.get('nombre', '').strip()
                if nombre:
                    try:
                        # Validación manual de duplicado
                        if Estados.objects.filter(nombre__iexact=nombre).exists():
                            messages.error(request, "Ya existe un estado con ese nombre.")
                        else:
                            Estados.objects.create(nombre=nombre)
                            messages.success(request, "Estado creado correctamente.")
                    except IntegrityError:
                        messages.error(request, "Error de integridad al crear el estado.")
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
                nombre = request.POST.get('nombre', '').strip()
                try:
                    estado = Estados.objects.get(id_estado=id_estado)
                    if nombre:
                        # Validación manual de duplicado, excluyendo el mismo registro
                        if Estados.objects.filter(nombre__iexact=nombre).exclude(id_estado=estado.id_estado).exists():
                            messages.error(request, "Ya existe un estado con ese nombre.")
                        else:
                            estado.nombre = nombre
                            estado.save()
                            messages.success(request, "Estado actualizado correctamente.")
                            return redirect('gentelella_page', page='cal_estado')
                    else:
                        messages.error(request, "El nombre del estado no puede estar vacío.")
                except Estados.DoesNotExist:
                    messages.error(request, f"No se encontró el estado con ID {id_estado}.")
                except IntegrityError:
                    messages.error(request, "Error de integridad al actualizar el estado.")
                return redirect(f"{reverse('gentelella_page', kwargs={'page': 'editar_usuario'})}?editar={id_usuario}")


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

                        # Validar duplicado (nombre + estado)
                        if Municipios.objects.filter(nombre__iexact=nombre.strip(), id_estado=estado).exists():
                            messages.error(request, "Ya existe un municipio con ese nombre en el estado seleccionado.")
                        else:
                            Municipios.objects.create(nombre=nombre.strip(), id_estado=estado)
                            messages.success(request, "Municipio creado correctamente.")
                    except Estados.DoesNotExist:
                        messages.error(request, "Estado no encontrado.")
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

                        # Validar duplicado, excluyendo el actual
                        if Municipios.objects.filter(nombre__iexact=nombre.strip(), id_estado=estado).exclude(id_municipio=municipio.id_municipio).exists():
                            messages.error(request, "Ya existe un municipio con ese nombre en el estado seleccionado.")
                        else:
                            municipio.nombre = nombre.strip()
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
                return redirect('gentelella_page', page='editar_municipio', editar=id_municipio)
        # ================= CÓDIGOS POSTALES ===================
        elif page == "cal_cp":
            codigos = CodigosPostales.objects.select_related('id_colonia', 'id_municipio', 'id_estado').all()
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
                codigo_valor = request.POST.get('codigo')
                id_colonia = request.POST.get('id_colonia')
                id_municipio = request.POST.get('id_municipio')
                id_estado = request.POST.get('id_estado')

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
                    colonia = Colonias.objects.get(id_colonia=id_colonia)
                    municipio = Municipios.objects.get(id_municipio=id_municipio) if id_municipio else None
                    estado = Estados.objects.get(id_estado=id_estado) if id_estado else None

                    # 🔐 Validación para evitar duplicados
                    if CodigosPostales.objects.filter(codigo=codigo_valor, id_colonia=colonia).exists():
                        messages.error(request, "Ya existe un código postal con ese valor para la colonia seleccionada.")
                        return redirect('gentelella_page', page='cal_cp')

                    # ✅ Si no existe, lo crea
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

            # Eliminar una propiedad individual
            if 'eliminar_individual' in request.GET and 'id_propiedad' in request.GET:
                try:
                    propiedad_id = request.GET['id_propiedad']
                    propiedad = Propiedades.objects.get(id_propiedad=propiedad_id)
                    propiedad.delete()
                    messages.success(request, f"Propiedad con ID {propiedad_id} eliminada correctamente.")
                except Propiedades.DoesNotExist:
                    messages.error(request, f"No se encontró la propiedad con ID {propiedad_id}.")
                except Exception as e:
                    messages.error(request, f"Error al eliminar la propiedad: {str(e)}")
                return redirect('gentelella_page', page='cal_estimaciones')

            # Eliminar todas las propiedades y reiniciar los IDs
           # Eliminar todas las propiedades y reiniciar los IDs
            if 'eliminar' in request.GET:
                try:
                    # Eliminar todos los registros
                    Propiedades.objects.all().delete()
                    # Reiniciar la secuencia de IDs (esto depende de la base de datos)
                    with connection.cursor() as cursor:
                        cursor.execute("ALTER TABLE propiedades AUTO_INCREMENT = 1")
                    messages.success(request, "Todas las propiedades han sido eliminadas y los IDs reiniciados a 1")
                except Exception as e:
                    messages.error(request, f"Error al eliminar propiedades o reiniciar IDs: {str(e)}")
                return redirect('gentella_page', page='cal_estimaciones')   
                
                # Generar reporte PDF de una propiedad individual con diseño limpio y completo
        if 'generar_reporte_individual' in request.GET and 'id_propiedad' in request.GET:
            print(f"Generando reporte individual para propiedad ID: {request.GET['id_propiedad']}")
            try:
                propiedad_id = request.GET['id_propiedad']
                propiedad = Propiedades.objects.get(id_propiedad=propiedad_id)

                usuario = request.user if request.user.is_authenticated else None
                usuario_nombre = usuario.username if usuario else "Usuario invitado"
                usuario_correo = usuario.email if usuario else "correo@invitado.com"

                pdf = FPDF(orientation='L')  # Orientación horizontal (Landscape)
                pdf.add_page()
                pdf.set_auto_page_break(False)  # Desactivar salto de página automático

                # Encabezado con logo, empresa, usuario y correo
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
                if os.path.exists(logo_path):
                    pdf.image(logo_path, x=120, y=10, w=40)  # Logo a la derecha
                pdf.set_xy(10, 10)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(100, 8, "Altaltium Real Estate Solutions", ln=True, align='L')
                pdf.set_font("Arial", '', 10)
                pdf.cell(100, 6, f"Usuario: {usuario_nombre}", ln=True, align='L')
                pdf.cell(100, 6, f"Correo: {usuario_correo}", ln=True, align='L')
                pdf.ln(5)

                # Valores aproximados a la izquierda
                pdf.set_xy(10, 40)
                pdf.set_font("Arial", '', 10)
                pdf.cell(90, 6, f"Valor Comercial Aproximado: ${propiedad.valor_comercial or 'N/A'}", ln=True, align='L')
                pdf.cell(90, 6, f"Valor Judicial Aproximado: ${propiedad.valor_judicial or 'N/A'}", ln=True, align='L')

                # Mapa a la derecha
                mapa_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'mapa.png')
                if os.path.exists(mapa_path):
                    pdf.image(mapa_path, x=110, y=30, w=180)  # Mapa a la derecha, ajustado

                # Título principal (arriba de los valores)
                pdf.set_xy(10, 25)
                pdf.set_text_color(0, 66, 156)  # Azul rey
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Resultados de Estimación de Propiedad", ln=True, align='C')
                pdf.ln(15)

                # Descripción del Inmueble
                pdf.set_xy(10, 90)
                pdf.set_text_color(0, 66, 156)  # Azul rey
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "Descripción del Inmueble", ln=True)
                pdf.ln(10)

                # Dirección
                pdf.set_xy(10, 110)
                pdf.set_text_color(0, 66, 156)  # Azul rey
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(90, 8, "Dirección", ln=True, align='L')
                pdf.set_text_color(0, 0, 0)  # Volver a negro
                pdf.set_font("Arial", '', 10)
                pdf.set_x(10)
                pdf.cell(90, 6, "Calle:", ln=True)
                pdf.cell(90, 6, f"{propiedad.calle or 'ww'}", ln=True)
                pdf.cell(90, 6, "Colonia:", ln=True)
                pdf.cell(90, 6, f"{propiedad.id_colonia.nombre if propiedad.id_colonia else 'Sin colonia'}", ln=True)
                pdf.cell(90, 6, "Delegación:", ln=True)
                pdf.cell(90, 6, f"{propiedad.id_municipio.nombre if propiedad.id_municipio else 'Sin municipio'}", ln=True)
                pdf.cell(90, 6, "Estado:", ln=True)
                pdf.cell(90, 6, f"{propiedad.id_estado.nombre if propiedad.id_estado else 'Sin estado'}", ln=True)

                # Características
                pdf.set_xy(110, 110)
                pdf.set_text_color(0, 66, 156)  # Azul rey
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(90, 8, "Características", ln=True, align='L')
                pdf.set_text_color(0, 0, 0)  # Volver a negro
                pdf.set_font("Arial", '', 10)
                pdf.set_x(110)
                pdf.cell(90, 6, "Terreno:", ln=True)
                pdf.cell(90, 6, f"{propiedad.terreno or '12.00'} m2", ln=True)
                pdf.cell(90, 6, "Construcción:", ln=True)
                pdf.cell(90, 6, f"{propiedad.construccion or 'N/A'} m2", ln=True)
                pdf.cell(90, 6, "Recámaras:", ln=True)
                pdf.cell(90, 6, f"{propiedad.recamaras or 'N/A'}", ln=True)
                pdf.cell(90, 6, "Sanitarios:", ln=True)
                pdf.cell(90, 6, f"{propiedad.sanitarios or 'N/A'}", ln=True)
                pdf.cell(90, 6, "Estacionamiento:", ln=True)
                pdf.cell(90, 6, f"{propiedad.estacionamiento or 'N/A'}", ln=True)

                # Información adicional
                pdf.set_xy(210, 110)
                pdf.set_text_color(0, 66, 156)  # Azul rey
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(90, 8, "Información adicional", ln=True, align='L')
                pdf.set_text_color(0, 0, 0)  # Volver a negro
                pdf.set_font("Arial", '', 10)
                pdf.set_x(210)
                pdf.cell(90, 6, "Comentarios:", ln=True)
                pdf.cell(90, 6, f"{propiedad.comentarios or 'N/A'}", ln=True)
                pdf.cell(90, 6, "Estado de conservación:", ln=True)
                pdf.cell(90, 6, f"{propiedad.estado_conservacion or 'Muy bueno'}", ln=True)

                 # Obtener el PDF generado como bytes
                pdf_output = pdf.output(dest='S')

                # Crear la respuesta HTTP con el PDF
                response = HttpResponse(pdf_output, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="reporte_propiedad_{propiedad_id}.pdf"'
                
                print(f"Reporte individual generado para ID: {propiedad_id}")
                return response

            except Propiedades.DoesNotExist:
                print(f"No se encontró la propiedad con ID: {propiedad_id}")
                return HttpResponse("Propiedad no encontrada", status=404)

            except Exception as e:
                print(f"Error al generar el reporte: {str(e)}")
                return HttpResponse(f"Error: {str(e)}", status=500)

        # ================= USUARIOS ===================
        elif page == "cal_usuarios":
            try:
                usuarios = Usuarios.objects.all()
                print(f"DEBUG: Usuarios recuperados: {list(usuarios)}")
                print(f"DEBUG: Número de usuarios: {usuarios.count()}")
            except Exception as e:
                print(f"DEBUG: Error al recuperar usuarios: {str(e)}")
                usuarios = []

            if 'eliminar' in request.GET:
                try:
                    usuario = Usuarios.objects.get(id=request.GET['eliminar'])
                    usuario.delete()
                    messages.success(request, "Usuario eliminado correctamente.")
                except Usuarios.DoesNotExist:
                    messages.error(request, f"No se encontró el usuario con ID {request.GET['eliminar']}.")
                return redirect('gentelella_page', page='cal_usuarios')

            if request.method == 'POST' and 'editar' not in request.GET:
                username = request.POST.get('username')
                first_name = request.POST.get('nombre')
                roles = request.POST.get('roles')
                email = request.POST.get('email')
                password1 = request.POST.get('password1')
                password2 = request.POST.get('password2')

            

        # ================= EDITAR USUARIO ===================
        elif page == "editar_usuario":
            if 'editar' in request.GET:
                try:
                    usuario_editar = Usuarios.objects.get(id=request.GET['editar'])
                    context['usuario_editar'] = usuario_editar
                except Usuarios.DoesNotExist:
                    messages.error(request, f"No se encontró el usuario con ID {request.GET['editar']}.")
                    return redirect('gentelella_page', page='cal_usuarios')

            if request.method == 'POST':
                id_usuario = request.POST.get('id_usuario')
                try:
                    usuario = Usuarios.objects.get(id=id_usuario)
                    username = request.POST.get('username')
                    first_name = request.POST.get('nombre')
                    email = request.POST.get('email')
                    roles = request.POST.get('roles')  # ← campo roles aquí
                    password1 = request.POST.get('password1')
                    password2 = request.POST.get('password2')

                    if username and first_name and email:
                        usuario.username = username
                        usuario.first_name = first_name
                        usuario.email = email

                        # Guardar roles si se proporciona
                        if roles:
                            usuario.roles = roles

                        if password1 and password2 and password1 == password2:
                            usuario.password = password1
                        elif password1 or password2:
                            messages.error(request, "Las contraseñas no coinciden o están incompletas.")
                            return redirect('gentelella_page', page='editar_usuario', editar=id_usuario)

                        if 'profile_picture' in request.FILES:
                            usuario.profile_picture = request.FILES['profile_picture']

                        usuario.save()
                        messages.success(request, "Usuario actualizado correctamente.")
                        return redirect('gentelella_page', page='cal_usuarios')
            
                    else:
                        messages.error(request, "Faltan datos para actualizar el usuario.")
                except Usuarios.DoesNotExist:
                    messages.error(request, f"No se encontró el usuario con ID {id_usuario}.")
                except IntegrityError:
                    messages.error(request, "El nombre de usuario o correo ya existe.")
                return redirect('gentelella_page', page='editar_usuario', editar=id_usuario)
            

        # ---------VISTA ALCALDIAS--------- #
        elif page == "cal_vista_usuarios":
                try:
                    vistas = AlcaldiaVistas.objects.all()
                    print(f"DEBUG: Alcaldias recuperadas: {list(vistas)}")
                    print(f"DEBUG: Número de vista alcaldías: {vistas.count()}")
                except Exception as e:
                    print(f"DEBUG: Error al recuperar vistas: {str(e)}")
                    vistas = []
                    messages.error(request, f"Error al recuperar vistas: {str(e)}")

                if 'eliminar' in request.GET:
                    try:
                        vista = AlcaldiaVistas.objects.get(id=request.GET['eliminar'])
                        vista.delete()
                        messages.success(request, "Vista eliminada correctamente.")
                    except AlcaldiaVistas.DoesNotExist:
                        messages.error(request, f"No se encontró la vista con ID {request.GET['eliminar']}.")
                    return redirect('gentelella_page', page='cal_vista_usuarios')

                if request.method == 'POST' and 'editar' not in request.GET:
                    estado = request.POST.get('estado')
                    alcaldia = request.POST.get('alcaldia')
                    colonia = request.POST.get('colonia')
                    promedio_mxn = request.POST.get('promedio_mxn')
                    zona = request.POST.get('zona')

                    try:
                        promedio_mxn = float(promedio_mxn.replace('$', '').replace(',', ''))
                    except (ValueError, AttributeError):
                        messages.error(request, "Formato de promedio inválido. Use formato: $26,301")
                        return redirect('gentelella_page', page='cal_vista_usuarios')

                    if estado and alcaldia and colonia and promedio_mxn:
                        try:
                            AlcaldiaVistas.objects.create(
                                estado=estado,
                                alcaldia=alcaldia,
                                colonia=colonia,
                                promedio_mxn=promedio_mxn,
                                zona=zona if zona else None
                            )
                            messages.success(request, "Vista creada correctamente.")
                        except Exception as e:
                            messages.error(request, f"Error al crear vista: {str(e)}")
                    else:
                        messages.error(request, "Faltan datos obligatorios para crear la vista.")
                    return redirect('gentelella_page', page='cal_vista_usuarios')

                context.update({'vistas': vistas})
                return render(request, 'gentelella/cal_vista_usuarios.html', context)

            # ================= EDITAR VISTAS ALCALDÍAS ===================
        elif page == "editar_vistas_alcaldia":
                if 'editar' in request.GET:
                    try:
                        vista_editar = AlcaldiaVistas.objects.get(id=request.GET['editar'])
                        context['vista_editar'] = vista_editar
                    except AlcaldiaVistas.DoesNotExist:
                        messages.error(request, f"No se encontró la vista con ID {request.GET['editar']}.")
                        return redirect('gentelella_page', page='cal_vista_usuarios')

                if request.method == 'POST':
                    id_vista = request.POST.get('id')
                    try:
                        vista = AlcaldiaVistas.objects.get(id=id_vista)
                        estado = request.POST.get('estado')
                        alcaldia = request.POST.get('alcaldia')
                        colonia = request.POST.get('colonia')
                        promedio_mxn = request.POST.get('promedio_mxn')
                        zona = request.POST.get('zona')

                        try:
                            promedio_mxn = float(promedio_mxn.replace('$', '').replace(',', ''))
                        except (ValueError, AttributeError):
                            messages.error(request, "Formato de promedio inválido. Use formato: $26,301")
                            return redirect('gentelella_page', page='editar_vistas_alcaldia', editar=id_vista)

                        if estado and alcaldia and colonia and promedio_mxn:
                            vista.estado = estado
                            vista.alcaldia = alcaldia
                            vista.colonia = colonia
                            vista.promedio_mxn = promedio_mxn
                            vista.zona = zona if zona else None
                            vista.save()
                            messages.success(request, "Vista actualizada correctamente.")
                            return redirect('gentelella_page', page='cal_vista_usuarios')
                        else:
                            messages.error(request, "Faltan datos obligatorios para actualizar la vista.")
                    except AlcaldiaVistas.DoesNotExist:
                        messages.error(request, f"No se encontró la vista con ID {id_vista}.")
                    except Exception as e:
                        messages.error(request, f"Error al actualizar vista: {str(e)}")
                    return redirect('gentelella_page', page='editar_vistas_alcaldia', editar=id_vista)

        # ================= INDEX (Dashboard) ===================
        elif page == 'index':
            # Contadores para el dashboard
            total_usuarios = Usuarios.objects.count()
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

    
#Vista para la documentación 
@never_cache
def vista_documentacion(request):
    usuario_id = request.session.get('usuario_id')
    usuario = None

    if usuario_id:
        try:                        
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            usuario = None


    context = {
        'usuario': usuario,
        # otros datos si tienes
    }    
    return render(request, 'documentacion/doc.html', context)