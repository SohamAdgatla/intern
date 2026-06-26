from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from clinical.models import (
    AuditLog,
    CodedConcept,
    Condition,
    MedicationStatement,
    Observation,
    ObservationAttachment,
    PatientProfile,
    PatientUser,
)


@admin.register(PatientUser)
class PatientUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Clinical Portal", {"fields": ("role", "fhir_id")}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("role",)}),)


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user_id", "gender", "birth_date", "active", "updated_at")
    list_filter = ("active", "gender")


@admin.register(CodedConcept)
class CodedConceptAdmin(admin.ModelAdmin):
    list_display = ("display", "system", "code", "version")
    search_fields = ("display", "code")


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("patient", "code", "value_quantity", "value_unit", "effective_datetime", "status")
    list_filter = ("category", "status")
    date_hierarchy = "effective_datetime"


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ("patient", "code", "clinical_status", "effective_datetime")
    list_filter = ("clinical_status", "verification_status")


@admin.register(MedicationStatement)
class MedicationStatementAdmin(admin.ModelAdmin):
    list_display = ("patient", "medication_code", "status", "adherence_status", "period_start")
    list_filter = ("status", "adherence_status")


@admin.register(ObservationAttachment)
class ObservationAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "capture_source", "uploaded_at", "observation")
    list_filter = ("capture_source",)
    readonly_fields = ("fhir_id", "uploaded_at", "file_size_bytes")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "patient", "action", "resource_type", "status_code")
    list_filter = ("action", "resource_type")
    date_hierarchy = "timestamp"
    readonly_fields = [f.name for f in AuditLog._meta.fields]
