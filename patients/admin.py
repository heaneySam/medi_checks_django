from django.contrib import admin
from .models import Patient, Medication, PatientMedication, AttendanceRecord

# Register your models here.

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'nhs_number', 'date_of_birth', 'contact_number')
    search_fields = ('first_name', 'last_name', 'nhs_number')
    list_filter = ('created_at',)

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(PatientMedication)
class PatientMedicationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'medication', 'dosage', 'frequency', 'start_date', 'get_status_display_name')
    list_filter = ('frequency', 'start_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'medication__name')
    ordering = ('patient', 'medication')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('patient_medication', 'date', 'attended', 'created_by')
    list_filter = ('attended', 'date', 'created_by')
    search_fields = ('patient_medication__patient__first_name', 'patient_medication__patient__last_name', 
                    'patient_medication__medication__name')
