from django.db import models
from django.core.exceptions import ValidationError


class ReferenceBase(models.Model):
    """Abstract base for all 5 reference tables."""
    instructions_diversification = models.TextField(blank=True, default='')
    instructions_liquidity = models.TextField(blank=True, default='')
    instructions_fees = models.TextField(blank=True, default='')
    instructions_tax = models.TextField(blank=True, default='')
    instructions_risk = models.TextField(blank=True, default='')
    instructions_performance = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    INSTRUCTION_FIELDS = [
        'instructions_diversification',
        'instructions_liquidity',
        'instructions_fees',
        'instructions_tax',
        'instructions_risk',
        'instructions_performance',
    ]

    class Meta:
        abstract = True


class EconomicExposure(ReferenceBase):
    EXPOSURE_GROUP_CHOICES = [
        ('fixed_income', 'Fixed Income'),
        ('equity', 'Equity'),
        ('real_estate', 'Real Estate'),
        ('crypto', 'Crypto'),
        ('precious_metals', 'Precious Metals'),
        ('undetermined', 'Undetermined'),
    ]
    exposure_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    exposure_group = models.CharField(max_length=32, choices=EXPOSURE_GROUP_CHOICES)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'economic_exposure'
        ordering = ['exposure_code']
        verbose_name_plural = 'Economic Exposures'

    def __str__(self):
        return f"{self.exposure_code} — {self.name}"


class TaxProfile(ReferenceBase):
    tax_profile_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'tax_profile'
        ordering = ['tax_profile_code']

    def __str__(self):
        return f"{self.tax_profile_code} — {self.name}"


class IssuerType(ReferenceBase):
    issuer_type_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'issuer_type'
        ordering = ['issuer_type_code']

    def __str__(self):
        return f"{self.issuer_type_code} — {self.name}"


class Issuer(ReferenceBase):
    issuer_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    issuer_type = models.ForeignKey(
        IssuerType, on_delete=models.PROTECT, related_name='issuers'
    )
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'issuer'
        ordering = ['issuer_code']
        indexes = [
            models.Index(fields=['issuer_type'], name='idx_issuer_issuer_type_id'),
        ]

    def __str__(self):
        return f"{self.issuer_code} — {self.name}"


