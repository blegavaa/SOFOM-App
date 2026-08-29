from django.contrib import admin

from .models import (
    SOFOM,
    User,
    Client,
    LegalRepresentative,
    ClientDocument,
    Credit,
    CreditDocument,
)


@admin.register(SOFOM)
class SOFOMAdmin(admin.ModelAdmin):
    list_display = (
        "legal_name",
        "rfc",
        "status",
        "created_at",
    )

    search_fields = (
        "legal_name",
        "trade_name",
        "rfc",
    )

    list_filter = (
        "status",
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "sofom",
        "role",
        "is_active",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )

    list_filter = (
        "role",
        "is_active",
    )


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    list_display = (
        "matricula",
        "name",
        "rfc",
        "person_type",
        "sofom",
        "is_active",
        "created_at",
    )

    search_fields = (
        "matricula",
        "registration_number",
        "rfc",
        "first_name",
        "paternal_surname",
        "maternal_surname",
        "business_name",
        "email",
    )

    list_filter = (
        "person_type",
        "is_active",
        "sofom",
    )

    readonly_fields = (
        "matricula",
        "person_type",
        "created_at",
    )


@admin.register(LegalRepresentative)
class LegalRepresentativeAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "client",
        "rfc",
        "position",
    )

    search_fields = (
        "full_name",
        "rfc",
        "client__matricula",
    )


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "client",
        "document_type",
        "created_at",
    )

    list_filter = (
        "document_type",
    )

    search_fields = (
        "client__matricula",
        "client__rfc",
        "client__first_name",
        "client__paternal_surname",
        "client__business_name",
    )


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "client",
        "amount_requested",
        "approved_amount",
        "status",
        "payment_frequency",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_frequency",
        "sofom",
    )

    search_fields = (
        "name",
        "client__matricula",
        "client__rfc",
        "client__first_name",
        "client__paternal_surname",
        "client__business_name",
    )


@admin.register(CreditDocument)
class CreditDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "credit",
        "document_type",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = (
        "document_type",
    )

    search_fields = (
        "credit__name",
        "credit__client__matricula",
    )