from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.db.models import Count, Sum
from django.db import transaction
from .models import (
    SOFOM,
    User,
    Client,
    ClientDocument,
    Credit,
    CreditDocument,
    LegalRepresentative,
    SavingsAccount,
    SavingsTransaction,
)

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from .models import Credit, User

def home(request):
    return render(request, "home.html")

def about(request):
    return render(request, "about.html")

def login_view(request):

    if request.user.is_authenticated:
        return redirect("/monarca/dashboard/")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect(
                "/monarca/dashboard/"
            )

        messages.error(
            request,
            "El usuario o la contraseña son incorrectos."
        )

    return render(
        request,
        "login.html"
    )

from django.db import transaction

def sofom_register(request):

    if request.method == "POST":

        with transaction.atomic():

            sofom = SOFOM.objects.create(
                legal_name=request.POST["legal_name"],
                trade_name=request.POST.get("trade_name"),
                rfc=request.POST["rfc"],
                email=request.POST["sofom_email"],
                phone=request.POST["sofom_phone"],
                fiscal_address=request.POST["fiscal_address"],
                tax_regime=request.POST.get("tax_regime"),
                legal_representative_name=request.POST.get("legal_representative_name"),
                status=SOFOM.Status.PENDING
            )

            user = User.objects.create_user(
                username=request.POST["username"],
                first_name=request.POST["first_name"],
                last_name=request.POST["last_name"],
                email=request.POST["email"],
                password=request.POST["password"],
                phone=request.POST["phone"],
                sofom=sofom,
                role=User.Role.ADMIN
            )

        login(request, user)

        return redirect("/monarca/dashboard/")

    return render(request, "sofom_register.html")

@login_required
def dashboard(request):
    sofom = request.user.sofom

    clients = Client.objects.filter(sofom=sofom)
    credits = Credit.objects.filter(sofom=sofom)

    context = {
        "total_clients": clients.count(),
        "active_clients": clients.filter(is_active=True).count(),

        "total_credits": credits.count(),

        "credits_review": credits.filter(
            status=Credit.Status.REVIEW
        ).count(),

        "credits_approved": credits.filter(
            status=Credit.Status.APPROVED
        ).count(),

        "credits_active": credits.filter(
            status=Credit.Status.ACTIVE
        ).count(),

        "credits_paid": credits.filter(
            status=Credit.Status.PAID
        ).count(),

        "amount_requested": credits.aggregate(
            total=Sum("amount_requested")
        )["total"] or 0,

        "amount_approved": credits.aggregate(
            total=Sum("approved_amount")
        )["total"] or 0,

        "recent_credits": credits.select_related(
            "client"
        ).order_by("-created_at")[:5],
    }

    return render(request, "dashboard.html", context)

from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404


@login_required
def credits(request):
    sofom = request.user.sofom

    # Cambio rápido de estado
    if request.method == "POST":
        credit_id = request.POST.get("credit_id")
        new_status = request.POST.get("status")

        credit = get_object_or_404(
            Credit,
            id=credit_id,
            sofom=sofom
        )

        valid_statuses = [
            Credit.Status.REVIEW,
            Credit.Status.APPROVED,
            Credit.Status.ACTIVE,
            Credit.Status.PAID,
        ]

        if new_status in valid_statuses:
            credit.status = new_status
            credit.save(update_fields=["status"])

        return redirect(request.get_full_path())

    credits_qs = Credit.objects.filter(
        sofom=sofom
    ).select_related(
        "client",
        "assigned_to"
    )

    # -----------------------
    # FILTROS
    # -----------------------

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        credits_qs = credits_qs.filter(
            Q(name__icontains=search) |
            Q(client__name__icontains=search) |
            Q(client__rfc__icontains=search)
        )

    if status:
        credits_qs = credits_qs.filter(status=status)

    credits_qs = credits_qs.order_by("-created_at")

    # -----------------------
    # MÉTRICAS GENERALES
    # -----------------------

    all_credits = Credit.objects.filter(sofom=sofom)

    total_credits = all_credits.count()

    credits_review = all_credits.filter(
        status=Credit.Status.REVIEW
    ).count()

    credits_approved = all_credits.filter(
        status=Credit.Status.APPROVED
    ).count()

    credits_active = all_credits.filter(
        status=Credit.Status.ACTIVE
    ).count()

    credits_paid = all_credits.filter(
        status=Credit.Status.PAID
    ).count()

    total_requested = all_credits.aggregate(
        total=Sum("amount_requested")
    )["total"] or 0

    total_approved = all_credits.aggregate(
        total=Sum("approved_amount")
    )["total"] or 0

    context = {
        "credits": credits_qs,

        "total_credits": total_credits,
        "credits_review": credits_review,
        "credits_approved": credits_approved,
        "credits_active": credits_active,
        "credits_paid": credits_paid,

        "total_requested": total_requested,
        "total_approved": total_approved,

        "search": search,
        "selected_status": status,
    }

    return render(request, "credits.html", context)

