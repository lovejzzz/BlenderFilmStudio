# Final encoded-audio checks

Before either final soundtrack/movie exists, strengthen the independent delivery reviewer so a failed full decode cannot appear as PASS merely because ffprobe found a stream. Require FFmpeg's complete audio/video decode to return zero, parse its EBU R128 integrated loudness and true peak, and retain the log.

For the existing frozen encoder target of-20LUFS and-2dBTP, preregister an encoded integrated range of-22 through-18LUFS and a true peak at or below-1dBFS. These are technical delivery checks, not a claim about artistic sound quality or subjective hearing. Do not gate on a fixed loudness range: the original sparse impact score intentionally has strong dynamics. The retained6-second preview decodes and measures-19.6LUFS/-8.0dBFS; it is a format check, not either final film's result.

Only the independent read-only reviewer changes. No final source, audio synthesis, encoder target, frame or running process changes. This stays inside the delivery-review admission's2GiB and zero-Blender limits.
