"""Build article-native diagrams and plots from the published aggregate data."""

import html
import json
from pathlib import Path


def esc(value):
    return html.escape(str(value), quote=True)


def svg_start(label, width=400, height=250):
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}"><title>{esc(label)}</title>'


def text(x, y, label, cls="axis-label", anchor="start"):
    return f'<text x="{x:g}" y="{y:g}" class="{cls}" text-anchor="{anchor}">{esc(label)}</text>'


def line(x1, y1, x2, y2, cls="chart-grid"):
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" class="{cls}" />'


def poly(points):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def interactive_mark(label, body, difficulty=""):
    return f'<g class="chart-mark {difficulty}" tabindex="0" role="img" aria-label="{esc(label)}" data-readout="{esc(label)}"><title>{esc(label)}</title>{body}</g>'


def rhythm_plot(data, metric, title, unit, maximum, ticks):
    """Dots are medians; whiskers are the exact published 25th/75th percentiles."""
    parts = [f'<section class="chart-panel"><h4>{title}</h4>', svg_start(title)]
    left, right, top, bottom = 44, 380, 24, 196
    y = lambda value: bottom - value / maximum * (bottom - top)
    for tick in ticks:
        parts += [line(left, y(tick), right, y(tick)), text(left - 10, y(tick) + 4, tick, anchor="end")]
    for index, size in enumerate(data['board_sizes']):
        x = 84 + index * 88
        parts.append(text(x, 219, f"{size}×{size}", anchor="middle"))
        for difficulty, offset in [('medium', -10), ('hard', 10)]:
            group = next(g for g in data['groups'] if g['size'] == size and g['difficulty'] == difficulty)
            if metric == 'longest_placement_run_median':
                median = group[metric]
                label = f"{size}×{size}, {difficulty}: median {median:g} {unit}; n={group['cases']}"
                mark = f'<circle cx="{x+offset}" cy="{y(median):.2f}" r="5" />'
            else:
                distribution = next(g for g in data['distributions'] if g['size'] == size and g['difficulty'] == difficulty and g['metric'] == metric)
                median, low, high = (distribution[k] for k in ['median', 'q25', 'q75'])
                label = f"{size}×{size}, {difficulty}: median {median:g}, middle 50% {low:g}–{high:g} {unit}; n={distribution['n']}"
                mark = line(x+offset,y(low),x+offset,y(high),'chart-whisker')
                mark += line(x+offset-4,y(low),x+offset+4,y(low),'chart-whisker')
                mark += line(x+offset-4,y(high),x+offset+4,y(high),'chart-whisker')
                mark += f'<circle cx="{x+offset}" cy="{y(median):.2f}" r="5" />'
            parts.append(interactive_mark(label, mark, difficulty))
    parts += [text(44, 242, unit), '</svg></section>']
    return ''.join(parts)


def discovery_plot(data):
    title = 'How placements accumulate'
    parts = ['<section class="chart-panel"><h4>'+title+'</h4>', svg_start(title)]
    left, right, top, bottom = 44, 380, 24, 196
    x = lambda v: left + v * (right-left)
    y = lambda v: bottom - v * (bottom-top)
    for tick in [0, .25, .5, .75, 1]:
        parts += [line(left,y(tick),right,y(tick)),text(left-10,y(tick)+4,f'{tick:.0%}',anchor='end')]
        parts.append(text(x(tick),219,f'{tick:.0%}',anchor='middle'))
    for curve in data['discovery_curves']:
        xs = curve['trace_progress_fraction']
        q25, median, q75 = (curve[k] for k in ['determined_fraction_q25','determined_fraction_median','determined_fraction_q75'])
        assert len(xs) == len(q25) == len(median) == len(q75)
        assert all(0 <= a <= b <= c <= 1 for a,b,c in zip(q25,median,q75))
        band = [(x(a),y(b)) for a,b in zip(xs,q25)] + list(reversed([(x(a),y(b)) for a,b in zip(xs,q75)]))
        parts.append(f'<g class="{esc(curve["difficulty"])}"><polygon class="chart-band" points="{poly(band)}" /><polyline class="chart-curve" points="{poly([(x(a),y(b)) for a,b in zip(xs,median)])}" /></g>')
        # Keyboard/hover samples expose exact values at quarter-trace intervals.
        for i in [0,25,50,75,100]:
            label=f'{curve["difficulty"].capitalize()}, {xs[i]:.0%} through trace: {median[i]:.1%} placed; middle 50% {q25[i]:.1%}–{q75[i]:.1%}; n={curve["n"]}'
            parts.append(interactive_mark(label,f'<circle cx="{x(xs[i]):.2f}" cy="{y(median[i]):.2f}" r="4" />',curve['difficulty']))
    parts += [text(44,242,'Fraction of deduction trace completed'), '</svg></section>']
    return ''.join(parts)


