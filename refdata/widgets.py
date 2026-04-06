import json
from django.forms import Widget
from django.utils.safestring import mark_safe


class WeightedJsonWidget(Widget):
    """Renders a JSON weight dict as editable rows with code dropdown + weight input."""

    template_name = 'refdata/widgets/weighted_json.html'

    def __init__(self, code_model, code_field, attrs=None):
        super().__init__(attrs)
        self.code_model = code_model
        self.code_field = code_field

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = {}
        if not isinstance(value, dict):
            value = value or {}
        codes = list(
            self.code_model.objects.filter(active=True)
            .values_list(self.code_field, flat=True)
            .order_by(self.code_field)
        )
        context['widget'].update({
            'rows': list(value.items()) if value else [],
            'available_codes': codes,
            'field_name': name,
        })
        return context

    def value_from_datadict(self, data, files, name):
        codes = data.getlist(f'{name}_code')
        weights = data.getlist(f'{name}_weight')
        result = {}
        for code, weight in zip(codes, weights):
            code = code.strip()
            weight = weight.strip()
            if code and weight:
                try:
                    result[code] = round(float(weight), 6)
                except ValueError:
                    pass
        return result if result else None
