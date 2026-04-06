from django.db import migrations


def seed_reference_data(apps, schema_editor):
    EconomicExposure = apps.get_model('refdata', 'EconomicExposure')
    TaxProfile = apps.get_model('refdata', 'TaxProfile')
    IssuerType = apps.get_model('refdata', 'IssuerType')

    exposures = [
        ('fi_cdi_br', 'CDI Brazil', 'fixed_income'),
        ('fi_ipca_br', 'IPCA Brazil', 'fixed_income'),
        ('fi_prefixado_br', 'Prefixado Brazil', 'fixed_income'),
        ('fi_international', 'Fixed Income International', 'fixed_income'),
        ('eq_br', 'Equity Brazil', 'equity'),
        ('eq_international', 'Equity International', 'equity'),
        ('re_br', 'Real Estate Brazil', 'real_estate'),
        ('re_international', 'Real Estate International', 'real_estate'),
        ('crypto', 'Crypto', 'crypto'),
    ]
    for code, name, group in exposures:
        EconomicExposure.objects.get_or_create(
            exposure_code=code,
            defaults={'name': name, 'exposure_group': group},
        )

    tax_profiles = [
        ('general', 'General'),
        ('tax_exempt', 'Tax Exempt'),
        ('taxable_no_come_cotas', 'Taxable No Come-Cotas'),
        ('previdencia', 'Previdencia'),
    ]
    for code, name in tax_profiles:
        TaxProfile.objects.get_or_create(
            tax_profile_code=code, defaults={'name': name},
        )

    issuer_types = [
        ('br_government', 'Brazilian Government'),
        ('br_bank', 'Brazilian Bank'),
        ('br_infrastructure', 'Brazilian Infrastructure'),
        ('br_other', 'Brazilian Other'),
        ('nonbr_government', 'Non-Brazilian Government'),
        ('nonbr_other', 'Non-Brazilian Other'),
    ]
    for code, name in issuer_types:
        IssuerType.objects.get_or_create(
            issuer_type_code=code, defaults={'name': name},
        )


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('refdata', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(seed_reference_data, reverse_seed),
    ]
