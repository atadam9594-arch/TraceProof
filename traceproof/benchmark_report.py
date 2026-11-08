"""Self-contained, script-free and path-free HTML for a video benchmark result."""
from __future__ import annotations

from html import escape
from pathlib import Path

from .benchmark import RESULT_SCHEMA


def render_benchmark_report(result):
    if not isinstance(result, dict) or result.get('schema') != RESULT_SCHEMA:
        raise ValueError('Unsupported benchmark result schema')
    summary = result.get('summary')
    pairs = result.get('pairs')
    groups = result.get('groups')
    if not isinstance(summary, dict) or not isinstance(pairs, list) or not isinstance(groups, dict):
        raise ValueError('Malformed benchmark result')

    def val(obj, percent=False):
        if obj is None:
            return 'Undefined'
        if type(obj) is float and percent:
            return str(round(obj * 100, 2)) + '%'
        return escape(str(obj), quote=True)

    def intervals(stat, key):
        rng = stat.get('confidence_intervals_95',{}).get(key)
        if isinstance(rng,list) and len(rng)==2:
            return f'{val(rng[0],True)}–{val(rng[1],True)}'
        return 'Undefined'

    labels = [('pairs','Pairs'),('evaluated','Evaluated'),('errors','Errors'),
              ('true_positive','True positive'),('false_positive','False positive'),
              ('true_negative','True negative'),('false_negative','False negative'),
              ('precision','Precision'),('recall','Recall'),('false_positive_rate','False positive rate'),
              ('specificity','Specificity'),('accuracy','Accuracy'),('coverage','Coverage')]
    rows = []
    for key,label in labels:
        ci = intervals(summary,key) if key in {'precision','recall','false_positive_rate','specificity','accuracy','coverage'} else '—'
        rows.append(f'<tr><th scope="row">{label}</th><td>{val(summary.get(key),key in {'precision','recall','false_positive_rate','specificity','accuracy','coverage'})}</td><td>{ci}</td></tr>')
    groups_rows = []
    for name, stats in sorted(groups.items()):
        if not isinstance(stats,dict):
            raise ValueError('Invalid benchmark group')
        groups_rows.append('<tr><th scope="row">'+escape(name,quote=True)+'</th>'+
                           ''.join(f'<td>{val(stats.get(key),key in {"recall","false_positive_rate","coverage"})}</td>' for key in ('evaluated','false_positive','false_negative','recall','false_positive_rate','coverage'))+'</tr>')
    pair_rows = []
    for record in pairs:
        if not isinstance(record,dict):
            raise ValueError('Invalid pair record')
        pair_rows.append('<tr>'+''.join(f'<td>{val(record.get(key))}</td>'
                          for key in ('id','group','expected_overlap','status','relation','predicted_overlap','elapsed_ms'))+'</tr>')
    digest = escape(str(result.get('manifest_sha256','')),quote=True)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>TraceProof — dataset evaluation</title><style>
:root {{color-scheme:light}} body{{font:15px/1.55 system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 20px;color:#172033}}
h1,h2{{line-height:1.2}}p.warning{{background:#f3f5f8;border-left:4px solid #596d83;padding:15px}}
table{{width:100%;border-collapse:collapse;margin:16px 0 30px;font-size:14px}}th,td{{padding:10px;border-bottom:1px solid #d4dbe6;text-align:left;overflow-wrap:anywhere}}th{{font-weight:650}}tbody tr:nth-child(even){{background:#f7f9fc}}.scroll{{overflow-x:auto}}
code{{overflow-wrap:anywhere}}footer{{border-top:1px solid #ccd4df;padding-top:18px;font-size:13px;color:#516179}}
@media print{{body{{margin:0;font-size:12px}}}}</style></head>
<body><header><strong>TRACEPROOF · EXPERIMENTAL BENCHMARK</strong><h1>Video overlap — dataset evaluation</h1>
<p class="warning"><strong>Not a forensic verdict.</strong> This report describes only manually labeled pairs from one dataset. Results must not be presented as universal detection accuracy or as proof of AI authorship, authenticity or source identity.</p>
<p>Manifest SHA-256: <code>{digest}</code><br>Sampled frames per video: {val(result.get('samples'))}</p></header>
<main><section><h2>Overall confusion matrix and rates</h2><div class="scroll"><table><thead><tr><th>Metric</th><th>Value</th><th>95% Wilson interval</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>Per-group breakdown</h2><div class="scroll"><table><thead><tr><th>Group</th><th>Evaluated</th><th>False +</th><th>False −</th><th>Recall</th><th>False + rate</th><th>Coverage</th></tr></thead><tbody>{''.join(groups_rows)}</tbody></table></div></section>
<section><h2>Individual labeled pairs</h2><div class="scroll"><table><thead><tr><th>ID</th><th>Group</th><th>Expected overlap</th><th>Status</th><th>Relation</th><th>Predicted overlap</th><th>Elapsed ms</th></tr></thead><tbody>{''.join(pair_rows)}</tbody></table></div></section></main>
<footer>Created by TraceProof. Confidence intervals assume independent binomial observations; they do not account for dataset bias, shared sources, distribution shift or errors. Raw video paths and data are intentionally absent.</footer></body></html>'''


def write_benchmark_report(result, output):
    path = Path(output)
    path.write_text(render_benchmark_report(result),encoding='utf-8')
    return path