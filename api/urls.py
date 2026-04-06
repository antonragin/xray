from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EconomicExposureViewSet, TaxProfileViewSet, IssuerTypeViewSet,
    IssuerViewSet, InstrumentTemplateViewSet,
    SchemaView, BatchInstructionView, ReferenceHealthView,
)

router = DefaultRouter()
router.register(r'economic-exposures', EconomicExposureViewSet, basename='economic-exposure')
router.register(r'tax-profiles', TaxProfileViewSet, basename='tax-profile')
router.register(r'issuer-types', IssuerTypeViewSet, basename='issuer-type')
router.register(r'issuers', IssuerViewSet, basename='issuer')
router.register(r'instrument-templates', InstrumentTemplateViewSet, basename='instrument-template')

urlpatterns = [
    path('schema/', SchemaView.as_view(), name='api-schema'),
    path('batch/instructions/', BatchInstructionView.as_view(), name='batch-instructions'),
    path('health/references/', ReferenceHealthView.as_view(), name='reference-health'),
] + router.urls
