from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, ValidationError):
        custom_data = {
            'error': 'validation_error',
            'message': 'Request data failed validation.',
        }
        if isinstance(response.data, dict):
            non_field = response.data.pop('non_field_errors', None)
            if non_field:
                custom_data['non_field_errors'] = non_field
            if response.data:
                custom_data['field_errors'] = response.data
        elif isinstance(response.data, list):
            custom_data['non_field_errors'] = response.data
        response.data = custom_data
    elif response.status_code == 404:
        response.data = {
            'error': 'not_found',
            'message': str(exc.detail) if hasattr(exc, 'detail') else 'Not found.',
        }
    elif response.status_code == 405:
        response.data = {
            'error': 'method_not_allowed',
            'message': 'DELETE is not allowed. Use PATCH with {"active": false} to deactivate.',
        }

    return response