class InstrumentTemplate(ReferenceBase):
    INSTRUMENT_KIND_CHOICES = [
        ('listed', 'Listed'),
        ('fixed_income', 'Fixed Income'),
        ('fund', 'Fund'),
        ('crypto', 'Crypto'),
        ('other', 'Other'),
    ]

    template_code = models.CharField(max_length=64, unique=True)
    instrument_kind = models.CharField(max_length=32, choices=INSTRUMENT_KIND_CHOICES)
    short_name = models.CharField(max_length=255)
    long_name = models.CharField(max_length=512, blank=True, default='')
    cnpj = models.CharField(max_length=32, blank=True, default='')
    b3_listed = models.BooleanField(null=True, blank=True)
    is_bdr = models.BooleanField(null=True, blank=True)
    yearly_fee_pct = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    performance_fee_pct = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    has_fgc = models.BooleanField(null=True, blank=True)
    withdrawal_days = models.IntegerField(
        null=True, blank=True,
        help_text='Withdrawal/redemption days (T+N). E.g., 0=same day, 1=T+1, 30=T+30.'
    )
    requires_expiry_date = models.BooleanField(default=False)
    requires_issuer_or_issuer_type = models.BooleanField(default=False)

    primary_economic_exposure = models.ForeignKey(
        EconomicExposure, on_delete=models.PROTECT,
        null=True, blank=True, related_name='templates_primary'
    )
    economic_exposure_weights_json = models.JSONField(null=True, blank=True)

    tax_profile = models.ForeignKey(
        TaxProfile, on_delete=models.PROTECT, related_name='templates'
    )

    primary_issuer_type = models.ForeignKey(
        IssuerType, on_delete=models.PROTECT,
        null=True, blank=True, related_name='templates_primary'
    )
    issuer_type_weights_json = models.JSONField(null=True, blank=True)

    issuer = models.ForeignKey(
        Issuer, on_delete=models.PROTECT,
        null=True, blank=True, related_name='templates'
    )

    class Meta:
        db_table = 'instrument_template'
        ordering = ['template_code']
        indexes = [
            models.Index(fields=['tax_profile'], name='idx_it_tax_profile_id'),
            models.Index(fields=['primary_economic_exposure'], name='idx_it_prim_econ_exp_id'),
            models.Index(fields=['primary_issuer_type'], name='idx_it_prim_issuer_type_id'),
            models.Index(fields=['issuer'], name='idx_it_issuer_id'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        primary_economic_exposure__isnull=False,
                        economic_exposure_weights_json__isnull=True,
                    ) | models.Q(
                        primary_economic_exposure__isnull=True,
                        economic_exposure_weights_json__isnull=False,
                    )
                ),
                name='chk_exposure_source',
            ),
            models.CheckConstraint(
                condition=models.Q(yearly_fee_pct__isnull=True) | models.Q(yearly_fee_pct__gte=0),
                name='chk_yearly_fee_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(performance_fee_pct__isnull=True) | models.Q(performance_fee_pct__gte=0),
                name='chk_performance_fee_non_negative',
            ),
        ]

    def __str__(self):
        return f"{self.template_code} — {self.short_name}"

    def clean(self):
        super().clean()
        has_primary = self.primary_economic_exposure_id is not None
        has_weights = self.economic_exposure_weights_json is not None
        if has_primary == has_weights:
            raise ValidationError(
                'Exactly one of primary_economic_exposure or '
                'economic_exposure_weights_json must be set.'
            )
        if has_weights:
            _validate_weights_json(
                self.economic_exposure_weights_json,
                EconomicExposure, 'exposure_code',
                'economic_exposure_weights_json',
            )
        if self.issuer_type_weights_json:
            _validate_weights_json(
                self.issuer_type_weights_json,
                IssuerType, 'issuer_type_code',
                'issuer_type_weights_json',
            )
        if self.yearly_fee_pct is not None and self.yearly_fee_pct < 0:
            raise ValidationError({'yearly_fee_pct': 'Must be non-negative.'})
        if self.performance_fee_pct is not None and self.performance_fee_pct < 0:
            raise ValidationError({'performance_fee_pct': 'Must be non-negative.'})
        # Fund-specific mandatory fields
        if self.instrument_kind == 'fund':
            errors = {}
            if not self.cnpj or not self.cnpj.strip():
                errors['cnpj'] = 'CNPJ is required for funds.'
            if self.yearly_fee_pct is None:
                errors['yearly_fee_pct'] = 'Administration fee (yearly_fee_pct) is required for funds.'
            if self.withdrawal_days is None:
                errors['withdrawal_days'] = 'Withdrawal days (T+N) is required for funds.'
            if errors:
                raise ValidationError(errors)


def _validate_weights_json(data, model_class, code_field, field_name):
    if not isinstance(data, dict):
        raise ValidationError({field_name: 'Must be a JSON object.'})
    if not data:
        raise ValidationError({field_name: 'Must not be empty.'})
    total = 0.0
    for code, weight in data.items():
        if not isinstance(weight, (int, float)):
            raise ValidationError(
                {field_name: f'Weight for "{code}" must be numeric.'}
            )
        if weight <= 0:
            raise ValidationError(
                {field_name: f'Weight for "{code}" must be positive.'}
            )
        if not model_class.objects.filter(**{code_field: code, 'active': True}).exists():
            raise ValidationError(
                {field_name: f'Code "{code}" not found (or inactive) in {model_class.__name__}.'}
            )
        total += weight
    if abs(total - 1.0) > 0.0005:
        raise ValidationError(
            {field_name: f'Weights sum to {total:.4f}, must be 1.0 (tolerance 0.0005).'}
        )
