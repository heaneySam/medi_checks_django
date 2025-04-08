from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.patient_list, name='patient_list'),
    path('add/', views.add_patient, name='add_patient'),
    path('add-dummy/', views.add_dummy_patient, name='add_dummy_patient'),
    path('fetch-details/', views.fetch_patient_details, name='fetch_patient_details'),
    path('<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
]
