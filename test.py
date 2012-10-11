#!/usr/bin/env python3
import subprocess

import snakenest

subprocess.call(
  ["clingo", "example.lp", "-n", "3"],
  stdout=open("out.as", 'w')
)

with open("out.as") as fin:
  raw = fin.read()
answers = snakenest.parse_raw(raw)
#import cProfile
#cProfile.run('snakenest.parse_raw(raw)')

if len(answers) == 3\
and len(answers[0]) == 1342\
and len(answers[1]) == 659\
and len(answers[2]) == 1342:
  print("Parsing test: passed")
else:
  print("Parsing test: failed")

reparsed = snakenest.parse_set(str(answers[0]))

if reparsed == answers[0]:
  print("Reparsing test: passed")
else:
  print("Reparsing test: failed")

with open("orig", 'w') as fout:
  fout.write(str(answers[0]).replace(' ', '\n'))

with open("reparsed", 'w') as fout:
  fout.write(str(reparsed).replace(' ', '\n'))
