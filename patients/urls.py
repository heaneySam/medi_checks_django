from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.PatientListView.as_view(), name='patient_list'),
    path('add/', views.add_patient, name='add_patient'),
    path('add-dummy/', views.add_dummy_patient, name='add_dummy_patient'),
    path('fetch-details/', views.fetch_patient_details, name='fetch_patient_details'),
    path('<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('<int:patient_id>/edit/', views.edit_patient, name='edit_patient'),
    path('<int:patient_id>/delete/', views.delete_patient, name='delete_patient'),
]
