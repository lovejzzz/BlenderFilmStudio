"""Measured two-pass normalization shared by export and audio-only recovery."""
import json, math, subprocess
from pathlib import Path

def measured_filter(ffmpeg, wav, output):
    output = Path(output)
    argv = [ffmpeg, '-nostdin', '-hide_banner', '-i', str(wav), '-af',
            'loudnorm=I=-20:TP=-2:LRA=7:print_format=json', '-f', 'null', '-']
    result = subprocess.run(argv, capture_output=True, text=True, check=True, timeout=120)
    (output / 'audio-measurement.log').write_text(result.stderr)
    values, _ = json.JSONDecoder().raw_decode(result.stderr[result.stderr.rfind('{'):])
    fields = {'measured_I': 'input_i', 'measured_TP': 'input_tp',
              'measured_LRA': 'input_lra', 'measured_thresh': 'input_thresh',
              'offset': 'target_offset'}
    if not all(math.isfinite(float(values[key])) for key in fields.values()):
        raise ValueError('Soundtrack cannot be normalized: non-finite measurement')
    gain_db = min(-20 - float(values['input_i']), -2 - float(values['input_tp']))
    filt = f'volume={gain_db:.6f}dB'
    (output / 'audio-normalization.json').write_text(json.dumps(
        {'argv': argv, 'measurement': values, 'filter': filt,
         'method': 'measured constant gain, preserving original dynamics'}, indent=2))
    return filt
