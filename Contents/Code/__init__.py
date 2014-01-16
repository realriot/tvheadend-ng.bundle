import urllib2, base64, simplejson, time
json = simplejson

NAME = 'TV-Headend Next Generation'
#ART = 'art-default.jpg'
PLUGIN_PREFIX = '/video/tvheadend-ng'

# Preferences
options_username = '%s' % (Prefs['tvheadend_user']) 
options_password = '%s' % (Prefs['tvheadend_pass'])
options_hostname = '%s' % (Prefs['tvheadend_host'])
options_web_port = '%s' % (Prefs['tvheadend_web_port'])
options_htsp_port = '%s' % (Prefs['tvheadend_htsp_port'])

# URL structure
url_structure = 'stream/channel'
url_transcode = '?mux=mpegts&acodec=aac&vcodec=H264&transcode=1&resolution=384'
url_base = 'http://%s:%s@%s:%s/%s/' % (options_username, options_password, options_hostname, options_web_port, url_structure)

# Static texts
TEXT_TITLE = u'TV-Headend'
TEXT_ALLCHANNELS = u'All channels'
TEXT_TAGCHANNELS = u'Tagged channels'
TEXT_PREFERENCES = u'Settings'

# Resources
ICON_MAIN = 'main.png'
ICON_SETTINGS = 'settings.png'
ICON_CHANNEL = 'channel.png'
ICON_TAG = 'tag.png'

# Debug mode
debug = True

####################################################################################################

def Start():
	Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, NAME, ICON_MAIN)

####################################################################################################

@handler('/video/tvheadend', TEXT_TITLE, thumb=ICON_MAIN)
def MainMenu():
	oc = ObjectContainer(title1=TEXT_TITLE)
	oc.add(DirectoryObject(key=Callback(getChannels, prevTitle=TEXT_ALLCHANNELS), title=TEXT_ALLCHANNELS))
	oc.add(DirectoryObject(key=Callback(getChannelsByTag, prevTitle=TEXT_TITLE), title=TEXT_TAGCHANNELS))
	oc.add(PrefsObject(title=TEXT_PREFERENCES, thumb=R(ICON_SETTINGS)))
	return oc

####################################################################################################

def getTVHeadendJsonOld(what, url = False):
	tvh_url = dict( channeltags='op=listTags', epg='start=0&limit=300')
	if url != False: 
		tvh_url[what] = url
        base64string = base64.encodestring('%s:%s' % (options_username, options_password)).replace('\n', '')
        request = urllib2.Request("http://%s:%s/%s" % (options_hostname, options_web_port, what),tvh_url[what])
        request.add_header("Authorization", "Basic %s" % base64string)
        response = urllib2.urlopen(request)
        json_tmp = response.read()
        json_data = json.loads(json_tmp)
        return json_data

def getTVHeadendJson(apirequest, arg1):
	api = dict(
		getChannelGrid='api/channel/grid?start=0&limit=999999',
		getEpgGrid='api/epg/grid?start=0&limit=1000',
		getIdNode='api/idnode/load?uuid=' + arg1
	)

	base64string = base64.encodestring('%s:%s' % (options_username, options_password)).replace('\n', '')
	request = urllib2.Request("http://%s:%s/%s" % (options_hostname, options_web_port, api[apirequest]))
	request.add_header("Authorization", "Basic %s" % base64string)
	response = urllib2.urlopen(request)

	json_tmp = response.read()
	json_data = json.loads(json_tmp)
	return json_data

####################################################################################################

def getEPG():
	json_data = getTVHeadendJson('getEpgGrid','')
	return json_data

