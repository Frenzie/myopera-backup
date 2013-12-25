#!/usr/bin/env python3

import os
import re

backup_directory = 'backup-data'

check = ['</div>']

for root, dirs, files in os.walk(backup_directory):
	for file in files:
		if file.endswith(".txt"):
			file_path = os.path.join(root, file)
			
			with open(file_path, 'r') as f:
				content = f.readlines()
			
			if content[-1:] != check:
				print(file_path)
				print(content[-3:])