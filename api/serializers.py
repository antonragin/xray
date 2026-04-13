from rest_framework import serializers
from refdata.models import (
    EconomicExposure, TaxProfile, IssuerType, Issuer, InstrumentTemplate,
    _validate_weights_json,
)
from django.core.exceptions import ValidationError as DjangoValidationError


class EconomicExposureSerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicExposure
        fields = [
            'exposure_code', 'name', 'exposure_group', 'description',
            'instructions_diversification', 'instructions_liquidity',
            'instructions_fees', 'instructions_tax',
            'instructions_risk', 'instructions_performance',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_exposure_code(self, value):
        if self.instance and self.instance.exposure_code != value:
            raise serializers.ValidationError('This field is immutable after creation.')
        return value


class TaxProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxProfile
        fields = [
            'tax_profile_code', 'name', 'description',
            'instructions_diversification', 'instructions_liquidity',
            'instructions_fees', 'instructions_tax',
            'instructions_risk', 'instructions_performance',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_tax_profile_code(self, value):
        if self.instance and self.instance.tax_profile_code != value:
            raise serializers.ValidationError('This field is immutable after creation.')
        return value


class IssuerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssuerType
        fields = [
            'issuer_type_code', 'name', 'description',
            'instructions_diversification', 'instructions_liquidity',
            'instructions_fees', 'instructions_tax',
            'instructions_risk', 'instructions_performance',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_issuer_type_code(self, value):
        if self.instance and self.instance.issuer_type_code != value:
            raise serializers.ValidationError('This field is immutable after creation.')
        return value


class IssuerSerializer(serializers.ModelSerializer):
    issuer_type_code = serializers.SlugRelatedField(
        source='issuer_type',
        slug_field='issuer_type_code',
        queryset=IssuerType.objects.filter(active=True),
    )

    class Meta:
        model = Issuer
        fields = [
            'issuer_code', 'name', 'issuer_type_code', 'description',
            'instructions_diversification', 'instructions_liquidity',
            'instructions_fees', 'instructions_tax',
            'instructions_risk', 'instructions_performance',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_issuer_code(self, value):
        if self.instance and self.instance.issuer_code != value:
            raise serializers.ValidationError('This field is immutable after creation.')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['issuer_type'] = {
            'issuer_type_code': instance.issuer_type.issuer_type_code,
            'name': instance.issuer_type.name,
        }
        return data


class InstrumentTemplateSerializer(serializers.ModelSerializer):
    tax_profile_code = serializers.SlugRelatedField(
        source='tax_profile',
        slug_field='tax_profile_code',
        queryset=TaxProfile.objects.filter(active=True),
    )
    primary_economic_exposure_code = serializers.SlugRelatedField(
        source='primary_economic_exposure',
        slug_field='exposure_code',
        queryset=EconomicExposure.objects.filter(active=True),
        required=False, allow_null=True,
    )
    primary_issuer_type_code = serializers.SlugRelatedField(
        source='primary_issuer_type',
        slug_field='issuer_type_code',
        queryset=IssuerType.objects.filter(active=True),
        required=False, allow_null=True,
    )
    issuer_code = serializers.SlugRelatedField(
        source='issuer',
        slug_field='issuer_code',
        queryset=Issuer.objects.filter(active=True),
        required=False, allow_null=True,
    )

    class Meta:
        model = InstrumentTemplate
        fields = [
            'template_code', 'instrument_kind', 'short_name', 'long_name',
            'cnpj', 'b3_listed', 'is_bdr',
            'yearly_fee_pct', 'performance_fee_pct', 'has_fgc',
            'withdrawal_days',
            'requires_expiry_date', 'requires_issuer_or_issuer_type',
            'primary_economic_exposure_code', 'economic_exposure_weights_json',
            'tax_profile_code',
            'primary_issuer_type_code', 'issuer_type_weights_json',
            'issuer_code',
            'instructions_diversification', 'instructions_liquidity',
            'instructions_fees', 'instructions_tax',
            'instructions_risk', 'instructions_performance',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_template_code(self, value):
        if self.instance and self.instance.template_code != value:
            raise serializers.ValidationError('This field is immutable after creation.')
        return value

    def validate(self, attrs):
        primary_exp = attrs.get(
            'primary_economic_exposure',
            getattr(self.instance, 'primary_economic_exposure', None) if self.instance else None,
        )
        weights_exp = attrs.get(
            'economic_exposure_weights_json',
            getattr(self.instance, 'economic_exposure_weights_json', None) if self.instance else None,
        )
        has_primary = primary_exp is not None
        has_weights = weights_exp is not None
        # For partial updates, only validate if either field is being changed
        if not self.partial or 'primary_economic_exposure' in attrs or 'economic_exposure_weights_json' in attrs:
            if has_primary == has_weights:
                raise serializers.ValidationError(
                    'Exactly one of primary_economic_exposure_code or '
                    'economic_exposure_weights_json must be provided.'
                )
        if has_weights and weights_exp:
            try:
                _validate_weights_json(
                    weights_exp, EconomicExposure, 'exposure_code',
                    'economic_exposure_weights_json',
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))

        issuer_type_wj = attrs.get(
            'issuer_type_weights_json',
            getattr(self.instance, 'issuer_type_weights_json', None) if self.instance else None,
        )
        if issuer_type_wj:
            try:
                _validate_weights_json(
                    issuer_type_wj, IssuerType, 'issuer_type_code',
                    'issuer_type_weights_json',
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.tax_profile:
            data['tax_profile'] = {
                'tax_profile_code': instance.tax_profile.tax_profile_code,
                'name': instance.tax_profile.name,
            }
        if instance.primary_economic_exposure:
            data['primary_economic_exposure'] = {
                'exposure_code': instance.primary_economic_exposure.exposure_code,
                'name': instance.primary_economic_exposure.name,
            }
        if instance.primary_issuer_type:
            data['primary_issuer_type'] = {
                'issuer_type_code': instance.primary_issuer_type.issuer_type_code,
                'name': instance.primary_issuer_type.name,
            }
        if instance.issuer:
            data['issuer'] = {
                'issuer_code': instance.issuer.issuer_code,
                'name': instance.issuer.name,
            }
        return data
