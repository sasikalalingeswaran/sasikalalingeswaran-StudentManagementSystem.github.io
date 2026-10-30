from django import forms
from django.contrib.auth.hashers import make_password, check_password
from .models import Faculty, Student, Assignment, MarkRecord, StudentQuery

class FacultySignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    class Meta:
        model = Faculty
        fields = ["name","email","employee_id"]
    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.password_hash = make_password(self.cleaned_data["password"])
        if commit: obj.save()
        return obj

class FacultyLoginForm(forms.Form):
    employee_id = forms.CharField(label="Employee ID")
    password = forms.CharField(widget=forms.PasswordInput)
    def clean(self):
        data = super().clean()
        if data.get("employee_id") and data.get("password"):
            try: faculty = Faculty.objects.get(employee_id__iexact=data["employee_id"].strip())
            except Faculty.DoesNotExist: raise forms.ValidationError("Invalid employee ID or password.")
            if not check_password(data["password"], faculty.password_hash):
                raise forms.ValidationError("Invalid employee ID or password.")
            data["faculty"] = faculty
        return data

class StudentLoginForm(forms.Form):
    login_name = forms.CharField(label="Registered student name")
    dob = forms.DateField(label="Date of birth", widget=forms.DateInput(attrs={"type":"date"}))
    def clean(self):
        data = super().clean()
        if data.get("login_name") and data.get("dob"):
            try: student = Student.objects.get(login_name__iexact=data["login_name"].strip(), dob=data["dob"])
            except Student.DoesNotExist: raise forms.ValidationError("Student name or date of birth is incorrect.")
            data["student"] = student
        return data

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["name","roll_number","dob","email","department","year","phone","address"]
        widgets = {"dob": forms.DateInput(attrs={"type":"date"}), "address": forms.Textarea(attrs={"rows":3})}
    def save(self, commit=True):
        obj = super().save(commit=False)
        base = "-".join(obj.name.lower().strip().split())
        base = "".join(c for c in base if c.isalnum() or c == "-") or "student"
        login = base
        n = 2
        while Student.objects.filter(login_name__iexact=login).exclude(pk=obj.pk).exists():
            login = f"{base}-{n}"; n += 1
        obj.login_name = login
        if commit: obj.save()
        return obj

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["title","subject","description","due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type":"date"}), "description": forms.Textarea(attrs={"rows":4})}

class MarkForm(forms.ModelForm):
    class Meta:
        model = MarkRecord
        fields = ["student","subject","assessment","score","max_score"]
    def clean(self):
        data = super().clean()
        if data.get("score") is not None and data.get("max_score") is not None and data["score"] > data["max_score"]:
            raise forms.ValidationError("Score cannot be greater than maximum score.")
        return data

class QueryForm(forms.ModelForm):
    class Meta:
        model = StudentQuery
        fields = ["subject","message"]
        widgets = {"message": forms.Textarea(attrs={"rows":4, "placeholder":"Describe your question clearly..."})}

class ResponseForm(forms.ModelForm):
    class Meta:
        model = StudentQuery
        fields = ["response"]
        widgets = {"response": forms.Textarea(attrs={"rows":3, "placeholder":"Write a helpful response..."})}
