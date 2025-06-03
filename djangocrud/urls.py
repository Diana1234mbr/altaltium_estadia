from django.contrib import admin
from django.urls import path
from tasks import views

urlpatterns = [
    path('estimaciones/', views.estimaciones, name='estimaciones'),
    path('admin/', admin.site.urls),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='signout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('', views.welcome, name='welcome'),
    path('admin-panel/<str:page>/', views.gentelella_view, name='gentelella_page'),
    path('benito/', views.vista_benito_juarez, name='benito'),
    path('alvaro/', views.vista_alvaro, name='alvaro'),
    path('coyoacan/', views.vista_coyoacan, name='coyoacan'),
    path('xochimilco/', views.vista_xochimilco, name='xochimilco'),
    path('azcapotzalco/', views.vista_azcapotzalco, name='azcapotzalco'),
    path('cuajimalpa/', views.vista_cuajimalpa, name='cuajimalpa'),
    path('cuauhtemoc/', views.vista_cuauhtemoc, name='cuauhtemoc'),
    path('miguel/', views.vista_miguel, name='miguel'),
    path('gustavo/', views.vista_gustavo, name='gustavo'),
    path('iztacalco/', views.vista_iztacalco, name='iztacalco'),
    path('iztapalapa/', views.vista_iztapalapa, name='iztapalapa'),
    path('magda/', views.vista_magda, name='magda'),
    path('milpa/', views.vista_milpa, name='milpa'),
    path('tlahuac/', views.vista_tlahuac, name='tlahuac'),
    path('tlalpan/', views.vista_tlalpan, name='tlalpan'),
    path('venustiano/', views.vista_venustiano, name='venustiano'),
    path('obtener_colonias/', views.obtener_colonias, name='obtener_colonias'),
    path('obtener_codigos_postales/', views.obtener_codigos_postales, name='obtener_codigos_postales'),

    path('colonias/', views.gentelella_view, {'page': 'cal_colonia'}, name='colonias_list'),
    path('colonias/editar/', views.gentelella_view, {'page': 'editar_colonia'}, name='editar_colonia'),

]