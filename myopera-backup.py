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

config = configparser.ConfigParser()
config.read([os.path.expanduser(config_file)])
user = config.get('DEFAULT', 'user')
password = config.get('DEFAULT', 'password')
counter = config.getint('DEFAULT', 'counter')

# For when we need to send some basic authorization along
credentials = user, password

# Read counter file to resume from last time.
counter = 111 # regular old public forum
#test for HTML entity parsing
#counter = 14782702
#test for private groups
counter = 14951902


# Shortcut for sleep
# We don't want to get banned from the server.
def wait():
	time.sleep(5)

# start for loop here, from counter up to ???

# more logical variable name; also we need a string for concatenating
comment_id = str(counter)

# Only get headers
# No authorization required
header_request = requests.head('http://my.opera.com/community/forums/findpost.pl?id='+comment_id)

# findpost.pl redirects, find out where
location = header_request.headers['location']

# Grab all the relevant metadata.
topic_id = re.search(r'id=([0-9]+)', location).group(1)
timestamp = re.search(r't=([0-9]+)', location).group(1)

print(location)
print(topic_id)
print(comment_id)
print(timestamp)

wait()

# Construct quote URL
quote_request_url = 'http://my.opera.com/community/forums/reply.dml?action=quote&commentid='+comment_id+'&id='+topic_id
print(quote_request_url)

quote_request = requests.get(quote_request_url, auth=credentials)

quote_page = quote_request.text

# True if HTTP status 200; False for e.g. 401 or 404. Maybe check actual error codes and raise an alarm if it's not 401 or 404? Or write some kind of error log under else?
if (quote_request.ok):
	#print(quote_page)
	
	metadata = re.search(r'<div id="forumnav"><p class="forumnav"><a href="/[\w]+/forums/">Forums</a>  » <a href="forum\.dml\?id=([0-9]+)">(.+?)</a> » <a href="topic\.dml\?id=[0-9]+">(.+?)</a>', quote_page)
	
	print(metadata.group(0))
	forum_id = metadata.group(1)
	forum_name = metadata.group(2)
	topic_title = metadata.group(3)
	print(forum_id)
	print(forum_name)
	print(topic_title)
	
	# re.DOTALL makes dot also match newlines
	post = re.search(r'<textarea name="comment" id="postcontent" rows="20" cols="60">\[quote=([\w]+)](.+?)\[/quote] </textarea>', quote_page, re.DOTALL)
	user = post.group(1)
	post_text = post.group(2)
	
	print(user)
	#print(post_text)
	
	# Decode HTML entities
	# Thanks to http://stackoverflow.com/a/2087433
	import html.parser
	h = html.parser.HTMLParser()
	post_text = h.unescape(post_text)
	
	print(post_text)
	
	#################
	#we're still missing the forum category; grab it using the topic id or forum id
	
	
	# write post file
	# format something simple and logical, e.g.
	'''
	user
	comment_id
	timestamp
	forum_category_id
	forum_category
	forum_id
	forum_name
	topic_id
	topic_title

	post_text
	'''
	# in this format line 1 is user name, line 2 is comment id, etc. line 10 (or whatever) and all following is the comment
	
	
	# write counter file
	# we apparently can't trust configparser's write function because it uses dictionaries, so we simply replace line 4 or something
	#f = open('test.ini', 'w'); f.write('blabla')
	# maybe try this http://stackoverflow.com/questions/1877999/delete-final-line-in-file-via-python
	
	'''
	readFile = open(config_file)

	lines = readFile.readlines()

	readFile.close()
	w = open("file",'w')

	w.writelines([item for item in lines[:-1]])

	w.close()
	'''
	
	# Wait before we go to the next post
	#counter+=1
	#wait()