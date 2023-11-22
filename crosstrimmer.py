#!/usr/bin/env python3

from pathlib import Path
import shutil
import subprocess
import tempfile

import crosslooper


__version__ = "1.0.1"
__author__ = """Splendide Imaginarius"""


def cli_parser(**ka):
    parser = crosslooper.cli_parser(take=None, **ka)

    parser.description = crosstrimmer.__doc__

    if 'content' not in ka:
        parser.add_argument(
            'content',
            action='store',
            type=str,
            help='Audio file containing content to trim.')
    if 'timing' not in ka:
        parser.add_argument(
            'timing',
            action='store',
            type=str,
            help='Audio file containing timing to apply to the content.')
    if 'out' not in ka:
        parser.add_argument(
            'out',
            action='store',
            type=str,
            help='Output FLAC file containing the trimmed content.')
    if 'take' not in ka:
        parser.add_argument(
            '-t', '--take',
            dest='take',
            action='store',
            type=float,
            default=10.0,
            help='Take X seconds of the inputs to look at when trimming intro. ' +
                 '(default: 10)')
    if 'quiet' not in ka:
        parser.add_argument(
            '-q', '--quiet',
            dest='quiet',
            action='store_true',
            help='Suppress informational output.')

    return parser


def crosstrimmer(use_argparse=True, **ka):
    """CLI interface to make one audio file match the timing of another audio
    file containing similar content.
    ffmpeg needs to be available.
    """

    ka['in1'] = None
    ka['in2'] = None
    ka['show'] = False
    ka['loop-start-min'] = 0.0
    ka['loop-search-len'] = None
    ka['loop'] = False
    ka['loop-start-max'] = None
    ka['loop-end-min'] = None
    ka['loop-len-min'] = None
    ka['loop-search-step'] = None
    ka['loop-force'] = False
    ka['loop-enable-seconds-tags'] = False
    ka['samples'] = False
    ka['skip'] = False

    if use_argparse:
        parser = cli_parser(**ka)
        args = parser.parse_args().__dict__
        ka.update(args)

    ka['in1'] = ka['content']
    ka['in2'] = ka['timing']

    # We use 'take' instead of 'loop-search-len' to improve speed.
    ka['loop-search-len'] = -1

    verbose = ka['verbose']
    quiet = ka['quiet']

    content_path = Path(ka['content'])
    timing_path = Path(ka['timing'])
    if not content_path.exists():
        raise Exception(f'{content_path} does not exist')
    if not timing_path.exists():
        raise Exception(f'{timing_path} does not exist')

    out_path = Path(ka['out'])

    # Get content sample rate
    command = ['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_entries', 'stream=sample_rate', '-of', 'csv', str(content_path)]
    content_sample_rate = subprocess.run(command,
                                         capture_output=True,
                                         check=True)
    content_sample_rate = content_sample_rate.stdout
    content_sample_rate = content_sample_rate.decode('utf-8')
    content_sample_rate = content_sample_rate.removeprefix('stream,')
    content_sample_rate = int(content_sample_rate)

    with tempfile.TemporaryDirectory() as tempdir:
        longer_intro_silence_path, offset, _ = crosslooper.file_offset(use_argparse=False, **ka)

        if not quiet:
            print(f'"{longer_intro_silence_path}" has longer intro silence, offset is {offset:.12f} seconds')

        if content_path == longer_intro_silence_path:
            if not quiet:
                print(f'Cutting silence off of beginning of {content_path}')

            command = ['ffmpeg', '-i', str(content_path), '-af', f'atrim=start={offset:.12f}', str(Path(tempdir) / 'synced-start.flac')]
            subprocess.run(command,
                           stdout=(None if verbose else subprocess.DEVNULL),
                           stderr=(None if verbose else subprocess.DEVNULL),
                           check=True)
        else:
            if not quiet:
                print(f'Adding silence to beginning of {content_path}')

            # ffmpeg floors the sample count when you pass seconds to adelay.
            # We prefer to round, so we do the math ourselves.
            offset_samples = round(offset * content_sample_rate)

            command = ['ffmpeg', '-i', str(content_path), '-af', f'adelay=delays={offset_samples}S:all=1', str(Path(tempdir) / 'synced-start.flac')]
            subprocess.run(command,
                           stdout=(None if verbose else subprocess.DEVNULL),
                           stderr=(None if verbose else subprocess.DEVNULL),
                           check=True)

        ka['in1'] = timing_path
        ka['in2'] = Path(tempdir)/'synced-start.flac'
        _, zero_offset, _ = crosslooper.file_offset(use_argparse=False, **ka)
        zero_offset_samples = round(zero_offset * content_sample_rate)

        if not quiet:
            print(f'Zero start offset is {zero_offset:.6f} seconds')
        if zero_offset_samples != 0:
            raise Exception(f'{content_path}: Zero start offset is {zero_offset:.6f} seconds')

        _, synced_start_data = crosslooper.normalize_denoise(Path(tempdir) / 'synced-start.flac', 'out', allow_take=False)
        len_synced_start = len(synced_start_data) / content_sample_rate

        timing_sample_rate, timing_data = crosslooper.normalize_denoise(timing_path, 'out', allow_take=False)
        len_timing = len(timing_data) / timing_sample_rate

        if len_synced_start > len_timing:
            if not quiet:
                print(f'"{content_path}" has longer outro silence, offset is {len_synced_start-len_timing} seconds')
                print(f'Cutting silence off of end of {content_path}')

            command = ['ffmpeg', '-i', str(Path(tempdir) / 'synced-start.flac'), '-af', f'atrim=end={len_timing:.12f}', str(Path(tempdir) / 'synced-all.flac')]
            subprocess.run(command,
                           stdout=(None if verbose else subprocess.DEVNULL),
                           stderr=(None if verbose else subprocess.DEVNULL),
                           check=True)
        else:
            if not quiet:
                print(f'"{timing_path}" has longer outro silence, offset is {len_timing-len_synced_start} seconds')
                print(f'Adding silence to end of {content_path}')

            offset = len_timing - len_synced_start

            command = ['ffmpeg', '-i', str(Path(tempdir) / 'synced-start.flac'), '-af', f'apad=pad_dur={offset:.12f}', str(Path(tempdir) / 'synced-all.flac')]
            subprocess.run(command,
                           stdout=(None if verbose else subprocess.DEVNULL),
                           stderr=(None if verbose else subprocess.DEVNULL),
                           check=True)

        synced_all_sample_rate, synced_all_data = crosslooper.normalize_denoise(Path(tempdir) / 'synced-all.flac', 'out', allow_take=False)
        len_synced_all = len(synced_all_data) / synced_all_sample_rate

        zero_offset = len_synced_all - len_timing
        zero_offset_samples = round(zero_offset * content_sample_rate)

        if not quiet:
            print(f'Zero len offset is {zero_offset:.6f} seconds')
        if zero_offset_samples != 0:
            raise Exception(f'{content_path}: Zero len offset is {zero_offset:.6f} seconds')

        shutil.copyfile(Path(tempdir) / 'synced-all.flac', out_path)


main = crosstrimmer
if __name__ == '__main__':
    main()
