# B62-Q1-D4-C3 timeline-marker camera routing

v0.3 completed all 12 Cycles renders, but every original/corrected Combined pair was pixel-identical because Blender's frame-193 timeline marker reselected the original camera during render evaluation. C3 permits the render tool to route both the marker and `scene.camera` to the labelled condition, then restore the marker. It does not alter the independent geometry result: corrected frame 288 exceeded the frozen area maximum, so a correctly routed retry may validly return scientific REJECTED.
