from django.contrib import admin
from django.urls import path
from tasks import views

urlpatterns = [
    path('estimaciones/', views.estimaciones, name='estimaciones'),
    path('admin/', admin.site.urls),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('', views.welcome, name='welcome'),
    path('admin-panel/<str:page>/', views.gentelella_view, name='gentelella_page'),
    path('benito/', views.vista_benito_juarez, name='benito'),
    path('alvaro/', views.vista_alvaro, name='alvaro'),
    path('coyoacan/', views.vista_coyoacan, name='coyoacan'),
    path('xochimilco/', views.vista_xochimilco, name='xochimilco'),
    path('azcapotzalco/', views.vista_azcapotzalco, name='azcapotzalco'),
    path('cuajimalpa/', views.vista_cuajimalpa, name='cuajimalpa'),

]

