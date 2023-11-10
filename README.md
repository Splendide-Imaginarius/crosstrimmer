# CrossTrimmer

CrossTrimmer is a tool for automatically trimming/padding an audio file to match the timings of another audio file. If you have a low-quality trimmed audio file, and a high-quality untrimmed master, CrossTrimmer may be able to produce a FLAC file with the same timings as the low-quality file, but with the same quality as the master.

## Installation

First, you'll need to install [CrossLooper](https://github.com/Splendide-Imaginarius/crosslooper) according to its installation instructions.

Once you've done that, to install CrossTrimmer via pip, do this from the `crosstrimmer` repo directory:

```
pip install --user .
```

## Usage

To trim/pad `content.ogg` to match the timing of `timing.ogg` and save the result in `result.flac`:

```
crosstrimmer content.ogg timing.ogg result.flac
```

To trim/pad all pairs of files in two directories:

```
crosstrimmerdir ./content/ ./timing/ ./result/
```

To evaluate the quality difference between `result.flac` and `timing.ogg`, you can do this:

```
./wavinterleave.sh result.flac timing.ogg 5 interleaved.flac
```

The resulting `interleaved.flac` will alternate between 5 seconds of `result.flac` and 5 seconds of `timing.ogg`.

## Related Projects

* [CrossLooper](https://github.com/Splendide-Imaginarius/crosslooper)
* [WavGrep](https://github.com/Splendide-Imaginarius/wavgrep)

## Credits

Copyright 2023 Splendide Imaginarius.

This is not a license requirement, but if you use CrossTrimmer for a project, it would be greatly appreciated if you credit me. Example credits: "Audio was trimmed with CrossTrimmer by Splendide Imaginarius." Linking back to this Git repository would also be greatly appreciated.

CrossTrimmer is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

CrossTrimmer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with CrossTrimmer. If not, see [https://www.gnu.org/licenses/](https://www.gnu.org/licenses/).