def render_rhythm(assets):
    data = json.loads((assets/'puzzle-rhythm.json').read_text())
    assert len(data['groups']) == 8 and sum(g['cases'] for g in data['groups']) == data['cases'] == 96
    for d in data['distributions']:
        assert d['n'] == 12 and d['q25'] <= d['median'] <= d['q75']
        field = {'first_determination_step':'opening_steps_median','determination_gap_max':'longest_discovery_gap_median'}[d['metric']]
        group = next(g for g in data['groups'] if g['size']==d['size'] and g['difficulty']==d['difficulty'])
        assert d['median'] == group[field]
    return '''<div class="native-figure-content" data-native="puzzle-rhythm">
<div class="figure-topline"><div><p class="figure-kicker">96 generated cases · canonical solver</p><p class="figure-title">A puzzle has more than one kind of rhythm.</p></div>
<div class="chart-legend"><span class="medium">● Medium</span><span class="hard">● Hard</span></div></div>
<div class="native-chart-grid">''' + rhythm_plot(data,'first_determination_step','First exact placement','Deduction steps',12,[0,3,6,9,12]) + rhythm_plot(data,'determination_gap_max','Longest gap between placements','Deduction steps',12,[0,3,6,9,12]) + rhythm_plot(data,'longest_placement_run_median','Longest consecutive placement chain','Consecutive placements',6,[0,2,4,6]) + discovery_plot(data) + '''</div>
<p class="chart-readout" aria-live="polite">Hover over or focus a dot to inspect the published values.</p></div>'''


def render_pipeline():
    steps=[('Verified structure','Generate a board and clues; establish a unique solution.'),('Semantic setting','Add a world, names and clue wording to the checked puzzle.'),('Paired queries','Export the same case as text or a visual observation.'),('Agent + tools','Act in a stateful environment and submit an answer.'),('Gold reward','Check the answer against the verified solution.')]
    return '<div class="native-figure-content" data-native="pipeline"><p class="figure-kicker">From construction to verification</p><p class="figure-title">One checked puzzle, many ways to play.</p><ol class="pipeline">'+''.join(f'<li><span class="pipeline-step">{i:02}</span><strong>{title}</strong><p>{description}</p></li>' for i,(title,description) in enumerate(steps,1))+'</ol></div>'


def render_breakthrough():
    return '''<div class="native-figure-content" data-native="breakthrough"><p class="figure-kicker">A deduction before the first placement</p><p class="figure-title">Narrowing a room can unlock the next clue.</p>
<ol class="deduction-steps">
<li><span class="pipeline-step">01</span><div><strong>Hyacinth · Cliff</strong><p>Her remaining columns are <span class="cell-chip">C6</span> and <span class="cell-chip">C7</span>.</p></div></li>
<li><span class="pipeline-step">02</span><div><strong>Mortimer · Galleon</strong><p>A hat wearer cannot share Hyacinth’s column or an adjacent column. <span class="cell-chip excluded"><s>C6</s> excluded</span> <span class="cell-chip excluded"><s>C7</s> excluded</span></p></div></li>
<li><span class="pipeline-step">03</span><div><strong>Mortimer · Frigate A</strong><p>His remaining candidates are <span class="cell-chip">C15</span> and <span class="cell-chip">C17</span>, both in row 10. That row is reserved.</p></div></li>
</ol></div>'''


def step_points(events, key, x, y):
    points=[(x(events[0]['step']),y(events[0][key]))]
    for old,new in zip(events,events[1:]):
        points += [(x(new['step']),y(old[key])),(x(new['step']),y(new[key]))]
    return points


def render_contest(assets):
    data=json.loads((assets/'contest-rhythm.json').read_text())
    events=data['events']
    x=lambda v: 44+v/85*336
    panels=[]
    for key,title,ticks,maximum in [('people_located','People located out of 23',[0,5,10,15,20,23],23),('candidate_cells','Candidate cells across 23 people',[0,500,1000,1500,2000],2000)]:
        y=lambda v: 204-v/maximum*170
        parts=[f'<section class="chart-panel"><h4>{title}</h4>',svg_start(title)]
        for tick in ticks:parts += [line(44,y(tick),380,y(tick)),text(34,y(tick)+4,f'{tick:,}',anchor='end')]
        for tick in [0,13,40,71,85]:parts.append(text(x(tick),227,tick,anchor='middle'))
        parts.append(f'<polyline class="chart-curve" points="{poly(step_points(events,key,x,y))}" />')
        # Coordinates and names from the private solution are deliberately not exported.
        for event in events:
            if event['step'] % 5 and event['step'] not in [13, 71, 84]:
                continue
            label=f'Event {event["step"]}: {event["people_located"]} {"person" if event["people_located"] == 1 else "people"} located, {event["candidate_cells"]:,} candidate cells'
            parts.append(interactive_mark(label,f'<circle cx="{x(event["step"]):.2f}" cy="{y(event[key]):.2f}" r="3" />','medium'))
        parts += [text(44,247,'Deduction event · linear axes'),'</svg></section>']
        panels.append(''.join(parts))
    return '<div class="native-figure-content" data-native="contest-rhythm"><p class="figure-kicker">The Treasure Hunt · recorded solver trace</p><p class="figure-title">Partial progress, then a chain of placements.</p><div class="native-chart-grid">'+''.join(panels)+'</div><p class="chart-readout" aria-live="polite">Hover over or focus a point to inspect an event. Events describe the solver trace, not elapsed time.</p></div>'


def native_content(image_path, assets):
    functions={'semantic-pipeline.png':render_pipeline,'puzzle-rhythm.png':lambda:render_rhythm(assets),'opening-breakthrough.png':render_breakthrough,'contest-rhythm.png':lambda:render_contest(assets)}
    renderer=functions.get(Path(image_path).name)
    return renderer() if renderer else None
