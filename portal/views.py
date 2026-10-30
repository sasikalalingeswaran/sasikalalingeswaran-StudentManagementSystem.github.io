from datetime import date
import json
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import Avg, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Faculty, Student, Assignment, MarkRecord, StudentQuery
from .forms import FacultySignupForm, FacultyLoginForm, StudentLoginForm, StudentForm, AssignmentForm, MarkForm, QueryForm, ResponseForm

def home(request):
    return render(request, "portal/home.html")

def faculty_signup(request):
    if request.session.get("faculty_id"): return redirect("faculty_dashboard")
    form = FacultySignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        faculty = form.save()
        request.session["faculty_id"] = faculty.id
        messages.success(request, "Faculty account created. Welcome to your dashboard.")
        return redirect("faculty_dashboard")
    return render(request, "portal/form_page.html", {"form":form,"heading":"Create faculty account","subtitle":"Register your institutional faculty profile","back_url":"home"})

def faculty_login(request):
    form = FacultyLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.session["faculty_id"] = form.cleaned_data["faculty"].id
        messages.success(request, "Signed in successfully.")
        return redirect("faculty_dashboard")
    return render(request, "portal/form_page.html", {"form":form,"heading":"Faculty sign in","subtitle":"Access academic management tools","back_url":"home"})

def student_login(request):
    form = StudentLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.session["student_id"] = form.cleaned_data["student"].id
        messages.success(request, f"Welcome, {form.cleaned_data['student'].name}.")
        return redirect("student_dashboard")
    return render(request, "portal/form_page.html", {"form":form,"heading":"Student sign in","subtitle":"Use your registered name and date of birth","back_url":"home"})

def faculty_required(view):
    def wrapped(request, *args, **kwargs):
        if not request.session.get("faculty_id"):
            messages.info(request, "Please sign in as faculty first.")
            return redirect("faculty_login")
        try: request.faculty = Faculty.objects.get(pk=request.session["faculty_id"])
        except Faculty.DoesNotExist:
            request.session.pop("faculty_id", None); return redirect("faculty_login")
        return view(request,*args,**kwargs)
    return wrapped

def student_required(view):
    def wrapped(request, *args, **kwargs):
        if not request.session.get("student_id"):
            messages.info(request, "Please sign in as a student first.")
            return redirect("student_login")
        try: request.student = Student.objects.get(pk=request.session["student_id"])
        except Student.DoesNotExist:
            request.session.pop("student_id", None); return redirect("student_login")
        return view(request,*args,**kwargs)
    return wrapped

@faculty_required
def faculty_dashboard(request):
    students = Student.objects.all().order_by("name")
    marks = MarkRecord.objects.select_related("student")
    queries = StudentQuery.objects.select_related("student")
    context = {"faculty":request.faculty,"student_count":students.count(),"assignment_count":Assignment.objects.count(),
        "open_queries":queries.filter(status="open").count(),"average_score":marks.aggregate(v=Avg("score"))["v"] or 0,
        "recent_queries":queries[:5],"recent_students":students[:5]}
    return render(request,"portal/faculty_dashboard.html",context)

@faculty_required
def student_list(request):
    q=request.GET.get("q","").strip()
    students=Student.objects.all().order_by("name")
    if q: students=students.filter(name__icontains=q) | students.filter(roll_number__icontains=q)
    return render(request,"portal/student_list.html",{"students":students,"q":q})

@faculty_required
def student_add(request):
    form=StudentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        student=form.save()
        messages.success(request,f"Student added. Login name: {student.login_name} · Initial password: {student.dob:%Y-%m-%d}")
        return redirect("student_list")
    return render(request,"portal/form_page.html",{"form":form,"heading":"Add student","subtitle":"Student login name is generated from their registered name","back_url":"student_list"})

@faculty_required
def student_edit(request,pk):
    student=get_object_or_404(Student,pk=pk); form=StudentForm(request.POST or None,instance=student)
    if request.method=="POST" and form.is_valid():
        student=form.save(); messages.success(request,f"Student updated. Login name: {student.login_name}"); return redirect("student_list")
    return render(request,"portal/form_page.html",{"form":form,"heading":"Edit student","subtitle":"Update student profile and login details","back_url":"student_list"})

