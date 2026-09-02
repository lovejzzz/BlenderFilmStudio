#!/usr/bin/env python3
"""C1 scene adapter: observe and safely reuse the copied scene's FLIP roster."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("inspect-rc6-liquid-flip-particle-axis-scene.py")
EXPECTED_BASE_SHA256 = "7723b976d2e78e53f1d83091f80fbc65e24ee279aeb1aa9f1c5bfb50f73a23c9"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 FLIP-particle axis C1 scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '''    if settings.use_flip_particles or len(domain.particle_systems) != 0:
        raise RuntimeError("FLIP particle system was not initially absent")

    settings.use_flip_particles = True
    bpy.context.view_layer.update()
    if not settings.use_flip_particles or len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system creation failed")''',
        '''    initial_use_flip_particles = bool(settings.use_flip_particles)
    initial_particle_system_count = len(domain.particle_systems)
    if initial_particle_system_count not in (0, 1) or (initial_use_flip_particles and initial_particle_system_count != 1):
        raise RuntimeError("FLIP particle initial roster is not safely interpretable")
    exposure_action = "REUSED_EXISTING_ENABLED_SYSTEM"
    if not initial_use_flip_particles:
        settings.use_flip_particles = True
        exposure_action = "ENABLED_IN_MEMORY_WITH_EXISTING_SYSTEM" if initial_particle_system_count == 1 else "ENABLED_IN_MEMORY_AND_CREATED_SYSTEM"
    bpy.context.view_layer.update()
    if not settings.use_flip_particles or len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system exposure failed")''',
        1,
        "initial roster handling",
    ),
    (
        '''            "flipParticleSystemInitiallyAbsent": True,
            "flipParticleSystemExposedInMemory": True,
            "displayPercentage": 100,''',
        '''            "initialUseFlipParticles": initial_use_flip_particles,
            "initialParticleSystemCount": initial_particle_system_count,
            "exposureAction": exposure_action,
            "finalUseFlipParticles": bool(settings.use_flip_particles),
            "finalParticleSystemCount": len(domain.particle_systems),
            "displayPercentage": 100,''',
        1,
        "observed configuration",
    ),
    ("bfs.rc6LiquidFlipParticleAxisDiagnostic.v0.1", "bfs.rc6LiquidFlipParticleAxisDiagnostic.v0.2", 1, "schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 FLIP-particle axis C1 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FLIP_PARTICLE_AXIS_SCENE_C1_V02", "exec"), globals(), globals())
