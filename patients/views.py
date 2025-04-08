from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Count, Q, Min, Case, When, Value, CharField, OuterRef, Subquery
from django.utils import timezone
from .models import Patient, PatientMedication, AttendanceRecord, Medication
from django.template.loader import render_to_string
import logging
import random
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

# Create your views here.

class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20

    def get_queryset(self):
        # Get next appointment for each patient
        next_appointments = PatientMedication.objects.filter(
            patient=OuterRef('pk')
        ).annotate(
            next_date=Min('attendance_records__date', 
            filter=Q(attendance_records__date__gt=timezone.now()))
        ).values('next_date')[:1]

        queryset = Patient.objects.annotate(
            medication_count=Count('medications'),
            next_appointment=Subquery(next_appointments),
            medication_status=Case(
                When(medications__isnull=True, then=Value('none')),
                default=Value('unknown'),
                output_field=CharField(),
            )
        ).prefetch_related('medications')

        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(nhs_number__icontains=search_query)
            )

        # Sorting
        sort_by = self.request.GET.get('sort', '')
        sort_dir = self.request.GET.get('dir', 'asc')
        
        if sort_by == 'name':
            order_by = ['last_name', 'first_name'] if sort_dir == 'asc' else ['-last_name', '-first_name']
        elif sort_by == 'nhs':
            order_by = ['nhs_number'] if sort_dir == 'asc' else ['-nhs_number']
        elif sort_by == 'appointment':
            order_by = ['next_appointment'] if sort_dir == 'asc' else ['-next_appointment']
        elif sort_by == 'medications':
            order_by = ['medication_count'] if sort_dir == 'asc' else ['-medication_count']
        else:
            order_by = ['last_name', 'first_name']
        
        return queryset.order_by(*order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sort_by'] = self.request.GET.get('sort', '')
        context['sort_dir'] = self.request.GET.get('dir', 'asc')
        context['search_query'] = self.request.GET.get('search', '')
        context['is_mobile'] = self.request.user_agent.is_mobile
        
        # Add medication status for each patient
        for patient in context['patients']:
            worst_status = 'green'
            has_medications = False
            
            for med in patient.medications.all():
                has_medications = True
                status = med.get_status()
                if status == 'red':
                    worst_status = 'red'
                    break
                elif status == 'amber' and worst_status != 'red':
                    worst_status = 'amber'
            
            patient.worst_status = 'none' if not has_medications else worst_status
            
        return context

class PatientDetailView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object
        now = timezone.now()
        
        # Get active medications with their next appointments
        active_medications = patient.medications.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now.date())
        ).select_related('medication')
        
        # For each medication, get its next appointment
        for med in active_medications:
            next_appointment = med.attendance_records.filter(
                date__gt=now
            ).order_by('date').first()
            med.next_appointment = next_appointment
        
        context['active_medications'] = active_medications
        context['now'] = now
        context['is_mobile'] = self.request.user_agent.is_mobile
        
        # Get recent attendance records across all medications
        recent_attendance = AttendanceRecord.objects.filter(
            patient_medication__patient=patient
        ).select_related('patient_medication__medication').order_by('-date')[:5]
        context['recent_attendance'] = recent_attendance
        
        # Get upcoming appointments
        upcoming_attendance = AttendanceRecord.objects.filter(
            patient_medication__patient=patient,
            date__gt=now
        ).select_related('patient_medication__medication').order_by('date')[:3]
        context['upcoming_attendance'] = upcoming_attendance
        
        return context

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from .models import Patient, PatientMedication, AttendanceRecord, Medication
import random
from datetime import datetime, timedelta

@login_required
def patient_list(request):
    sort_by = request.GET.get('sort', 'last_name')
    order = request.GET.get('order', 'asc')
    search_query = request.GET.get('search', '').strip()

    # Start with all patients and prefetch related medications
    patients = Patient.objects.all().prefetch_related(
        'medications',
        'medications__medication'
    )

    # Apply search filter if provided
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(hospital_number__icontains=search_query) |
            Q(medications__medication__name__icontains=search_query)
        ).distinct()

    # Apply sorting
    if sort_by == 'name':
        patients = patients.order_by(f'{"" if order == "asc" else "-"}last_name', 'first_name')
    elif sort_by == 'next_appointment':
        patients = patients.order_by(f'{"" if order == "asc" else "-"}medications__next_appointment')
    elif sort_by == 'disease':
        patients = patients.order_by(f'{"" if order == "asc" else "-"}medications__medication__disease')
    else:
        patients = patients.order_by(f'{"" if order == "asc" else "-"}{sort_by}')

    context = {
        'patients': patients,
        'current_time': timezone.now(),  
        'is_mobile': request.user_agent.is_mobile,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'patients/partials/patient_table_body.html', context)
    return render(request, 'patients/patient_list.html', context)