def getChannelInfo(uuid, json_epg):
	result = {
		'iconurl':'',
		'epg_title':'',
		'epg_description':'',
		'epg_duration':0,
		'epg_start':0,
		'epg_stop':0,
		'epg_summary':''
	}

	json_data = getTVHeadendJson('getIdNode', uuid)
	if json_data['entries'][0]['params'][2].get('value'):
		result['iconurl'] = json_data['entries'][0]['params'][2].get('value')

	for epg in json_epg['events']:
		if epg['channelUuid'] == uuid:
			if epg.get('title'):
				 result['epg_title'] = epg['title'];
			if epg.get('description'):
				 result['epg_description'] = epg['description'];
			if epg.get('duration'):
				result['epg_duration'] = epg['duration']*1000;
			if epg.get('start'):
				result['epg_start'] = time.strftime("%H:%M", time.localtime(int(epg['start'])));
			if epg.get('stop'):
				result['epg_stop'] = time.strftime("%H:%M", time.localtime(int(epg['stop'])));
	return result

def lookupVideoObject(video_url, title, thumb):
	oc = ObjectContainer()

	oc.add(VideoClipObject(
		key = Callback(lookupVideoObject, video_url = video_url, title = title, thumb = thumb),
		rating_key = video_url,
		title = title,
		thumb = thumb,
		items = [
			MediaObject(
				container = Container.MP4,
				video_codec = VideoCodec.H264,
				audio_codec = AudioCodec.AAC,
				audio_channels = 2,
				parts = [PartObject(key = video_url)]
			)
		]
	))
        return oc

####################################################################################################

def getChannelsByTag(prevTitle):
	json_data = getTVHeadendJsonOld('channeltags')
	tagList = ObjectContainer(title1=TEXT_TAGCHANNELS, no_cache=True)

	for tag in json_data['entries']:
		if debug == True: Log("Getting channellist for tag: " + tag['name'])
		tagList.add(DirectoryObject(key=Callback(getChannels, prevTitle=tag['name'], tag=int(tag['identifier'])), title=tag['name']))
	return tagList 

def getChannels(prevTitle, tag=int(0)):
	json_data = getTVHeadendJson('getChannelGrid', '')
	json_epg = getEPG()
	channelList = ObjectContainer(title1=prevTitle, no_cache=True)

	for channel in json_data['entries']:
		if tag > 0:
			tags = channel['tags']
			for tids in tags:
				if (tag == int(tids)):
					if debug == True: Log("Got channel with tag: " + channel['name'])
					chaninfo = getChannelInfo(channel['uuid'], json_epg)
					channelList.add(createTVChannelObject(channel, chaninfo))
		else:
			chaninfo = getChannelInfo(channel['uuid'], json_epg)
			channelList.add(createTVChannelObject(channel, chaninfo))

       	return channelList

def createTVChannelObject(channel, chaninfo, container = False):
	name = channel['name'] 
	if chaninfo['iconurl'] != "":
		icon = chaninfo['iconurl']
	else:
		icon = R(ICON_CHANNEL)
	id = channel['uuid'] 
	summary = ''

	# Add epg data.
	if chaninfo['epg_title'] != "" and chaninfo['epg_start'] != 0 and chaninfo['epg_stop'] != 0 and chaninfo['epg_duration'] != 0:
		summary = '%s (%s-%s)\n\n%s' % (chaninfo['epg_title'],chaninfo['epg_start'],chaninfo['epg_stop'], summary)
		duration = chaninfo['epg_duration'];
		name = name + " (" + chaninfo['epg_title'] + ") - (" + chaninfo['epg_start'] + "-" + chaninfo['epg_stop'] + ")"

	# Build streaming url.
	vurl = "%s%s%s" % (url_base, id, url_transcode)

	vco = VideoClipObject(
		key = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, container = True),
		rating_key = id,
		title = name,
		summary = summary,
		duration = chaninfo['epg_duration'],
		thumb = icon,
		items = [
			MediaObject(
				container = 'mpegts',
				video_codec = VideoCodec.H264,
				audio_codec = AudioCodec.AAC,
				audio_channels = 2,
				optimized_for_streaming = True,
				parts = [PartObject(key = vurl)]
			)
		]
	)

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco
	return vco
