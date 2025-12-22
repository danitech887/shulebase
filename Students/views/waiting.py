from django.shortcuts import render

from ..models import MasterSchool,StudentInfo


def waiting_page(request):
    students_count = StudentInfo.objects.count()
    schools = MasterSchool.objects.count()

    context = {
        'schools': schools,
        'students': students_count
    }
    return render(request, 'school/waiting.html',context)