def generate_dummy_patient():
    first_names = ["James", "Emma", "Oliver", "Sophia", "William", "Isabella", "Henry", "Charlotte", "George", "Ava"]
    last_names = ["Smith", "Jones", "Williams", "Brown", "Taylor", "Davies", "Wilson", "Evans", "Thomas", "Johnson"]
    medications = ["Mycophenalate", "Methotrexate", "Ibuprofen", "Amoxicillin", "Omeprazole", "Simvastatin", "Ramipril"]
    frequencies = ["daily", "weekly", "biweekly", "monthly", "quarterly"]
    diseases = ["Rheumatoid Arthritis", "Sarcoidoisis", "Asthma", "Bronchiectasis", "COPD", "Heart Disease", "Depression"]
    doses = ["100mg", "250mg", "500mg", "1g", "2g", "5mg", "10mg", "20mg"]
    
    # Generate random dates within a reasonable range
    dob = timezone.now() - timedelta(days=random.randint(365*20, 365*80))  # Age between 20-80
    next_appointment = timezone.now() + timedelta(days=random.randint(1, 60))  # Next 1-60 days
    last_attendance = timezone.now() - timedelta(days=random.randint(1, 30))  # Last 1-30 days
    
    return {
        'first_name': random.choice(first_names),
        'last_name': random.choice(last_names),
        'date_of_birth': dob,
        'nhs_number': f"{random.randint(1000000000, 9999999999)}",  # 10 digit number
        'hospital_number': f"H{random.randint(10000, 99999)}",
        'medication': random.choice(medications),
        'disease': random.choice(diseases),
        'frequency': random.choice(frequencies),
        'next_appointment': next_appointment,
        'last_attendance': last_attendance,
        'dose': random.choice(doses),
        'notes': f"Test patient created on {timezone.now().strftime('%Y-%m-%d')}"
    }

@require_http_methods(["POST"])
def add_dummy_patient(request):
    if request.method == 'POST':
        try:
            dummy_data = generate_dummy_patient()
            
            # Create the patient
            patient = Patient.objects.create(
                first_name=dummy_data['first_name'],
                last_name=dummy_data['last_name'],
                date_of_birth=dummy_data['date_of_birth'],
                nhs_number=dummy_data['nhs_number'],
                hospital_number=dummy_data['hospital_number']
            )
            
            # Create medication
            medication = Medication.objects.create(
                name=dummy_data['medication'],
                disease=dummy_data['disease'],
                description=f"Medication for {dummy_data['disease']}"
            )
            
            # Create patient medication link with all fields
            patient_med = PatientMedication.objects.create(
                patient=patient,
                medication=medication,
                frequency=dummy_data['frequency'],
                next_appointment=dummy_data['next_appointment'],
                dosage=dummy_data['dose'],
                notes=dummy_data['notes'],
                last_attendance_date=dummy_data['last_attendance'].date()
            )
            
            # Create an attendance record
            AttendanceRecord.objects.create(
                patient_medication=patient_med,
                date=dummy_data['last_attendance'],
                notes="Initial attendance record"
            )
            
            return render(request, 'patients/partials/patient_row.html', {
                'patient': patient,
                'current_time': timezone.now()
            })
        except Exception as e:
            logger.error(f"Error adding dummy patient: {str(e)}")
            return HttpResponse(f"Error adding dummy patient: {str(e)}", status=500)
    return HttpResponseBadRequest()

