from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
import re
import unicodedata
from django.core.exceptions import ValidationError


# Validators
rfc_validator = RegexValidator(
    regex=r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$",
    message="Invalid RFC format."
)

curp_validator = RegexValidator(
    regex=r"^[A-Z]{4}\d{6}[A-Z]{6}[A-Z0-9]{2}$",
    message="Invalid CURP format."
)


class SOFOM(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Sin revisión"
        REVIEWING = "REVIEWING", "En revisión"
        APPROVED = "APPROVED", "Aprobada"
        REJECTED = "REJECTED", "Rechazada"

    legal_name = models.CharField(max_length=255)
    trade_name = models.CharField(max_length=255, blank=True)

    rfc = models.CharField(
        max_length=13,
        unique=True,
        validators=[rfc_validator]
    )

    email = models.EmailField()
    phone = models.CharField(max_length=20)

    fiscal_address = models.TextField()

    tax_regime = models.CharField(
        max_length=255,
        blank=True
    )

    legal_representative_name = models.CharField(
        max_length=255,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.legal_name


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = "SOFOM_ADMIN", "SOFOM Administrator"
        CREDIT_EXECUTIVE = "CREDIT_EXECUTIVE", "Credit Executive"

    sofom = models.ForeignKey(
        SOFOM,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.CREDIT_EXECUTIVE
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.get_full_name() or self.username


class Client(models.Model):

    class PersonType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Persona física"
        COMPANY = "COMPANY", "Persona moral"

    sofom = models.ForeignKey(
        SOFOM,
        on_delete=models.PROTECT,
        related_name="clients"
    )

    # =========================
    # IDENTIFICADORES
    # =========================

    registration_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Número de registro"
    )

    matricula = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        editable=False,
        verbose_name="Matrícula"
    )

    # =========================
    # TIPO DE PERSONA
    # =========================

    person_type = models.CharField(
        max_length=20,
        choices=PersonType.choices,
        editable=False
    )

    # =========================
    # PERSONA FÍSICA
    # =========================

    first_name = models.CharField(
        max_length=100,
        blank=True
    )

    paternal_surname = models.CharField(
        max_length=100,
        blank=True
    )

    maternal_surname = models.CharField(
        max_length=100,
        blank=True
    )

    birth_date = models.DateField(
        null=True,
        blank=True
    )

    # =========================
    # PERSONA MORAL
    # =========================

    business_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Razón social"
    )

    constitution_date = models.DateField(
        null=True,
        blank=True
    )

    # =========================
    # FISCAL
    # =========================

    rfc = models.CharField(
        max_length=13,
        validators=[rfc_validator]
    )

    curp = models.CharField(
        max_length=18,
        validators=[curp_validator],
        blank=True
    )

    # =========================
    # CONTACTO
    # =========================

    email = models.EmailField()

    phone = models.CharField(
        max_length=20
    )

    address = models.TextField()

    occupation = models.CharField(
        max_length=255,
        blank=True
    )

    monthly_income = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sofom", "rfc"],
                name="unique_client_rfc_per_sofom"
            ),
            models.UniqueConstraint(
                fields=["sofom", "matricula"],
                name="unique_client_matricula_per_sofom"
            ),
        ]

    # =========================
    # NOMBRE MOSTRADO
    # =========================

    @property
    def name(self):

        if self.person_type == self.PersonType.COMPANY:
            return self.business_name

        return " ".join(
            part for part in [
                self.first_name,
                self.paternal_surname,
                self.maternal_surname
            ]
            if part
        )

    @property
    def full_name(self):
        return self.name

    # =========================
    # TIPO POR RFC
    # =========================

    def detect_person_type(self):

        rfc = (self.rfc or "").strip().upper()

        if len(rfc) == 13:
            return self.PersonType.INDIVIDUAL

        if len(rfc) == 12:
            return self.PersonType.COMPANY

        raise ValidationError(
            "El RFC debe tener 13 caracteres para persona física "
            "o 12 para persona moral."
        )

    # =========================
    # NORMALIZACIÓN
    # =========================

    @staticmethod
    def normalize_text(value):

        value = value or ""

        normalized = unicodedata.normalize(
            "NFD",
            value
        )

        normalized = "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        )

        return re.sub(
            r"[^A-Za-z]",
            "",
            normalized
        ).upper()

    # =========================
    # MATRÍCULA
    # =========================

    def generate_matricula(self):

        if self.person_type == self.PersonType.INDIVIDUAL:

            if not self.first_name:
                raise ValidationError(
                    "Se requiere el nombre para generar la matrícula."
                )

            if not self.paternal_surname:
                raise ValidationError(
                    "Se requiere el apellido paterno."
                )

            if not self.birth_date:
                raise ValidationError(
                    "Se requiere la fecha de nacimiento."
                )

            first_name = self.normalize_text(
                self.first_name
            )

            surname = self.normalize_text(
                self.paternal_surname
            )

            letters = first_name[:1] + surname[:2]

            date = self.birth_date.strftime("%d%m%y")

        else:

            if not self.business_name:
                raise ValidationError(
                    "Se requiere la razón social."
                )

            if not self.constitution_date:
                raise ValidationError(
                    "Se requiere la fecha de constitución."
                )

            business_name = self.normalize_text(
                self.business_name
            )

            letters = business_name[:3]

            date = self.constitution_date.strftime("%d%m%y")

        base = f"{letters}{date}"

        matricula = base
        counter = 1

        while Client.objects.filter(
            sofom=self.sofom,
            matricula=matricula
        ).exclude(pk=self.pk).exists():

            matricula = f"{base}{counter:02d}"
            counter += 1

        return matricula

    # =========================
    # GUARDADO
    # =========================

    def save(self, *args, **kwargs):

        self.rfc = (self.rfc or "").strip().upper()

        self.person_type = self.detect_person_type()

        if not self.matricula:
            self.matricula = self.generate_matricula()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matricula} - {self.name}"


