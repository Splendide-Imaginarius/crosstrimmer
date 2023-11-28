#!/usr/bin/env python3

from copy import deepcopy
from multiprocessing import Process, Queue, Lock
import os
from pathlib import Path

from tqdm import tqdm

import crosstrimmer


def cli_parser(**ka):
    parser = crosstrimmer.cli_parser(content=None, timing=None, out=None, **ka)

    if 'content' not in ka:
        parser.add_argument(
            'content',
            action='store',
            type=str,
            help='Directory of audio files containing content to trim.')
    if 'timing' not in ka:
        parser.add_argument(
            'timing',
            action='store',
            type=str,
            help='Directory of audio files containing timing to apply to the content.')
    if 'out' not in ka:
        parser.add_argument(
            'out',
            action='store',
            type=str,
            help='Directory to write FLAC files containing the trimmed content.')
    if 'threads' not in ka:
        parser.add_argument(
            '--threads',
            dest='threads',
            action='store',
            default=None,
            type=int,
            help='Number of threads to use. ' +
                 '(default: use all hardware threads)')

    return parser


def loop_process_run(input_file_queue, progress_queue, pbar_lock, process_num,
                     ka):
    tqdm.set_lock(pbar_lock)

    while True:
        finished, content, timing, out = input_file_queue.get()
        if finished:
            break

        timing_all = timing.parent.glob(timing.stem + '.*')
        try:
            timing = next(timing_all)
        except StopIteration:
            progress_queue.put(1)
            continue

        out = out.with_suffix('.flac')

        if not content.exists() or not timing.exists():
            progress_queue.put(1)
            continue

        if not content.is_file() or not timing.is_file():
            progress_queue.put(1)
            continue

        os.makedirs(out.parent, exist_ok=True)

        this_ka = deepcopy(ka)
        this_ka['content'] = content
        this_ka['timing'] = timing
        this_ka['out'] = out

        crosstrimmer.crosstrimmer(use_argparse=False,
                                  **this_ka)

        progress_queue.put(1)


def crosstrimmer_dir(**ka):
    """CLI interface to make a directory of audio files match the timing of a
    another directory of audio files containing similar content.
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
    ka['samples'] = True
    ka['skip'] = False
    ka['quiet'] = True

    parser = cli_parser(**ka)
    args = parser.parse_args().__dict__
    ka.update(args)

    ka['loop-search-len'] = -1

    content_dir = ka['content']
    timing_dir = ka['timing']
    out_dir = ka['out']

    # Validate dirs

    content_dir = Path(content_dir)
    timing_dir = Path(timing_dir)
    out_dir = Path(out_dir)

    content_dir = content_dir.resolve()
    timing_dir = timing_dir.resolve()
    out_dir = out_dir.resolve()

    if not content_dir.exists():
        raise Exception(f'Folder "{content_dir}" does not exist.')
    if not timing_dir.exists():
        raise Exception(f'Folder "{timing_dir}" does not exist.')
    if not out_dir.exists():
        raise Exception(f'Folder "{out_dir}" does not exist.')

    if content_dir.is_file():
        raise Exception(f'Folder "{content_dir}" is a file.')
    if timing_dir.is_file():
        raise Exception(f'Folder "{timing_dir}" is a file.')
    if out_dir.is_file():
        raise Exception(f'Folder "{out_dir}" is a file.')

    content_files = list(content_dir.glob("**/*"))

    pbar_lock = Lock()
    tqdm.set_lock(pbar_lock)

    total_pbar = tqdm(unit='track', position=0)
    total_pbar.set_description('folder')
    total_pbar.reset(total=len(content_files))

    input_file_queue = Queue()

    process_num = ka['threads']
    if process_num is None:
        process_num = os.cpu_count()

    progress_queue = Queue()

    loop_processes = []
    for p in range(process_num):
        loop_processes.append(Process(target=loop_process_run,
                                      args=(input_file_queue,
                                            progress_queue,
                                            pbar_lock,
                                            p,
                                            ka)))

    for p in loop_processes:
        p.start()

    for content_f in content_files:
        timing_f = timing_dir / (content_f.relative_to(content_dir))
        out_f = out_dir / (content_f.relative_to(content_dir))
        input_file_queue.put((False, content_f, timing_f, out_f))

    for content_f in content_files:
        progress_queue.get()
        total_pbar.update(1)

    for p in loop_processes:
        input_file_queue.put((True, None, None, None))


main = crosstrimmer_dir
if __name__ == '__main__':
    main()
