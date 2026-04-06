import django_filters
from refdata.models import (
    EconomicExposure, TaxProfile, IssuerType, Issuer, InstrumentTemplate
)


class EconomicExposureFilter(django_filters.FilterSet):
    class Meta:
        model = EconomicExposure
        fields = {
            'active': ['exact'],
            'exposure_group': ['exact'],
        }


class TaxProfileFilter(django_filters.FilterSet):
    class Meta:
        model = TaxProfile
        fields = {'active': ['exact']}


class IssuerTypeFilter(django_filters.FilterSet):
    class Meta:
        model = IssuerType
        fields = {'active': ['exact']}


class IssuerFilter(django_filters.FilterSet):
    issuer_type_code = django_filters.CharFilter(
        field_name='issuer_type__issuer_type_code',
    )

    class Meta:
        model = Issuer
        fields = {'active': ['exact']}


class InstrumentTemplateFilter(django_filters.FilterSet):
    tax_profile_code = django_filters.CharFilter(
        field_name='tax_profile__tax_profile_code',
    )
    primary_economic_exposure_code = django_filters.CharFilter(
        field_name='primary_economic_exposure__exposure_code',
    )
    issuer_code = django_filters.CharFilter(
        field_name='issuer__issuer_code',
    )

    class Meta:
        model = InstrumentTemplate
        fields = {
            'active': ['exact'],
            'instrument_kind': ['exact'],
            'b3_listed': ['exact'],
            'is_bdr': ['exact'],
            'has_fgc': ['exact'],
            'requires_expiry_date': ['exact'],
        }
