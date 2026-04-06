import json
from django.core.management.base import BaseCommand, CommandError
from processing.validators import validate_csv


class Command(BaseCommand):
    help = 'Validate a portfolio CSV against reference data'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--json', action='store_true', help='Output as JSON')

    def handle(self, *args, **options):
        result = validate_csv(options['csv_path'])

        if options['json']:
            out = {
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'row_count': result.row_count,
                'total_weight': result.total_weight,
            }
            self.stdout.write(json.dumps(out, indent=2))
            return

        if result.warnings:
            for w in result.warnings:
                self.stderr.write(self.style.WARNING(w))

        if result.is_valid:
            self.stdout.write(self.style.SUCCESS(
                f'Validation passed. {result.row_count} rows, total weight {result.total_weight:.6f}.'
            ))
        else:
            for e in result.errors:
                self.stderr.write(self.style.ERROR(e))
            raise CommandError('Validation failed.')
