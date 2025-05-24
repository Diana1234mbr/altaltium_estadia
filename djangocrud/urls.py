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
    path('alcaldia/<int:id>/', views.detalle_alcaldia, name='detalle_alcaldia'),
    path('admin-panel/<str:page>/', views.gentelella_view, name='gentelella_page'),
]
