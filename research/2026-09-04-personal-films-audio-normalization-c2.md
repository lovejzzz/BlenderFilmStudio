# Audio C2 parser correction

C1 Little Gravity stopped after the first-pass measurement and before creating any corrected media: FFmpeg appended a progress summary after its valid JSON object, so json.loads rejected trailing text. Keep the C1 root unchanged. C2 uses JSONDecoder.raw_decode to consume the measured object and ignore trailing FFmpeg diagnostics. Same target, source WAV, packet-copy operation, limits and checks; fresh PF-AUDIO-C2-2026-09-04-attempt-01 roots only. No Blender or source/retained-root writes. C1 consumed one measurement, zero media encodes.
