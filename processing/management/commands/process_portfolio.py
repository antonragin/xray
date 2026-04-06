from django.core.management.base import BaseCommand, CommandError
from processing.service import process_portfolio


class Command(BaseCommand):
    help = 'Process a portfolio CSV and generate the output bundle'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--output-dir', type=str, default=None)

    def handle(self, *args, **options):
        result = process_portfolio(
            options['csv_path'],
            output_dir=options.get('output_dir'),
        )
        if result.success:
            self.stdout.write(self.style.SUCCESS(f'Bundle: {result.zip_path}'))
            self.stdout.write(f'Run ID: {result.run_id}')
            self.stdout.write(f'Rows: {result.row_count}')
            if result.warnings:
                for w in result.warnings:
                    self.stderr.write(self.style.WARNING(w))
        else:
            for e in result.errors:
                self.stderr.write(self.style.ERROR(e))
            raise CommandError('Processing failed.')
