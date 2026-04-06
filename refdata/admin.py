from django.contrib import admin
from .models import (
    EconomicExposure, TaxProfile, IssuerType, Issuer, InstrumentTemplate
)
from .widgets import WeightedJsonWidget


INSTRUCTION_FIELDSET = (
    'Angle Instructions', {
        'classes': ('collapse',),
        'description': 'Instruction text for each report angle.',
        'fields': (
            'instructions_diversification',
            'instructions_liquidity',
            'instructions_fees',
            'instructions_tax',
            'instructions_risk',
            'instructions_performance',
        ),
    }
)

STATUS_FIELDSET = (
    'Status & Timestamps', {
        'fields': ('active', 'created_at', 'updated_at'),
    }
)


class ReferenceBaseAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('active',)
    list_per_page = 50
    actions = ['mark_inactive', 'mark_active']

    def mark_inactive(self, request, queryset):
        count = queryset.update(active=False)
        self.message_user(request, f'{count} records deactivated.')
    mark_inactive.short_description = 'Deactivate selected records'

    def mark_active(self, request, queryset):
        count = queryset.update(active=True)
        self.message_user(request, f'{count} records activated.')
    mark_active.short_description = 'Activate selected records'

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EconomicExposure)
class EconomicExposureAdmin(ReferenceBaseAdmin):
    list_display = ('exposure_code', 'name', 'exposure_group', 'active')
    list_filter = ('active', 'exposure_group')
    search_fields = ('exposure_code', 'name')
    fieldsets = [
        (None, {'fields': ('exposure_code', 'name', 'exposure_group', 'description')}),
        INSTRUCTION_FIELDSET,
        STATUS_FIELDSET,
    ]


@admin.register(TaxProfile)
class TaxProfileAdmin(ReferenceBaseAdmin):
    list_display = ('tax_profile_code', 'name', 'active')
    search_fields = ('tax_profile_code', 'name')
    fieldsets = [
        (None, {'fields': ('tax_profile_code', 'name', 'description')}),
        INSTRUCTION_FIELDSET,
        STATUS_FIELDSET,
    ]


@admin.register(IssuerType)
class IssuerTypeAdmin(ReferenceBaseAdmin):
    list_display = ('issuer_type_code', 'name', 'active')
    search_fields = ('issuer_type_code', 'name')
    fieldsets = [
        (None, {'fields': ('issuer_type_code', 'name', 'description')}),
        INSTRUCTION_FIELDSET,
        STATUS_FIELDSET,
    ]


@admin.register(Issuer)
class IssuerAdmin(ReferenceBaseAdmin):
    list_display = ('issuer_code', 'name', 'issuer_type', 'active')
    list_filter = ('active', 'issuer_type')
    search_fields = ('issuer_code', 'name')
    autocomplete_fields = ('issuer_type',)
    fieldsets = [
        (None, {'fields': ('issuer_code', 'name', 'issuer_type', 'description')}),
        INSTRUCTION_FIELDSET,
        STATUS_FIELDSET,
    ]


@admin.register(InstrumentTemplate)
class InstrumentTemplateAdmin(ReferenceBaseAdmin):
    list_display = (
        'template_code', 'short_name', 'instrument_kind',
        'tax_profile', 'active',
    )
    list_filter = ('active', 'instrument_kind', 'requires_expiry_date')
    search_fields = ('template_code', 'short_name', 'long_name', 'cnpj')
    autocomplete_fields = (
        'primary_economic_exposure', 'tax_profile',
        'primary_issuer_type', 'issuer',
    )
    actions = ['mark_inactive', 'mark_active', 'clone_templates']

    fieldsets = [
        ('Identification', {
            'fields': (
                'template_code', 'instrument_kind', 'short_name',
                'long_name', 'cnpj',
            ),
        }),
        ('Listing & Type Flags', {
            'fields': (
                'b3_listed', 'is_bdr', 'has_fgc',
                'requires_expiry_date', 'requires_issuer_or_issuer_type',
            ),
        }),
        ('Fees', {
            'fields': ('yearly_fee_pct', 'performance_fee_pct'),
        }),
        ('Economic Exposure', {
            'description': 'Set EITHER primary exposure OR weighted JSON, not both.',
            'fields': (
                'primary_economic_exposure',
                'economic_exposure_weights_json',
            ),
        }),
        ('Tax Profile', {
            'fields': ('tax_profile',),
        }),
        ('Issuer Linkage', {
            'description': 'Optional issuer or issuer type linkage.',
            'fields': (
                'issuer', 'primary_issuer_type',
                'issuer_type_weights_json',
            ),
        }),
        INSTRUCTION_FIELDSET,
        STATUS_FIELDSET,
    ]

    def clone_templates(self, request, queryset):
        for obj in queryset:
            obj.pk = None
            obj.template_code = f'{obj.template_code}_copy'
            obj.save()
            self.message_user(
                request,
                f'Cloned as "{obj.template_code}". Change the template_code before final save.'
            )
    clone_templates.short_description = 'Duplicate selected templates'

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'economic_exposure_weights_json':
            kwargs['widget'] = WeightedJsonWidget(
                code_model=EconomicExposure, code_field='exposure_code',
            )
        elif db_field.name == 'issuer_type_weights_json':
            kwargs['widget'] = WeightedJsonWidget(
                code_model=IssuerType, code_field='issuer_type_code',
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)
