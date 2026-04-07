import os
from django.template import Template, Context


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Portfolio X-Ray — {{ run_id }}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 1100px; margin: 2em auto; padding: 0 1em; color: #333; }
  h1 { color: #2C5F8A; border-bottom: 2px solid #4A90D9; padding-bottom: 0.3em; }
  h2 { color: #4A90D9; margin-top: 2em; }
  .cards { display: flex; gap: 1em; flex-wrap: wrap; margin: 1em 0; }
  .card { background: #f5f8fc; border: 1px solid #d0dce8; border-radius: 8px;
          padding: 1em 1.5em; min-width: 150px; }
  .card .value { font-size: 1.8em; font-weight: bold; color: #2C5F8A; }
  .card .label { font-size: 0.85em; color: #666; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  th, td { border: 1px solid #d0dce8; padding: 0.5em 0.8em; text-align: left; font-size: 0.9em; }
  th { background: #4A90D9; color: white; }
  tr:nth-child(even) { background: #f5f8fc; }
  .pct { text-align: right; }
  .chart-container { margin: 1em 0; }
  .chart-container img, .chart-container svg { max-width: 100%; height: auto; }
  details { margin: 0.5em 0; }
  details summary { cursor: pointer; color: #4A90D9; font-weight: bold; }
  pre { background: #f5f8fc; padding: 1em; border-radius: 4px; overflow-x: auto;
        font-size: 0.85em; white-space: pre-wrap; }
  .validation-ok { color: green; font-weight: bold; }
  .validation-warn { color: orange; }
  .download-links a { display: inline-block; margin: 0.3em 0.5em; padding: 0.4em 1em;
                       background: #4A90D9; color: white; border-radius: 4px; text-decoration: none; }
</style>
</head>
<body>
<h1>Portfolio X-Ray Preview</h1>
<p>Run: <strong>{{ run_id }}</strong> | Date: {{ upload_date }}</p>

{% if validation.is_valid %}
<p class="validation-ok">Validation passed.</p>
{% endif %}
{% if validation.warnings %}
<h2>Warnings</h2>
<ul>{% for w in validation.warnings %}<li class="validation-warn">{{ w }}</li>{% endfor %}</ul>
{% endif %}

<h2>Portfolio Summary</h2>
<div class="cards">
  <div class="card"><div class="value">{{ summary.row_count }}</div><div class="label">Positions</div></div>
  <div class="card"><div class="value">{{ summary.unique_templates }}</div><div class="label">Templates</div></div>
  <div class="card"><div class="value">{{ summary.total_weight }}</div><div class="label">Total Weight</div></div>
  <div class="card"><div class="value">{{ coverage.issuer_coverage_pct }}%</div><div class="label">Issuer Coverage</div></div>
  <div class="card"><div class="value">{{ coverage.maturity_coverage_pct }}%</div><div class="label">Maturity Coverage</div></div>
</div>

{% for alloc_name, alloc_data in allocations.items %}
<h2>{{ alloc_name|title }}</h2>
<table>
  <thead><tr><th>Name</th><th>Code</th><th class="pct">Weight</th><th class="pct">%</th></tr></thead>
  <tbody>
  {% for row in alloc_data %}
  <tr><td>{{ row.name }}</td><td><code>{{ row.code }}</code></td><td class="pct">{{ row.weight }}</td><td class="pct">{{ row.pct }}%</td></tr>
  {% endfor %}
  </tbody>
</table>
{% endfor %}

<h2>Charts</h2>
{% for chart_file in chart_files %}
<div class="chart-container">{{ chart_file|safe }}</div>
{% endfor %}

<h2>Unrolled Positions</h2>
<table>
  <thead>
    <tr><th>#</th><th>Name</th><th>Code</th><th>Kind</th><th>Weight</th><th>Issuer</th><th>Exposure</th><th>Tax</th><th>Maturity</th></tr>
  </thead>
  <tbody>
  {% for pos in positions %}
  <tr>
    <td>{{ pos.row_number }}</td>
    <td>{{ pos.display_name }}</td>
    <td><code>{{ pos.template_code }}</code></td>
    <td>{{ pos.instrument_kind }}</td>
    <td class="pct">{{ pos.weight }}</td>
    <td>{{ pos.issuer_name|default:"—" }}{% if pos.issuer_code %} <small>({{ pos.issuer_code }})</small>{% endif %}</td>
    <td>{{ pos.exposure_display }}</td>
    <td>{{ pos.tax_profile_name|default:"—" }}</td>
    <td>{{ pos.maturity_bucket|default:"—" }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>

{% for pos in positions %}
<details>
  <summary>Row {{ pos.row_number }}: {{ pos.display_name }} ({{ pos.template_code }}) — Instructions</summary>
  {% for angle, sources in pos.instructions.items %}
  {% if sources %}
  <h4>{{ angle|title }}</h4>
  <pre>{% for s in sources %}[{{ s.source|upper }}] {{ s.code }}
{{ s.text }}
{% endfor %}</pre>
  {% endif %}
  {% endfor %}
</details>
{% endfor %}

</body>
</html>"""


def generate_html_preview(run_id, upload_date, validation, positions, allocations, coverage, charts_dir):
    """Generate the HTML preview file content."""
    # Read SVG chart files for inline embedding
    chart_files = []
    if os.path.isdir(charts_dir):
        for fname in sorted(os.listdir(charts_dir)):
            if fname.endswith('.svg'):
                with open(os.path.join(charts_dir, fname), 'r') as f:
                    chart_files.append(f.read())

    # Prepare allocation data with percentages
    alloc_display = {}
    for name, data in allocations.items():
        display_name = name.replace('by_', '').replace('_', ' ')
        alloc_display[display_name] = [
            {'code': d['code'], 'name': d.get('name', d['code']),
             'weight': f"{d['weight']:.4f}", 'pct': f"{d['weight'] * 100:.1f}"}
            for d in data
        ]

    # Prepare positions for display
    pos_display = []
    for p in positions:
        exp_display = ', '.join(
            f"{e.get('name', e['code'])}({e['weight']:.0%})" if e['weight'] < 1
            else e.get('name', e['code'])
            for e in p.economic_exposures
        )
        pos_display.append({
            'row_number': p.row_number,
            'template_code': p.template_code,
            'display_name': p.display_name,
            'instrument_kind': p.instrument_kind,
            'weight': f"{float(p.weight):.4f}",
            'issuer_code': p.issuer_code,
            'issuer_name': p.issuer_name,
            'exposure_display': exp_display,
            'tax_profile_name': p.tax_profile_name,
            'maturity_bucket': p.maturity_bucket,
            'instructions': p.instructions,
        })

    unique_templates = len(set(p.template_code for p in positions))
    summary = {
        'row_count': len(positions),
        'unique_templates': unique_templates,
        'total_weight': f"{sum(float(p.weight) for p in positions):.4f}",
    }
    coverage_display = {
        'issuer_coverage_pct': f"{coverage.get('issuer_coverage', 0) * 100:.0f}",
        'maturity_coverage_pct': f"{coverage.get('maturity_coverage', 0) * 100:.0f}",
    }

    template = Template(HTML_TEMPLATE)
    ctx = Context({
        'run_id': run_id,
        'upload_date': upload_date,
        'validation': validation,
        'summary': summary,
        'coverage': coverage_display,
        'allocations': alloc_display,
        'chart_files': chart_files,
        'positions': pos_display,
    })
    return template.render(ctx)
