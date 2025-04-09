from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
from accounts.models import User

# Create your models here.

class Medication(models.Model):
    name = models.CharField(max_length=100)
    disease = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        if self.disease:
            return f"{self.name} ({self.disease})"
        return self.name

class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    nhs_number = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='NHS number must be 10 digits'
            )
        ]
    )
    hospital_number = models.CharField(max_length=50, null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} (NHS: {self.nhs_number})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """Calculate age in years from date of birth."""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

class PatientMedication(models.Model):
    STATUS_GREEN = 'green'
    STATUS_AMBER = 'amber'
    STATUS_RED = 'red'

    STATUS_CHOICES = [
        (STATUS_GREEN, 'On Track'),
        (STATUS_AMBER, 'Due Soon/Slightly Overdue'),
        (STATUS_RED, 'Significantly Overdue'),
    ]

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 2 Weeks'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Every 3 Months'),
        ('biannually', 'Every 6 Months'),
        ('annually', 'Yearly'),
        ('custom', 'Custom Schedule')
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medications')
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)
    dosage = models.CharField(max_length=100, null=True, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    custom_frequency_days = models.PositiveIntegerField(null=True, blank=True, 
                                                      help_text="Number of days between doses for custom frequency")
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    next_appointment = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    last_attendance_date = models.DateField(null=True, blank=True)

    def get_frequency_days(self):
        """Convert frequency choice to number of days between doses"""
        frequency_map = {
            'daily': 1,
            'weekly': 7,
            'biweekly': 14,
            'monthly': 30,
            'quarterly': 90,
            'biannually': 180,
            'annually': 365,
            'custom': self.custom_frequency_days or 0
        }
        return frequency_map.get(self.frequency, 0)

    def get_next_due_date(self):
        """Calculate when the next dose is due"""
        if not self.last_attendance_date:
            return self.start_date
        
        days_between = self.get_frequency_days()
        if days_between == 0:  # Invalid frequency
            return None
        
        return self.last_attendance_date + timedelta(days=days_between)

    def get_status(self):
        """
        Calculate traffic light status based on next due date
        Green: Not due for > 1 week
        Amber: Due within 1 week (before or after)
        Red: More than 1 week overdue
        """
        if not self.last_attendance_date and timezone.now().date() > self.start_date:
            return self.STATUS_RED

        next_due = self.get_next_due_date()
        if not next_due:
            return self.STATUS_RED

        today = timezone.now().date()
        days_until_due = (next_due - today).days

        if days_until_due < -7:  # More than 1 week overdue
            return self.STATUS_RED
        elif -7 <= days_until_due <= 7:  # Within 1 week either side
            return self.STATUS_AMBER
        else:  # Not due for > 1 week
            return self.STATUS_GREEN

    def get_status_display_name(self):
        """Get human-readable status name"""
        return dict(self.STATUS_CHOICES)[self.get_status()]

    class Meta:
        ordering = ['patient', 'medication']

    def __str__(self):
        return f"{self.patient.full_name} - {self.medication.name} ({self.get_frequency_display()})"

class AttendanceRecord(models.Model):
    patient_medication = models.ForeignKey(PatientMedication, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateTimeField()
    attended = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        # Update the last_attendance_date on the PatientMedication when attendance is recorded
        if self.attended:
            self.patient_medication.last_attendance_date = self.date.date()
            self.patient_medication.save()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        status = "Attended" if self.attended else "Missed"
        return f"{self.patient_medication.patient.full_name} - {status} on {self.date.strftime('%Y-%m-%d')}"
