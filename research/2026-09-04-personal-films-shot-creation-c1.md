# Coverage undo active-camera correction

Source review found that deleting an added coverage camera during Undo can clear scene.camera. Restore an existing product camera when that happens and require the actual verification to assert a non-null active camera. Candidate0024 repeats the same zero-render coverage workflow on a fresh copied0022 blend. Original0023 remains retained with its narrower checks. This changes neither film inputs nor rendered frames.
