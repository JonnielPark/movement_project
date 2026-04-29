# Data Format

## Purpose

This document describes the expected pose CSV format used by the current framework.

The format is intentionally simple so that pose data from different sources can be converted into a common representation.

## Required Columns

Each CSV file should contain frame and timestamp columns.

```text
frame
timestamp
```

`frame` should identify the frame index.

`timestamp` should represent the time of each frame. The current validation module uses timestamp differences to estimate sampling interval and FPS.

## Landmark Coordinate Columns

Each landmark should have x, y, and z coordinate columns.

```text
<landmark>_x
<landmark>_y
<landmark>_z
```

Example:

```text
left_knee_x
left_knee_y
left_knee_z
```

The landmark names are defined in:

```text
src/movement/config.py
```

## Optional Visibility Columns

Visibility columns are optional but recommended.

```text
<landmark>_visibility
```

Example:

```text
left_knee_visibility
```

Visibility values can be used later to detect unreliable landmarks, exclude unstable frames, or select robust frames for scale estimation.

## Example CSV Structure

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_visibility,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

## Current Assumptions

The current modules assume:

```text
1. one row represents one frame
2. each landmark has x, y, z coordinates
3. frame values are ordered or can be sorted
4. timestamp values are monotonic
5. landmark names match the project configuration
```

## Data Privacy

Do not commit private or identifiable data.

Do not commit:

- raw videos
- clinical data
- personal recordings
- private API keys
- IRB-restricted datasets
- internal SDK files

Recommended private folders:

```text
data/raw/
data/private/
data/clinical/
data/videos/
```
