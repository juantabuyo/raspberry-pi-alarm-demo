"""Render the actual local controller trace as an SVG; no hardware is involved."""
import argparse
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulate import run_demo


def render(output):
    result = run_demo()
    rows = result['states']
    svg = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg',
                            'viewBox': f'0 0 1000 {210 + len(rows) * 60}',
                            'role': 'img', 'aria-labelledby': 'title desc'})
    ET.SubElement(svg, 'title', {'id': 'title'}).text = 'Alarm controller: recorded simulation trace'
    ET.SubElement(svg, 'desc', {'id': 'desc'}).text = (
        'Seven recorded state entries from the real controller running with GPIO doubles '
        'and a manually advanced clock. Telegram is disabled. No physical hardware test.')
    ET.SubElement(svg, 'rect', {'width': '100%', 'height': '100%', 'fill': '#f5f7fb'})

    def text(x, y, value, size=19, colour='#17243d', weight='400'):
        ET.SubElement(svg, 'text', {'x': str(x), 'y': str(y),
            'font-family': 'system-ui, sans-serif', 'font-size': str(size),
            'fill': colour, 'font-weight': weight}).text = value

    text(42, 54, 'Alarm controller', 30, weight='650')
    text(42, 87, 'Recorded local simulation · actual controller, GPIO doubles, manual clock', 17)
    text(42, 132, 'EVENT', 13, '#53647a', '650')
    text(130, 132, 'SIMULATED TIME', 13, '#53647a', '650')
    text(345, 132, 'STATE', 13, '#53647a', '650')
    text(720, 132, 'DISPLAY CALL', 13, '#53647a', '650')
    colours = {'DISARMED': '#16856c', 'EXIT_DELAY': '#3e62bf', 'ARMED': '#53647a',
               'PREALARM': '#bb780b', 'ALARM': '#c74754'}
    for i, row in enumerate(rows):
        y = 150 + i * 60
        ET.SubElement(svg, 'rect', {'x': '30', 'y': str(y), 'width': '940',
            'height': '50', 'rx': '9', 'fill': '#ffffff'})
        text(53, y + 32, f'{i + 1:02}', 17, '#53647a')
        text(130, y + 32, f"{row['time_seconds']:g} s", 20)
        ET.SubElement(svg, 'circle', {'cx': '321', 'cy': str(y + 25), 'r': '6',
                                     'fill': colours[row['state']]})
        text(345, y + 32, row['state'], 20, colours[row['state']], '650')
        kind, value = row['display']
        display = 'blank' if kind == 'text' and str(value).isspace() else str(value)
        text(720, y + 32, display, 20)
    y = 188 + len(rows) * 60
    text(42, y, '85 seconds are simulated time. No physical or network validation.', 16, '#53647a')
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(svg)
    ET.ElementTree(svg).write(output, encoding='utf-8', xml_declaration=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'docs' / 'assets' / 'simulated-state-trace.svg')
    render(parser.parse_args().output)
