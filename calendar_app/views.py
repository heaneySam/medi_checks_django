from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from patients.models import PatientMedication

# Create your views here.

@login_required
def calendar_view(request):
    return render(request, 'calendar_app/calendar.html')

@login_required
def calendar_events(request):
    # Get start and end parameters from FullCalendar request
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    # Query all appointments
    appointments = PatientMedication.objects.filter(
        next_appointment__isnull=False
    ).select_related('patient', 'medication')
    
    # Format events for FullCalendar
    events = []
    for appt in appointments:
        status = appt.get_status()
        events.append({
            'id': appt.id,
            'title': f"{appt.patient.full_name} - {appt.medication.name}",
            'start': appt.next_appointment.isoformat(),
            'backgroundColor': {
                'green': '#10B981',  # Tailwind green-500
                'amber': '#F59E0B',  # Tailwind amber-500
                'red': '#EF4444',    # Tailwind red-500
            }.get(status, '#6B7280'),  # Default: gray-500
            'extendedProps': {
                'patient_id': appt.patient.id,
                'medication': appt.medication.name,
                'status': status,
                'dose': appt.dosage or 'Not specified'
            }
        })
    
    return JsonResponse(events, safe=False)
