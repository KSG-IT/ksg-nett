from django.contrib import admin

from admissions.models import Admission, Applicant, InternalGroupPriority


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    pass


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    pass


@admin.register(InternalGroupPriority)
class InternalGroupPriorityAdmin(admin.ModelAdmin):
    pass