@login_required
@login_required
def credit_detail(request, credit_id):

    credit = get_object_or_404(
        Credit.objects
        .select_related(
            "client",
            "sofom",
            "assigned_to"
        )
        .prefetch_related(
            "documents"
        ),
        id=credit_id,
        sofom=request.user.sofom
    )


    sofom_users = User.objects.filter(
        sofom=request.user.sofom,
        is_active=True
    ).order_by(
        "first_name",
        "last_name",
        "username"
    )


    if request.method == "POST":

        action = request.POST.get("action")


        if action == "update_credit":

            # --------------------------
            # DATOS GENERALES
            # --------------------------

            credit.name = request.POST.get(
                "name",
                ""
            ).strip()

            credit.status = request.POST.get(
                "status",
                Credit.Status.REVIEW
            )

            credit.payment_frequency = request.POST.get(
                "payment_frequency"
            )


            # --------------------------
            # MONTOS
            # --------------------------

            amount_requested = request.POST.get(
                "amount_requested"
            )

            approved_amount = request.POST.get(
                "approved_amount"
            )

            interest_rate = request.POST.get(
                "interest_rate"
            )

            term_months = request.POST.get(
                "term_months"
            )


            if amount_requested:
                credit.amount_requested = Decimal(
                    amount_requested
                )


            credit.approved_amount = (
                Decimal(approved_amount)
                if approved_amount
                else None
            )


            credit.interest_rate = (
                Decimal(interest_rate)
                if interest_rate
                else None
            )


            credit.term_months = (
                int(term_months)
                if term_months
                else None
            )


            # --------------------------
            # EJECUTIVO
            # --------------------------

            assigned_to_id = request.POST.get(
                "assigned_to"
            )


            if assigned_to_id:

                credit.assigned_to = get_object_or_404(
                    User,
                    id=assigned_to_id,
                    sofom=request.user.sofom,
                    is_active=True
                )

            else:

                credit.assigned_to = None


            # --------------------------
            # FECHAS
            # --------------------------

            credit.start_date = (
                request.POST.get("start_date")
                or None
            )

            credit.end_date = (
                request.POST.get("end_date")
                or None
            )


            # --------------------------
            # DESCRIPCIÓN
            # --------------------------

            credit.description = request.POST.get(
                "description",
                ""
            ).strip()


            credit.full_clean()
            credit.save()


            messages.success(
                request,
                "El crédito fue actualizado correctamente."
            )


            return redirect(
                "credit_detail",
                credit_id=credit.id
            )


    context = {
        "credit": credit,
        "sofom_users": sofom_users,
    }


    return render(
        request,
        "credit_detail.html",
        context
    )


def clients(request):
    sofom = request.user.sofom

    clients = Client.objects.filter(sofom=sofom).order_by("-created_at")

    return render(request, "clients.html", {
        "clients": clients
    })

