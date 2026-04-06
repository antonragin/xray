import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os


def render_horizontal_bar(data, title, output_path):
    """Render a horizontal bar chart to SVG.
    data: list of {code, weight} dicts, already sorted by weight descending.
    """
    if not data:
        return

    labels = [d['code'] for d in data]
    values = [d['weight'] * 100 for d in data]  # percentages

    fig, ax = plt.subplots(figsize=(10, max(2.5, len(labels) * 0.45)))
    bars = ax.barh(range(len(labels)), values, color='#4A90D9', edgecolor='#2C5F8A')
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel('Allocation (%)', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.invert_yaxis()

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', fontsize=8)

    ax.set_xlim(0, max(values) * 1.15 if values else 100)
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close(fig)


def generate_all_charts(allocations, charts_dir):
    """Generate all 5 required SVG charts."""
    charts = [
        ('by_economic_exposure', 'Allocation by Economic Exposure', 'economic_exposure_bar.svg'),
        ('by_issuer_type', 'Allocation by Issuer Type', 'issuer_type_bar.svg'),
        ('by_instrument_kind', 'Allocation by Instrument Kind', 'instrument_kind_bar.svg'),
        ('by_maturity_bucket', 'Allocation by Maturity Bucket', 'maturity_bucket_bar.svg'),
    ]
    for alloc_key, title, filename in charts:
        data = allocations.get(alloc_key, [])
        render_horizontal_bar(data, title, os.path.join(charts_dir, filename))

    # Top 10 issuers
    issuer_data = allocations.get('by_issuer', [])[:10]
    render_horizontal_bar(
        issuer_data, 'Top Issuers by Weight',
        os.path.join(charts_dir, 'issuer_bar_top10.svg'),
    )
