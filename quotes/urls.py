from django.urls import path

from quotes import views

urlpatterns = [
    path('', views.quotes_list),
    path('add/', views.quotes_add),
    path('pending/', views.quotes_pending),
    path("highscore/", views.quotes_highscore),

    path('<int:quote_id>/vote-up', views.vote_up),
    path('<int:quote_id>/vote-down', views.vote_down),
    path('<int:quote_id>/edit', views.quotes_edit),
    path('<int:quote_id>/delete', views.quotes_delete),
    path('<int:quote_id>/approve', views.quotes_approve)

]
