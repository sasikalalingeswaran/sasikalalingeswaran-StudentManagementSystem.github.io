import pytest
from django.urls import reverse
from portal.models import Student, Assignment, MarkRecord, StudentQuery


@pytest.mark.parametrize("name", ["faculty_dashboard", "student_list",
                                  "assignment_list", "marks_list", "faculty_queries"])
def test_faculty_pages_redirect_when_anonymous(client, name):
    resp = client.get(reverse(name))
    assert resp.status_code == 302
    assert resp.url == reverse("faculty_login")


@pytest.mark.parametrize("name", ["student_dashboard", "student_profile",
                                  "student_marks", "student_assignments", "student_queries"])
def test_student_pages_redirect_when_anonymous(client, name):
    resp = client.get(reverse(name))
    assert resp.status_code == 302
    assert resp.url == reverse("student_login")


def test_student_cannot_open_faculty_pages(student_client):
    resp = student_client.get(reverse("faculty_dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("faculty_login")


def test_faculty_login_flow(client, faculty):
    resp = client.post(reverse("faculty_login"),
                       {"employee_id": "F001", "password": "secret123"})
    assert resp.status_code == 302
    assert client.session["faculty_id"] == faculty.id


def test_faculty_login_bad_password_stays_on_page(client, faculty):
    resp = client.post(reverse("faculty_login"),
                       {"employee_id": "F001", "password": "wrong"})
    assert resp.status_code == 200
    assert "faculty_id" not in client.session


def test_student_login_flow(client, student):
    resp = client.post(reverse("student_login"),
                       {"login_name": "asha-kumar", "dob": "2004-05-17"})
    assert resp.status_code == 302
    assert client.session["student_id"] == student.id


def test_logout_clears_session(faculty_client):
    faculty_client.get(reverse("logout"))
    assert "faculty_id" not in faculty_client.session


def test_dashboard_renders(faculty_client, student):
    resp = faculty_client.get(reverse("faculty_dashboard"))
    assert resp.status_code == 200
    assert resp.context["student_count"] == 1


def test_student_search(faculty_client, student):
    resp = faculty_client.get(reverse("student_list"), {"q": "asha"})
    assert student in resp.context["students"]
    resp = faculty_client.get(reverse("student_list"), {"q": "zzz"})
    assert len(resp.context["students"]) == 0


def test_add_student(faculty_client):
    resp = faculty_client.post(reverse("student_add"), {
        "name": "Ravi S", "roll_number": "R9", "dob": "2003-01-02",
        "department": "ECE", "year": 3})
    assert resp.status_code == 302
    assert Student.objects.get(roll_number="R9").login_name == "ravi-s"


def test_delete_requires_post(faculty_client, student):
    url = reverse("student_delete", args=[student.pk])
    assert faculty_client.get(url).status_code == 405
    assert Student.objects.filter(pk=student.pk).exists()
    faculty_client.post(url)
    assert not Student.objects.filter(pk=student.pk).exists()


def test_create_assignment_sets_creator(faculty_client, faculty):
    faculty_client.post(reverse("assignment_add"), {
        "title": "HW1", "subject": "Maths", "description": "Do it",
        "due_date": "2026-12-01"})
    assert Assignment.objects.get(title="HW1").created_by == faculty


def test_save_marks(faculty_client, student):
    faculty_client.post(reverse("marks_list"), {
        "student": student.id, "subject": "Maths", "assessment": "Quiz",
        "score": "40", "max_score": "50"})
    assert MarkRecord.objects.filter(student=student).count() == 1


def test_respond_to_query_marks_answered(faculty_client, student):
    q = StudentQuery.objects.create(student=student, subject="Help", message="?")
    faculty_client.post(reverse("query_respond", args=[q.pk]), {"response": "Sure"})
    q.refresh_from_db()
    assert q.status == "answered" and q.responded_at is not None


def test_blank_response_rejected(faculty_client, student):
    q = StudentQuery.objects.create(student=student, subject="Help", message="?")
    faculty_client.post(reverse("query_respond", args=[q.pk]), {"response": "   "})
    q.refresh_from_db()
    assert q.status == "open"


def test_student_dashboard_percentage(student_client, student):
    MarkRecord.objects.create(student=student, subject="A", score=40, max_score=50)
    MarkRecord.objects.create(student=student, subject="B", score=30, max_score=50)
    resp = student_client.get(reverse("student_dashboard"))
    assert resp.context["percentage"] == 70.0


def test_student_sees_only_own_marks(student_client, student, db):
    other = Student.objects.create(name="Other", login_name="other",
                                   roll_number="R2", dob="2004-01-01")
    MarkRecord.objects.create(student=other, subject="X", score=1, max_score=10)
    resp = student_client.get(reverse("student_marks"))
    assert len(resp.context["records"]) == 0


def test_student_submits_query(student_client, student):
    student_client.post(reverse("student_queries"),
                        {"subject": "Exam", "message": "When?"})
    assert StudentQuery.objects.get(student=student).subject == "Exam"



from datetime import date

def test_home_page(client):
    assert client.get(reverse("home")).status_code == 200


def test_faculty_signup_creates_account_and_logs_in(client):
    resp = client.post(reverse("faculty_signup"), {
        "name": "Dr. New", "email": "new@example.com",
        "employee_id": "F777", "password": "longenough1"})
    assert resp.status_code == 302
    assert "faculty_id" in client.session


def test_faculty_signup_page_loads(client):
    assert client.get(reverse("faculty_signup")).status_code == 200


def test_signup_redirects_if_already_logged_in(faculty_client):
    resp = faculty_client.get(reverse("faculty_signup"))
    assert resp.url == reverse("faculty_dashboard")


def test_stale_faculty_session_redirects(client):
    session = client.session
    session["faculty_id"] = 99999
    session.save()
    resp = client.get(reverse("faculty_dashboard"))
    assert resp.url == reverse("faculty_login")
    assert "faculty_id" not in client.session


def test_stale_student_session_redirects(client):
    session = client.session
    session["student_id"] = 99999
    session.save()
    resp = client.get(reverse("student_dashboard"))
    assert resp.url == reverse("student_login")


def test_student_add_and_edit_pages_load(faculty_client, student):
    assert faculty_client.get(reverse("student_add")).status_code == 200
    assert faculty_client.get(reverse("student_edit", args=[student.pk])).status_code == 200


def test_edit_student(faculty_client, student):
    resp = faculty_client.post(reverse("student_edit", args=[student.pk]), {
        "name": "Asha Kumar", "roll_number": "R001", "dob": "2004-05-17",
        "department": "Physics", "year": 2})
    assert resp.status_code == 302
    student.refresh_from_db()
    assert student.department == "Physics"


def test_assignment_list_edit_delete(faculty_client, faculty):
    a = Assignment.objects.create(title="T", subject="S", description="D",
                                  due_date=date(2026, 12, 1), created_by=faculty)
    assert faculty_client.get(reverse("assignment_list")).status_code == 200
    assert faculty_client.get(reverse("assignment_edit", args=[a.pk])).status_code == 200
    faculty_client.post(reverse("assignment_edit", args=[a.pk]), {
        "title": "Updated", "subject": "S", "description": "D",
        "due_date": "2026-12-02"})
    a.refresh_from_db()
    assert a.title == "Updated"
    faculty_client.post(reverse("assignment_delete", args=[a.pk]))
    assert not Assignment.objects.filter(pk=a.pk).exists()


def test_mark_delete(faculty_client, student):
    m = MarkRecord.objects.create(student=student, subject="A", score=5, max_score=10)
    faculty_client.post(reverse("mark_delete", args=[m.pk]))
    assert not MarkRecord.objects.filter(pk=m.pk).exists()


def test_faculty_queries_page(faculty_client):
    assert faculty_client.get(reverse("faculty_queries")).status_code == 200


def test_invalid_marks_show_form_errors(faculty_client, student):
    resp = faculty_client.post(reverse("marks_list"), {
        "student": student.id, "subject": "M", "assessment": "Q",
        "score": "90", "max_score": "50"})
    assert resp.status_code == 200
    assert MarkRecord.objects.count() == 0


def test_student_profile_and_assignments_pages(student_client):
    assert student_client.get(reverse("student_profile")).status_code == 200
    assert student_client.get(reverse("student_assignments")).status_code == 200

def test_faculty_signup_creates_account_and_logs_in(client, db):
    resp = client.post(reverse("faculty_signup"), {
        "name": "Dr. New", "email": "new@example.com",
        "employee_id": "F777", "password": "longenough1"})
    assert resp.status_code == 302
    assert "faculty_id" in client.session


def test_stale_faculty_session_redirects(client, db):
    session = client.session
    session["faculty_id"] = 99999
    session.save()
    resp = client.get(reverse("faculty_dashboard"))
    assert resp.url == reverse("faculty_login")
    assert "faculty_id" not in client.session


def test_stale_student_session_redirects(client, db):
    session = client.session
    session["student_id"] = 99999
    session.save()
    resp = client.get(reverse("student_dashboard"))
    assert resp.url == reverse("student_login")