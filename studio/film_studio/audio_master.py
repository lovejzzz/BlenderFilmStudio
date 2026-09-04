"""Measured two-pass normalization shared by export and audio-only recovery."""
import json, math, re, subprocess
from pathlib import Path

def measured_filter(ffmpeg, wav, output):
    output = Path(output)
    argv = [ffmpeg, '-nostdin', '-hide_banner', '-i', str(wav), '-af',
            'ebur128=peak=true', '-f', 'null', '-']
    result = subprocess.run(argv, capture_output=True, text=True, check=True, timeout=120)
    (output / 'audio-measurement.log').write_text(result.stderr)
    summary = result.stderr.rsplit('Summary:', 1)[-1]
    integrated = re.search(r'I:\s+(-?[\d.]+) LUFS', summary)
    peak = re.search(r'Peak:\s+(-?[\d.]+) dBFS', summary)
    if not integrated or not peak:
        raise ValueError('Soundtrack measurement summary is incomplete')
    values = {'input_i': float(integrated.group(1)), 'input_tp': float(peak.group(1))}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError('Soundtrack cannot be normalized: non-finite measurement')
    gain_db = min(-20 - float(values['input_i']), -2 - float(values['input_tp']))
    filt = f'volume={gain_db:.6f}dB'
    (output / 'audio-normalization.json').write_text(json.dumps(
        {'argv': argv, 'measurement': values, 'filter': filt,
         'method': 'measured constant gain, preserving original dynamics'}, indent=2))
    return filt
