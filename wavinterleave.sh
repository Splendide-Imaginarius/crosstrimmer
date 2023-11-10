#!/usr/bin/env bash

set -euo pipefail

mkdir -p working

FIRST="$1"
shift
SECOND="$1"
shift

SEGMENT_TIME="$1"
shift

OUT="$1"
shift

mkdir -p "working/first"
mkdir -p "working/second"

ffmpeg -i "${FIRST}" -f segment -segment_time "${SEGMENT_TIME}" "working/first/out%03d.flac"
ffmpeg -i "${SECOND}" -f segment -segment_time "${SEGMENT_TIME}" "working/second/out%03d.flac"

mkdir -p "working/interleaved"
# || true because for very short audio, there may not be a *8 or *9.
cp working/first/*0.flac working/first/*2.flac working/first/*4.flac working/first/*6.flac working/first/*8.flac  "working/interleaved/" || true
cp working/second/*1.flac working/second/*3.flac working/second/*5.flac working/second/*7.flac working/second/*9.flac "working/interleaved/" || true

sox working/interleaved/*.flac "${OUT}"

rm -rf "working"
