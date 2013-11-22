#!/usr/bin/env python3

from bs4 import BeautifulSoup
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
log_file = 'myopera-backup.log'
backup_directory = 'backup-data'

config = configparser.ConfigParser()
config.read(config_file)
user = config.get('DEFAULT', 'user')
password = config.get('DEFAULT', 'password')
counter = config.getint('DEFAULT', 'counter')

# For when we need to send some basic authorization along
credentials = user, password

# Read counter file to resume from last time.
#counter = 1
#counter = 111 # regular old public forum
#test for HTML entity parsing
#counter = 14782702
#test for private groups
#counter = 14951902
#test for comment that does not exist
#counter = 14951903

counter_range = 14000000
#counter_range = counter + 14000000
#counter_range = counter+2

def getCommentFileName(comment_id_int):
	# Directory generation here so we can check if file exists; if it does, SKIP one iteration.
	# There are almost 15 million posts, so let's divide the top level per 100,000; that'll give us 150 directories
	# We can then do another level per 1000
	# So we get e.g. ./data/0-99999/0-999/1.txt
	# To achieve this, let's round down (floor) the comment_id, first divided by 100000 followed by 10000

	import math

	hundred_thousands = math.floor(comment_id_int/100000)
	hundred_thousands_next = hundred_thousands + 1
	hundred_thousands *= 100000
	hundred_thousands_next *= 100000
	hundred_thousands_next -= 1

	hundred_thousands_dir = backup_directory + '/' + str(hundred_thousands)+'-'+str(hundred_thousands_next)

	thousands = math.floor( (comment_id_int) / 1000 )
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
	
	return comment_file_name

def log(message):
	logfile = open(log_file, 'a') #a for append
	logfile.write(message + '\n')
	logfile.close()
	print(message)
	
def skipped(comment_id):
	with open(log_file, 'r') as f:
		for line in f:
			if line.startswith(comment_id + ' skipped'):
				return line[:-1] #minus the last character, although I'd think the newline \n was two
	return False

# Shortcut for sleep
# We don't want to get banned from the server, but we also don't want to take forever. 0.2 is probably too little but let's give it a try
def wait():
	return
	#time.sleep(0.2)

# From http://stackoverflow.com/q/1034573
def xstr(s):
	if s is None:
		return ''
	else:
		return str(s)

# start for loop here, from counter up to ???
# just three files for a first test
for comment_id_int in range(counter, counter_range):
	# we need a string for concatenating
	comment_id = str(comment_id_int)
	
	print('Processing comment '+comment_id+'.')
	
	# Let's not be too hasty after the last request
	wait()

	comment_file_name = getCommentFileName(comment_id_int)

	# Skip this iteration if the comment was already downloaded
	if os.path.exists(comment_file_name):
		print('Skipping '+comment_id+'. File exists.')
		continue
	
	# Skip this iteration if the comment was already skipped earlier for some reason.
	skipped_before = skipped(comment_id)
	if skipped_before:
		print(skipped_before)
		continue

	# Only get headers
	# No authorization required
	page_request = requests.get('http://my.opera.com/community/forums/findpost.pl?id='+comment_id, auth=credentials)
	
	# Skip this iteration if the comment doesn't exist or if authorization is required
	if page_request.ok is False:
		message = comment_id + ' skipped. ' + page_request.reason
		# Write failure to log file.
		log(message)
		continue

	# We need the location
	location = page_request.url
	# and also the page data
	page = page_request.text
	# Time to parse it.
	soup = BeautifulSoup(page)

	# Grab all the relevant metadata from the URL.
	topic_id = re.search(r'id=([0-9]+)', location).group(1)

	#print(location)
	#print(topic_id)

	metadata_soup = soup.find('div', id='forumnav')
	metadata_html = str(metadata_soup)
	
	# Skip this iteration if MyOpera messed up and the topic doesn't exist yet doesn't return not found.
	if not metadata_soup:
		message = comment_id + ' skipped. Empty Topic'
		# Write failure to log file.
		log(message)
		continue
	
	metadata_regex = r'''
<h1>(.*?)</h1>
<p class="forumnav"><a href="/[\w]+/forums/">Forums</a>   » <a dir="ltr" href="/community/forums/tgr.dml\?id=([0-9]+)">(.+?)</a>  » <a href="forum\.dml\?id=([0-9]+)">(.+?)</a></p>
</div>'''
	
	metadata = re.search(metadata_regex, metadata_html)
	
	#print(metadata.group(0))
	forum_category_id = metadata.group(2)
	forum_category = metadata.group(3)
	forum_id = metadata.group(4)
	forum_name = metadata.group(5)
	topic_title = metadata.group(1)
	#print(forum_id)
	#print(forum_name)
	#print(topic_title)
	
	comments = soup.findAll('div', 'fpost')
	
	###############
	# enter individual comments for loop
	for comment in comments:
		post_html = str(comment)
		
		post_soup = BeautifulSoup(post_html)
		
		posted_html = post_soup.find('p', 'posted')
		posted_html = str(posted_html)
		
		posted_regex = r'<p class="posted">(?:<span class="unread">unread</span>)?<a href="findpost\.pl\?id=([0-9]+)" title="permanent link to post">\s?(.*?)</a>(?: <b>\((edited)\)</b>)?</p>'
		posted_meta = re.search(posted_regex, posted_html)
		
		comment_id = posted_meta.group(1)
		# Needed for comment 1350280. Might there be more?
		timestamp = xstr(posted_meta.group(2))
		# Need empty string instead of None type if None
		edited = xstr(posted_meta.group(3))
		
		for link in post_soup.findAll('a'):
			if link.parent.name == 'b' and link.parent.parent.name == 'p' and link.parent.parent.parent.name == 'div' and link.parent.parent.parent.attrs == {'class': ['poster']}:
				user_html = str(link)
				user_regex = r'<a href=".+?"(?: title=".+?")?>(.*?)</a>'
				user = xstr(re.search(user_regex, user_html).group(1))
		
		# These next few lines are duplicated; oh noez! We could make it a
		# function or something.
		comment_file_name = getCommentFileName(int(comment_id))
		
		# Skip this iteration if the comment was already written
		if os.path.exists(comment_file_name):
			print('Skipping '+comment_id+'. File exists.')
			continue
		
		# write post file
		# format something simple and logical, e.g.
		'''
		comment_id
		timestamp
		edited
		user
		forum_category
		forum_category_id
		forum_name
		forum_id
		topic_title
		topic_id
	
		post_html
		'''
		# in this format line 1 is user name, line 2 is comment id, etc. line 10 (or whatever) and all following is the comment
		
		#write post backup file
		comment_file = open(comment_file_name, 'w')
		
		comment_file.write(comment_id + '\n')
		comment_file.write(timestamp + '\n')
		comment_file.write(edited + '\n')
		comment_file.write(user + '\n')
		comment_file.write(forum_category + '\n')
		comment_file.write(forum_category_id + '\n')
		comment_file.write(forum_name + '\n')
		comment_file.write(forum_id + '\n')
		comment_file.write(topic_title + '\n')
		comment_file.write(topic_id + '\n')
		comment_file.write('\n')
		comment_file.write(post_html)
		
		comment_file.close()
	
	########
	#exit for loop
	# write counter file
	comment_id_int += 1 #need to start from one higher next time
	comment_id = str(comment_id_int)
	config.set('DEFAULT', 'counter', comment_id)
	with open(config_file, 'w') as cf:
		config.write(cf)