@login_required
def clients_new(request):

    sofom = request.user.sofom

    if request.method == "POST":

        rfc = request.POST["rfc"].strip().upper()

        # -------------------------
        # CREAR CLIENTE
        # -------------------------

        client = Client(
            sofom=sofom,

            rfc=rfc,

            first_name=request.POST.get(
                "first_name",
                ""
            ).strip(),

            paternal_surname=request.POST.get(
                "paternal_surname",
                ""
            ).strip(),

            maternal_surname=request.POST.get(
                "maternal_surname",
                ""
            ).strip(),

            birth_date=request.POST.get(
                "birth_date"
            ) or None,

            curp=request.POST.get(
                "curp",
                ""
            ).strip().upper(),

            occupation=request.POST.get(
                "occupation",
                ""
            ).strip(),

            business_name=request.POST.get(
                "business_name",
                ""
            ).strip(),

            constitution_date=request.POST.get(
                "constitution_date"
            ) or None,

            email=request.POST["email"].strip(),

            phone=request.POST["phone"].strip(),

            address=request.POST["address"].strip(),

            monthly_income=request.POST.get(
                "monthly_income"
            ) or None,
        )


        # Ejecuta validadores y clean()
        client.full_clean()

        # save() calcula person_type y matrícula
        client.save()


        # ==================================================
        # DOCUMENTOS PERSONA FÍSICA
        # ==================================================

        if client.person_type == Client.PersonType.INDIVIDUAL:

            ine_file = request.FILES.get(
                "ine_file"
            )

            address_file = request.FILES.get(
                "individual_address_file"
            )


            if ine_file:

                ClientDocument.objects.create(
                    client=client,
                    document_type="INE",
                    file=ine_file
                )


            if address_file:

                ClientDocument.objects.create(
                    client=client,
                    document_type="ADDRESS_PROOF",
                    file=address_file
                )


        # ==================================================
        # DOCUMENTOS PERSONA MORAL
        # ==================================================

        elif client.person_type == Client.PersonType.COMPANY:

            constitution_file = request.FILES.get(
                "constitution_file"
            )

            tax_status_file = request.FILES.get(
                "tax_status_file"
            )

            representative_id_file = request.FILES.get(
                "representative_id_file"
            )

            address_file = request.FILES.get(
                "company_address_file"
            )


            if constitution_file:

                ClientDocument.objects.create(
                    client=client,
                    document_type="CONSTITUTION_ACT",
                    file=constitution_file
                )


            if tax_status_file:

                ClientDocument.objects.create(
                    client=client,
                    document_type="TAX_STATUS",
                    file=tax_status_file
                )


            if representative_id_file:

                ClientDocument.objects.create(
                    client=client,
                    document_type="LEGAL_REPRESENTATIVE_ID",
                    file=representative_id_file
                )


            if address_file:

                ClientDocument.objects.create(
                    client=client,
                    document_type="ADDRESS_PROOF",
                    file=address_file
                )


        return redirect(
            "clients_detail",
            matricula=client.matricula
        )


    return render(
        request,
        "clients_new.html"
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def settings(request):

    user = request.user
    sofom = user.sofom

    if request.method == "POST":

        action = request.POST.get("action")


        # ==========================
        # PERFIL PERSONAL
        # ==========================

        if action == "update_profile":

            user.first_name = request.POST.get(
                "first_name",
                ""
            ).strip()

            user.last_name = request.POST.get(
                "last_name",
                ""
            ).strip()

            user.email = request.POST.get(
                "email",
                ""
            ).strip()

            user.phone = request.POST.get(
                "phone",
                ""
            ).strip()

            user.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                ]
            )

            messages.success(
                request,
                "Los datos de tu cuenta fueron actualizados."
            )


        # ==========================
        # CONFIGURACIÓN SOFOM
        # ==========================

        elif action == "update_sofom":

            if user.role != User.Role.ADMIN:

                messages.error(
                    request,
                    "No tienes permisos para modificar la institución."
                )

                return redirect(
                    "settings"
                )


            sofom.legal_name = request.POST.get(
                "legal_name",
                ""
            ).strip()

            sofom.trade_name = request.POST.get(
                "trade_name",
                ""
            ).strip()

            sofom.rfc = request.POST.get(
                "rfc",
                ""
            ).strip().upper()

            sofom.email = request.POST.get(
                "email",
                ""
            ).strip()

            sofom.phone = request.POST.get(
                "phone",
                ""
            ).strip()

            sofom.tax_regime = request.POST.get(
                "tax_regime",
                ""
            ).strip()

            sofom.legal_representative_name = request.POST.get(
                "legal_representative_name",
                ""
            ).strip()

            sofom.fiscal_address = request.POST.get(
                "fiscal_address",
                ""
            ).strip()


            sofom.full_clean()
            sofom.save()


            messages.success(
                request,
                "La configuración de la SOFOM fue actualizada."
            )


        return redirect(
            "settings"
        )


    return render(
        request,
        "settings.html"
    )

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):

    logout(request)

    return redirect("/home/")

