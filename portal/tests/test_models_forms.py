import pytest
from datetime import date
from decimal import Decimal
from portal.forms import (StudentForm, MarkForm, FacultyLoginForm,
                          StudentLoginForm, FacultySignupForm)
from portal.models import Student, Faculty


def student_data(**over):
    d = {"name": "Asha Kumar", "roll_number": "R100", "dob": "2004-05-17",
         "department": "CS", "year": 2}
    d.update(over)
    return d


@pytest.mark.django_db
def test_student_form_generates_login_name():
    form = StudentForm(student_data())
    assert form.is_valid(), form.errors
    assert form.save().login_name == "asha-kumar"


@pytest.mark.django_db
def test_student_form_login_name_collision_gets_suffix(student):
    form = StudentForm(student_data(roll_number="R200"))
    assert form.is_valid(), form.errors
    assert form.save().login_name == "asha-kumar-2"


@pytest.mark.django_db
def test_student_edit_keeps_own_login_name(student):
    form = StudentForm(student_data(roll_number="R001"), instance=student)
    assert form.is_valid(), form.errors
    assert form.save().login_name == "asha-kumar"


@pytest.mark.django_db
def test_mark_form_rejects_score_above_max(student):
    form = MarkForm({"student": student.id, "subject": "Maths",
                     "assessment": "Quiz", "score": "95", "max_score": "50"})
    assert not form.is_valid()
    assert "Score cannot be greater" in str(form.errors)


@pytest.mark.django_db
def test_mark_form_accepts_valid(student):
    form = MarkForm({"student": student.id, "subject": "Maths",
                     "assessment": "Quiz", "score": "45", "max_score": "50"})
    assert form.is_valid(), form.errors
    assert form.save().score == Decimal("45")


@pytest.mark.django_db
def test_faculty_signup_hashes_password():
    form = FacultySignupForm({"name": "X", "email": "x@y.com",
                              "employee_id": "E1", "password": "longenough1"})
    assert form.is_valid(), form.errors
    f = form.save()
    assert f.password_hash != "longenough1"


def test_faculty_signup_short_password_invalid(db):
    form = FacultySignupForm({"name": "X", "email": "x@y.com",
                              "employee_id": "E1", "password": "short"})
    assert not form.is_valid()


def test_faculty_login_ok_and_case_insensitive_id(faculty):
    form = FacultyLoginForm({"employee_id": " f001 ", "password": "secret123"})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["faculty"] == faculty


def test_faculty_login_wrong_password(faculty):
    form = FacultyLoginForm({"employee_id": "F001", "password": "nope"})
    assert not form.is_valid()


def test_student_login_requires_matching_dob(student):
    assert StudentLoginForm({"login_name": "asha-kumar", "dob": "2004-05-17"}).is_valid()
    assert not StudentLoginForm({"login_name": "asha-kumar", "dob": "2000-01-01"}).is_valid()