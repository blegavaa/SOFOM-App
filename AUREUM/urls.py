from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", RedirectView.as_view(url="/home/", permanent=False)),

    path("home/", views.home, name="home"),

    path("about/", views.about, name="about"),

    path("login/", views.login_view, name="login"),

    path("sofom/register/", views.sofom_register, name="sofom_register"),

    path("monarca/dashboard/", views.dashboard, name="dashboard"),

    path("monarca/clients/", views.clients, name="clients"),

    path("monarca/clients/new/", views.clients_new, name="clients_new"),
    
    path("monarca/credits/", views.credits, name="credits"),
    
    path("monarca/settings/", views.settings, name="settings"),

    path("monarca/", views.sofom_home, name="sofom_home"),

    path("monarca/register/", 
        views.sofom_clients_register,
        name="sofom_clients_register"
    ),

    path("monarca/clients/<str:matricula>/",
        views.client_detail_view,
        name="clients_detail"
    ),

    path("monarca/clients/<str:matricula>/new_credit/",
        views.clients_new_credit,
        name="clients_new_credit"
    ),

    path("monarca/credits/<int:credit_id>/",
        views.credit_detail,
        name="credit_detail"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

]