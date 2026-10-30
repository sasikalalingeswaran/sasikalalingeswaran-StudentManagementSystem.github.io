from django.db import models
from django.utils import timezone
from datetime import date

class Faculty(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    employee_id = models.CharField(max_length=30, unique=True)
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Student(models.Model):
    name = models.CharField(max_length=120)
    login_name = models.CharField(max_length=140, unique=True)
    roll_number = models.CharField(max_length=30, unique=True)
    dob = models.DateField()
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=100, default="General")
    year = models.PositiveSmallIntegerField(default=1)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name} ({self.roll_number})"

class Assignment(models.Model):
    title = models.CharField(max_length=180)
    subject = models.CharField(max_length=100)
    description = models.TextField()
    due_date = models.DateField()
    created_by = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class MarkRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    subject = models.CharField(max_length=100)
    assessment = models.CharField(max_length=120, default="Internal Assessment")
    score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["student__name", "subject"]

class StudentQuery(models.Model):
    STATUS = [("open","Open"),("answered","Answered")]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="queries")
    subject = models.CharField(max_length=160)
    message = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ["-created_at"]