def sofom_home(request):
    sofom = request.user.sofom

    return render(request, "sofom_home.html", {
        "sofom": sofom
    })

def sofom_home(request):
    sofom = request.user.sofom

    return render(request, "sofom_home.html", {
        "sofom": sofom
    })

def sofom_clients_register(request):

    sofom = request.user.sofom

    if request.method == "POST":

        with transaction.atomic():

            client = Client.objects.create(
                sofom=sofom,
                person_type=request.POST["person_type"],
                name=request.POST["name"],
                rfc=request.POST["rfc"],
                curp=request.POST.get("curp", ""),
                email=request.POST["email"],
                phone=request.POST["phone"],
                address=request.POST["address"],
                birth_date=request.POST.get("birth_date") or None,
                occupation=request.POST.get("occupation", ""),
                monthly_income=request.POST.get("monthly_income") or None,
                is_active=True
            )

            credit = Credit.objects.create(
                sofom=request.user.sofom,
                client=client,
                name=request.POST["name"],
                amount_requested=request.POST["amount_requested"],
                payment_frequency=request.POST["payment_frequency"],
                description=request.POST.get("description", ""),
                status=Credit.Status.REVIEW,
            )

            # INE
            if request.FILES.get("ine_file"):
                ClientDocument.objects.create(
                    client=client,
                    document_type=ClientDocument.DocumentType.INE,
                    file=request.FILES["ine_file"],
                    uploaded_by=request.user
                )

            # ADDRESS
            if request.FILES.get("address_file"):
                ClientDocument.objects.create(
                    client=client,
                    document_type=ClientDocument.DocumentType.ADDRESS,
                    file=request.FILES["address_file"],
                    uploaded_by=request.user
                )

        return redirect("/monarca/clients/")

    return render(request, "sofom_clients_register.html")

@login_required
@login_required
def client_detail_view(request, matricula):

    client = get_object_or_404(
        Client.objects
        .select_related("sofom")
        .prefetch_related(
            "documents",
            "credits"
        ),
        matricula=matricula,
        sofom=request.user.sofom
    )


    savings_account = (
        SavingsAccount.objects
        .filter(
            client=client,
            sofom=request.user.sofom
        )
        .first()
    )


    savings_transactions = []

    if savings_account:

        savings_transactions = (
            savings_account.transactions
            .select_related("created_by")
            .order_by("-created_at")[:20]
        )


    context = {
        "client": client,
        "savings_account": savings_account,
        "savings_transactions": savings_transactions,
    }


    return render(
        request,
        "clients_detail.html",
        context
    )


@login_required
def clients_new_credit(request, matricula):

    client = get_object_or_404(
        Client,
        matricula=matricula,
        sofom=request.user.sofom
    )

    if request.method == "POST":

        Credit.objects.create(
            sofom=request.user.sofom,
            client=client,

            name=request.POST["name"],
            amount_requested=request.POST["amount_requested"],
            payment_frequency=request.POST["payment_frequency"],
            description=request.POST.get(
                "description",
                ""
            ),

            status=Credit.Status.REVIEW
        )

        return redirect(
            "clients_detail",
            matricula=client.matricula
        )

    return render(
        request,
        "clients_new_credit.html",
        {
            "client": client
        }
    )