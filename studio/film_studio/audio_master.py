"""Measured two-pass normalization shared by export and audio-only recovery."""
import json, math, subprocess
from pathlib import Path

def measured_filter(ffmpeg, wav, output):
    output = Path(output)
    argv = [ffmpeg, '-nostdin', '-hide_banner', '-i', str(wav), '-af',
            'loudnorm=I=-20:TP=-2:LRA=7:print_format=json', '-f', 'null', '-']
    result = subprocess.run(argv, capture_output=True, text=True, check=True, timeout=120)
    (output / 'audio-measurement.log').write_text(result.stderr)
    values = json.loads(result.stderr[result.stderr.rfind('{'):])
    fields = {'measured_I': 'input_i', 'measured_TP': 'input_tp',
              'measured_LRA': 'input_lra', 'measured_thresh': 'input_thresh',
              'offset': 'target_offset'}
    if not all(math.isfinite(float(values[key])) for key in fields.values()):
        raise ValueError('Soundtrack cannot be normalized: non-finite measurement')
    filt = 'loudnorm=I=-20:TP=-2:LRA=7:linear=true:' + ':'.join(
        f'{key}={values[value]}' for key, value in fields.items())
    (output / 'audio-normalization.json').write_text(json.dumps(
        {'argv': argv, 'measurement': values, 'filter': filt}, indent=2))
    return filt