def add_patient(request):
    try:
        # Log the incoming data for debugging
        logger.debug(f"Received POST data: {request.POST}")
        
        # Create patient with required fields
        patient_data = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'nhs_number': request.POST.get('nhs_number') or None,
            'hospital_number': request.POST.get('hospital_number') or None
        }
        
        # Handle date of birth
        dob = request.POST.get('date_of_birth')
        if dob and dob.strip():
            patient_data['date_of_birth'] = dob
        
        # Validate required fields
        if not patient_data['first_name'] or not patient_data['last_name']:
            raise ValidationError("First name and last name are required")

        patient = Patient.objects.create(**patient_data)

        # Create medication if provided
        medication_name = request.POST.get('medication')
        if medication_name and medication_name.strip():
            medication = Medication.objects.create(
                name=medication_name.strip()
            )

            # Create patient medication relationship if frequency is provided
            frequency = request.POST.get('frequency')
            if frequency and frequency.strip():
                patient_med_data = {
                    'patient': patient,
                    'medication': medication,
                    'frequency': frequency.strip(),
                }
                
                # Add next appointment if provided
                next_appointment = request.POST.get('next_appointment')
                if next_appointment and next_appointment.strip():
                    patient_med_data['next_appointment'] = next_appointment
                
                PatientMedication.objects.create(**patient_med_data)

        # Return the new patient row HTML
        return render(request, 'patients/partials/patient_row.html', {'patient': patient})
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return HttpResponse(str(e), status=400)
    except Exception as e:
        logger.error(f"Error adding patient: {str(e)}")
        return HttpResponse(f"Error adding patient: {str(e)}", status=400)

@require_http_methods(["GET"])
def fetch_patient_details(request):
    hospital_number = request.GET.get('hospital_number')
    # TODO: Implement actual API call here
    # For now, return dummy data
    dummy_data = {
        'first_name': 'John',
        'last_name': 'Doe',
        'date_of_birth': '1990-01-01',
        'nhs_number': '123456789'
    }
    return JsonResponse(dummy_data)

@login_required
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    active_medications = patient.medications.filter(end_date__isnull=True)
    
    # Get attendance records through PatientMedication
    recent_attendance = AttendanceRecord.objects.filter(
        patient_medication__patient=patient
    ).select_related('patient_medication__medication').order_by('-date')[:10]

    # Get upcoming appointments
    upcoming_appointments = PatientMedication.objects.filter(
        patient=patient,
        next_appointment__gt=timezone.now()
    ).select_related('medication').order_by('next_appointment')[:5]

    context = {
        'patient': patient,
        'active_medications': active_medications,
        'recent_attendance': recent_attendance,
        'upcoming_appointments': upcoming_appointments,
        'current_time': timezone.now(),
        'is_mobile': request.user_agent.is_mobile,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'patients/partials/patient_detail.html', context)
    return render(request, 'patients/patient_detail.html', context)

@login_required
def edit_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    if request.method == 'POST':
        # Handle form submission later
        pass
    if request.headers.get('HX-Request'):
        return render(request, 'patients/partials/edit_patient.html', {'patient': patient, 'is_mobile': request.user_agent.is_mobile})
    return render(request, 'patients/edit_patient.html', {'patient': patient, 'is_mobile': request.user_agent.is_mobile})

@login_required
def delete_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    if request.method == 'DELETE':
        patient.delete()
        return HttpResponse(status=200)
    elif request.headers.get('HX-Request'):
        return render(request, 'patients/partials/delete_confirm.html', {'patient': patient, 'is_mobile': request.user_agent.is_mobile})
    return render(request, 'patients/delete_confirm.html', {'patient': patient, 'is_mobile': request.user_agent.is_mobile})

@login_required
def patient_list(request):
    patients = Patient.objects.all().order_by('first_name')
    sort = request.GET.get('sort')
    search = request.GET.get('search')

    if search:
        patients = patients.filter(
            Q(first_name__icontains=search) | 
            Q(last_name__icontains=search) |
            Q(medications__medication__disease__icontains=search) |
            Q(medications__medication__name__icontains=search)
        ).distinct()

    if sort == 'name':
        patients = patients.order_by('first_name')
    elif sort == 'disease':
        patients = patients.order_by('medications__medication__disease')
    elif sort == 'next_appointment':
        patients = patients.order_by('medications__next_appointment')

    context = {
        'patients': patients,
        'is_mobile': request.user_agent.is_mobile,
        'current_time': timezone.now(),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'patients/partials/patient_table_body.html', context)
    return render(request, 'patients/patient_list.html', context)
