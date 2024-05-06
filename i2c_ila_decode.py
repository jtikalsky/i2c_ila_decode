#!/usr/bin/python

import argparse
import csv
from typing import List

parser = argparse.ArgumentParser()
parser.add_argument(
    '-p',
    '--probe',
    type=int,
    default=0,
    help="The zero-indexed probe to interpret.\n"
    "The probe value (2 bits wide) will be interpreted as probe[0]=SCL probe[1]=SDA"
)
parser.add_argument('-r', '--raw', action='store_true', help='Bits instead of bytes')
parser.add_argument('waveform')
ARGS = parser.parse_args()
del parser


def load_waveform(fn: str) -> List[List[int]]:
	with open(fn, 'r') as fd:
		return [[
		    int(y) for y in x
		] for x in csv.reader(line for line in fd if not line.startswith('Radix') and not line.startswith('Sample'))]


def parse_i2c_bitstream(waveform: List[List[int]], probe: int) -> List[str]:
	# Output:
	# '[' = start
	# ']' = stop
	# '1' = data
	# '0' = data

	# Sample; Sample in Window; Trigger; Probes...
	windows: List[str] = []
	prev_scl = 1
	prev_sda = 1
	for transition in waveform:
		if transition[1] == 0:
			windows.append('')  # New window starting now.
		busval = transition[3 + probe]
		scl = (busval >> 0) & 1
		sda = (busval >> 1) & 1

		if scl and prev_sda and not sda:
			windows[-1] += '['
		elif scl and not prev_sda and sda:
			if len(windows[-1]) and windows[-1][-1] in '01':
				# Stop condition requires the clock to be up, which counts as an extra rising edge, I guess.
				windows[-1] = windows[-1][:-1]
			windows[-1] += ']'
		elif not prev_scl and scl:
			windows[-1] += str(sda)
		prev_scl = scl
		prev_sda = sda

	return windows


def format_bitstream(bitstream: str) -> str:
	out = ''
	count = 0
	for c in bitstream:
		if c in '[]':
			count = 0
			out = out.rstrip() + f' {c} '
		elif c in '01':
			count += 1
			if count == 9:
				if c == '0':
					out += ' A '
				elif c == '1':
					out += ' N '
				else:
					out += f' {c} '
				count = 0
			else:
				out += c
	return out


def hexify_formatted_bitstream(bitstream: str) -> str:
	fields = bitstream.split(' ')
	fields = [
	    '0x{:02X}'.format(int(f, 2)) if len(f) == 8 and not f.replace('0', '').replace('1', '') else f for f in fields
	]
	return ' '.join(fields)


waveform = load_waveform(ARGS.waveform)
bitstreams = parse_i2c_bitstream(waveform, ARGS.probe)

for sequence in bitstreams:
	if ARGS.raw:
		print(format_bitstream(sequence).strip())
	else:
		print(hexify_formatted_bitstream(format_bitstream(sequence)).strip())