class LegalRepresentative(models.Model):

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="legal_representatives"
    )

    full_name = models.CharField(
        max_length=255
    )

    rfc = models.CharField(
        max_length=13,
        validators=[rfc_validator]
    )

    curp = models.CharField(
        max_length=18,
        validators=[curp_validator],
        blank=True
    )

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField()

    position = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return self.full_name



class ClientDocument(models.Model):

    class DocumentType(models.TextChoices):

        # PERSONA FÍSICA
        INE = "INE", "Identificación oficial"

        # PERSONA MORAL
        CONSTITUTION_ACT = (
            "CONSTITUTION_ACT",
            "Acta constitutiva"
        )

        TAX_STATUS = (
            "TAX_STATUS",
            "Constancia de situación fiscal"
        )

        LEGAL_REPRESENTATIVE_ID = (
            "LEGAL_REPRESENTATIVE_ID",
            "Identificación del representante legal"
        )

        # AMBOS
        ADDRESS_PROOF = (
            "ADDRESS_PROOF",
            "Comprobante de domicilio"
        )


    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices
    )

    file = models.FileField(
        upload_to="client_documents/"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return (
            f"{self.client.matricula} - "
            f"{self.get_document_type_display()}"
        )

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


# ==========================================================
# CUENTA DE AHORRO
# ==========================================================

class SavingsAccount(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        FROZEN = "FROZEN", "Bloqueada"
        CLOSED = "CLOSED", "Cerrada"

    sofom = models.ForeignKey(
        "SOFOM",
        on_delete=models.PROTECT,
        related_name="savings_accounts"
    )

    client = models.ForeignKey(
        "Client",
        on_delete=models.PROTECT,
        related_name="savings_accounts"
    )

    account_number = models.CharField(
        max_length=30
    )

    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00"))
        ]
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    opened_at = models.DateTimeField(
        auto_now_add=True
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_savings_accounts",
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-opened_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["sofom", "account_number"],
                name="unique_savings_account_per_sofom"
            )
        ]

    def __str__(self):
        return f"{self.account_number} - {self.client}"

# ==========================================================
# MOVIMIENTOS DE AHORRO
# ==========================================================

class SavingsTransaction(models.Model):

    class TransactionType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Depósito"
        WITHDRAWAL = "WITHDRAWAL", "Retiro"
        INTEREST = "INTEREST", "Interés"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ]
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="savings_transactions"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} "
            f"${self.amount} - {self.account.account_number}"
        )

class Credit(models.Model):

    class Status(models.TextChoices):
        REVIEW = "REVIEW", "En revisión"
        APPROVED = "APPROVED", "Aprobado"
        ACTIVE = "ACTIVE", "Activo"
        PAID = "PAID", "Pagado"


    class PaymentFrequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Semanal"
        BIWEEKLY = "BIWEEKLY", "Quincenal"
        MONTHLY = "MONTHLY", "Mensual"


    sofom = models.ForeignKey(
        SOFOM,
        on_delete=models.PROTECT,
        related_name="credits"
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="credits"
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_credits"
    )

    name = models.CharField(max_length=255)

    amount_requested = models.DecimalField(
        max_digits=16,
        decimal_places=2
    )

    approved_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True
    )

    # 🔥 CAMBIO IMPORTANTE
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual interest rate percentage (Before IVA)."
    )

    # 🔥 CAMBIO IMPORTANTE
    term_months = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    payment_frequency = models.CharField(
        max_length=20,
        choices=PaymentFrequency.choices
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REVIEW
    )

    description = models.TextField(blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CreditDocument(models.Model):

    class DocumentType(models.TextChoices):
        APPLICATION = "APPLICATION", "Loan Application"
        CONTRACT = "CONTRACT", "Contract"
        PROMISSORY_NOTE = "PROMISSORY_NOTE", "Promissory Note"
        PAYMENT_TABLE = "PAYMENT_TABLE", "Payment Schedule"
        OTHER = "OTHER", "Other"


    credit = models.ForeignKey(
        Credit,
        on_delete=models.PROTECT,
        related_name="documents"
    )

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices
    )

    file = models.FileField(
        upload_to="credit_documents/"
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.document_type