@faculty_required
@require_POST
def student_delete(request,pk):
    get_object_or_404(Student,pk=pk).delete(); messages.success(request,"Student and related records deleted."); return redirect("student_list")

@faculty_required
def assignment_list(request):
    assignments=Assignment.objects.all().order_by("due_date")
    return render(request,"portal/assignment_list.html",{"assignments":assignments})

@faculty_required
def assignment_add(request):
    form=AssignmentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False); obj.created_by=request.faculty; obj.save(); messages.success(request,"Assignment published."); return redirect("assignment_list")
    return render(request,"portal/form_page.html",{"form":form,"heading":"Create assignment","subtitle":"Publish work and set a due date","back_url":"assignment_list"})

@faculty_required
def assignment_edit(request,pk):
    obj=get_object_or_404(Assignment,pk=pk); form=AssignmentForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Assignment updated."); return redirect("assignment_list")
    return render(request,"portal/form_page.html",{"form":form,"heading":"Edit assignment","subtitle":"Revise assignment details","back_url":"assignment_list"})

@faculty_required
@require_POST
def assignment_delete(request,pk):
    get_object_or_404(Assignment,pk=pk).delete(); messages.success(request,"Assignment deleted."); return redirect("assignment_list")

@faculty_required
def marks_list(request):
    form=MarkForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Marks saved."); return redirect("marks_list")
    records=MarkRecord.objects.select_related("student")
    students=Student.objects.all().order_by("name")
    chart_labels=[]; chart_values=[]
    for s in students:
        vals=list(s.marks.values_list("score",flat=True))
        if vals: chart_labels.append(s.name); chart_values.append(round(sum(float(x) for x in vals)/len(vals),2))
    return render(request,"portal/marks.html",{"form":form,"records":records,"chart_labels_json":json.dumps(chart_labels),"chart_values_json":json.dumps(chart_values)})

@faculty_required
@require_POST
def mark_delete(request,pk):
    get_object_or_404(MarkRecord,pk=pk).delete(); messages.success(request,"Mark record deleted."); return redirect("marks_list")

@faculty_required
def faculty_queries(request):
    queries=StudentQuery.objects.select_related("student")
    form=ResponseForm()
    return render(request,"portal/faculty_queries.html",{"queries":queries,"form":form})

@faculty_required
@require_POST
def query_respond(request,pk):
    query=get_object_or_404(StudentQuery,pk=pk); form=ResponseForm(request.POST,instance=query)
    if form.is_valid() and form.cleaned_data["response"].strip():
        obj=form.save(commit=False); obj.status="answered"; obj.responded_at=timezone.now(); obj.save(); messages.success(request,"Response sent to student.")
    else: messages.error(request,"Please enter a response.")
    return redirect("faculty_queries")

@student_required
def student_dashboard(request):
    s=request.student
    records=s.marks.all()
    total=sum(float(m.score) for m in records); maximum=sum(float(m.max_score) for m in records)
    pct=(total/maximum*100) if maximum else 0
    return render(request,"portal/student_dashboard.html",{"student":s,"records":records,"assignments":Assignment.objects.all().order_by("due_date"),"queries":s.queries.all()[:4],"percentage":round(pct,1)})

@student_required
def student_profile(request):
    return render(request,"portal/student_profile.html",{"student":request.student})

@student_required
def student_marks(request):
    records=request.student.marks.all()
    return render(request,"portal/student_marks.html",{"records":records})

@student_required
def student_assignments(request):
    return render(request,"portal/student_assignments.html",{"assignments":Assignment.objects.all().order_by("due_date")})

@student_required
def student_queries(request):
    form=QueryForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False); obj.student=request.student; obj.save(); messages.success(request,"Your query was sent to faculty."); return redirect("student_queries")
    return render(request,"portal/student_queries.html",{"form":form,"queries":request.student.queries.all()})

def logout(request):
    request.session.flush(); messages.success(request,"You have signed out."); return redirect("home")
