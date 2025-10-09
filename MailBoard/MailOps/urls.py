from django.urls import path
from . import views

app_name = 'mailops'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('oauth/start/', views.oauth_start, name='oauth_start'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('accounts/', views.account_management, name='account_management'),
    path('accounts/add/', views.add_account, name='add_account'),
    path('accounts/switch/<str:account_id>/', views.switch_account, name='switch_account'),
    path('accounts/remove/<str:account_id>/', views.remove_account, name='remove_account'),
    path('label/<str:label_id>/', views.dashboard_by_label, name='dashboard_by_label'),
    path('label/<str:label_id>/delete_all/', views.label_delete_all, name='label_delete_all'),
    path('message/<str:message_id>/', views.message_detail, name='message_detail'),
    path('message/<str:message_id>/delete/', views.message_delete, name='message_delete'),
    path('message/<str:message_id>/add_labels/', views.add_labels_to_message, name='add_labels_to_message'),
    path('message/<str:message_id>/remove_labels/', views.remove_labels_from_message, name='remove_labels_from_message'),
    path('labels/create/', views.create_label, name='create_label'),
]


