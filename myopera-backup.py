#!/usr/bin/env python3

import configparser
import os
import re
#http://docs.python-requests.org/en/latest/index.html
import requests
# For delay
import time

'''
myopera-backup.ini should exist in the same directory as this script. Contents should look like this:

[DEFAULT]
user=username
password=password
counter=1
'''
#or maybe make user/pass optional and start at 1 if nothing found…
config_file = 'myopera-backup.ini'
backup_directory = 'backup-data'

config = configparser.ConfigParser()
config.read(config_file)
user = config.get('DEFAULT', 'user')
password = config.get('DEFAULT', 'password')
counter = config.getint('DEFAULT', 'counter')

# For when we need to send some basic authorization along
credentials = user, password

# Read counter file to resume from last time.
#counter = 111 # regular old public forum
#test for HTML entity parsing
#counter = 14782702
#test for private groups
#counter = 14951902
#test for comment that does not exist
#counter = 14951903

def log(message):
	logfile = open('myopera-backup.log', 'a') #a for append
	logfile.write(message + '\n')
	logfile.close()
	
# Shortcut for sleep
# We don't want to get banned from the server, but we also don't want to take forever. 0.2 is probably too little but let's give it a try
def wait():
	time.sleep(0.2)

# start for loop here, from counter up to ???
# just three files for a first test
for comment_id_int in range(counter, counter + 1000):
	# we need a string for concatenating
	comment_id = str(comment_id_int)
	
	print('Processing comment '+comment_id+'.')
	
	# Let's not be too hasty after the last request
	wait()

	###################
	# Directory generation here so we can check if file exists; if it does, SKIP one iteration.
	# There are almost 15 million posts, so let's divide the top level per 100,000; that'll give us 150 directories
	# We can then do another level per 1000
	# So we get e.g. ./data/0-99999/0-999/1.txt
	# To achieve this, let's round down (floor) the comment_id, first divided by 100000 followed by 10000

	import math

	hundred_thousands = math.floor(counter/100000)
	hundred_thousands_next = hundred_thousands + 1
	hundred_thousands *= 100000
	hundred_thousands_next *= 100000
	hundred_thousands_next -= 1

	hundred_thousands_dir = backup_directory + '/' + str(hundred_thousands)+'-'+str(hundred_thousands_next)

	thousands = math.floor( (counter - hundred_thousands) / 1000 )
	thousands_next = thousands + 1
	thousands *= 1000
	thousands_next *= 1000
	thousands_next -= 1

	thousands_dir = hundred_thousands_dir + '/' + str(thousands)+'-'+str(thousands_next)

	if os.path.isdir(backup_directory) is False:
		os.mkdir(backup_directory)

	if os.path.isdir(hundred_thousands_dir) is False:
		os.mkdir(hundred_thousands_dir)

	if os.path.isdir(thousands_dir) is False:
		os.mkdir(thousands_dir)

	comment_file_name = thousands_dir + '/' + comment_id+'.txt'

	# Skip this iteration if the comment was already downloaded
	if os.path.exists(comment_file_name):
		print('Skipping '+comment_id+'. File exists.')
		continue

	# Only get headers
	# No authorization required
	header_request = requests.head('http://my.opera.com/community/forums/findpost.pl?id='+comment_id)
	
	# Skip this iteration if the comment doesn't exist
	if header_request.ok is False:
		print('Skipping '+comment_id+'. Does not exist on server.')
		# Write failure to log file.
		log(comment_id + ' skipped. Does not exist on server.')
		continue

	# findpost.pl redirects, find out where
	location = header_request.headers['location']

	# Grab all the relevant metadata.
	topic_id = re.search(r'id=([0-9]+)', location).group(1)
	timestamp = re.search(r't=([0-9]+)', location).group(1)

	#print(location)
	#print(topic_id)
	#print(comment_id)
	#print(timestamp)

	wait()

	# Construct quote URL
	quote_request_url = 'http://my.opera.com/community/forums/reply.dml?action=quote&commentid='+comment_id+'&id='+topic_id
	#print(quote_request_url)

	quote_request = requests.get(quote_request_url, auth=credentials)

	# True if HTTP status 200; False for e.g. 401 or 404. Maybe check actual error codes and raise an alarm if it's not 401 or 404? Or write some kind of error log under else?
	# Anyhoo, skip this iteration if False, because then we don't have read access.
	if quote_request.ok is False:
		print('Skipping '+comment_id+'. Authorization or other problem.')
		# Write failure to log file.
		log(comment_id + ' skipped. Authorization or other problem.')
		continue
	
	quote_page = quote_request.text
	#print(quote_page)
	
	metadata = re.search(r'<div id="forumnav"><p class="forumnav"><a href="/[\w]+/forums/">Forums</a>  » <a href="forum\.dml\?id=([0-9]+)">(.+?)</a> » <a href="topic\.dml\?id=[0-9]+">(.+?)</a>', quote_page)
	
	#print(metadata.group(0))
	forum_id = metadata.group(1)
	forum_name = metadata.group(2)
	topic_title = metadata.group(3)
	#print(forum_id)
	#print(forum_name)
	#print(topic_title)
	
	# re.DOTALL makes dot also match newlines
	post = re.search(r'<textarea name="comment" id="postcontent" rows="20" cols="60">\[quote=(.+?)](.+?)\[/quote] </textarea>', quote_page, re.DOTALL)
	user = post.group(1)
	post_text = post.group(2)
	
	# Decode HTML entities
	# Thanks to http://stackoverflow.com/a/2087433
	import html.parser
	h = html.parser.HTMLParser()
	post_text = h.unescape(post_text)
	
	#print(user)
	#print(post_text)
	
	#################
	#we're still missing the forum category; grab it using the topic id or forum id
	#forum_id with perscreen=1 is most likely the smallest
	category_request_url = 'http://my.opera.com/community/forums/forum.dml?id='+forum_id+'&perscreen=1'
	category_request = requests.get(category_request_url, auth=credentials)
	
	metadata = re.search(r'<p class="forumnav"><a href="/[\w]+/forums/">Forums</a>   » <a href="/community/forums/tgr.dml\?id=([0-9]+)" dir="ltr">(.+?)</a>', category_request.text)
	
	forum_category_id = metadata.group(1)
	forum_category = metadata.group(2)
	
	#print(forum_category_id)
	#print(forum_category)
	
	
	# write post file
	# format something simple and logical, e.g.
	'''
	comment_id
	user
	timestamp
	forum_category
	forum_category_id
	forum_name
	forum_id
	topic_title
	topic_id

	post_text
	'''
	# in this format line 1 is user name, line 2 is comment id, etc. line 10 (or whatever) and all following is the comment
	
	#write post backup file
	comment_file = open(comment_file_name, 'w')
	
	comment_file.write(comment_id + '\n')
	comment_file.write(user + '\n')
	comment_file.write(timestamp + '\n')
	comment_file.write(forum_category + '\n')
	comment_file.write(forum_category_id + '\n')
	comment_file.write(forum_name + '\n')
	comment_file.write(forum_id + '\n')
	comment_file.write(topic_title + '\n')
	comment_file.write(topic_id + '\n')
	comment_file.write('\n')
	comment_file.write(post_text)
	
	comment_file.close() 
	
	# write counter file
	comment_id_int += 1 #need to start from one higher next time
	comment_id = str(comment_id_int)
	config.set('DEFAULT', 'counter', comment_id)
	with open(config_file, 'w') as cf:
		config.write(cf)