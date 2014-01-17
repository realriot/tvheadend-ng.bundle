import urllib2, base64, simplejson, time
json = simplejson

# Static text. 
TEXT_NAME = 'TV-Headend Next Generation'
TEXT_TITLE = 'TV-Headend' 

# Image resources.
ICON_MAIN = 'main.png'
ICON_SETTINGS = 'settings.png'
ICON_CHANNEL = 'channel.png'
ICON_TAG = 'tag.png'

# Other definitions.
PLUGIN_PREFIX = '/video/tvheadend-ng'
debug = True

####################################################################################################

def Start():
	Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, TEXT_NAME, ICON_MAIN)
	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
	Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
	HTTP.CacheTime = 1

####################################################################################################

@handler('/video/tvheadend-ng', TEXT_TITLE, thumb=ICON_MAIN)
def MainMenu():
	oc = ObjectContainer(view_group='InfoList', no_cache=True)	

	if checkConfig():
		oc.title1 = TEXT_TITLE
		oc.header = None
		oc.message = None 
		oc = ObjectContainer(title1=TEXT_TITLE, no_cache=True)
		oc.add(DirectoryObject(key=Callback(getChannels, title=L('allchans')), title=L('allchans')))
		oc.add(DirectoryObject(key=Callback(getChannelsByTag, title=L('tagchans')), title=L('tagchans')))
		oc.add(PrefsObject(title=L('preferences'), thumb=R(ICON_SETTINGS)))
	else:
		oc.title1 = None
		oc.header = L('header_attention')
                oc.message = L('error_no_config')
		oc.add(PrefsObject(title=L('preferences'), thumb=R(ICON_SETTINGS)))

	return oc

####################################################################################################

def checkConfig():
	if Prefs['tvheadend_user'] != "" and Prefs['tvheadend_pass'] != "" and Prefs['tvheadend_host'] != "" and Prefs['tvheadend_web_port'] != "":
		# To validate the tvheadend connection, the function to fetch the channeltags will be used.
		json_data = getTVHeadendJsonOld('channeltags')
		if json_data != False:
			return True
		else:
			return False
	else:
		return False

def getTVHeadendJsonOld(what, url = False):
	tvh_url = dict( channeltags='op=listTags', epg='start=0&limit=300')
	if url != False: 
		tvh_url[what] = url

	try:
		base64string = base64.encodestring('%s:%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'])).replace('\n', '')
		request = urllib2.Request("http://%s:%s/%s" % (Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], what),tvh_url[what])
		request.add_header("Authorization", "Basic %s" % base64string)
		response = urllib2.urlopen(request)
		json_tmp = response.read()
		json_data = json.loads(json_tmp)
	except:
		return False	
	return json_data

def getTVHeadendJson(apirequest, arg1):
	api = dict(
		getChannelGrid='api/channel/grid?start=0&limit=999999',
		getEpgGrid='api/epg/grid?start=0&limit=1000',
		getIdNode='api/idnode/load?uuid=' + arg1
	)

	try:
                base64string = base64.encodestring('%s:%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'])).replace('\n', '')
                request = urllib2.Request("http://%s:%s/%s" % (Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], api[apirequest]))
                request.add_header("Authorization", "Basic %s" % base64string)
                response = urllib2.urlopen(request)

                json_tmp = response.read()
                json_data = json.loads(json_tmp)
	except:
		return False
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

####################################################################################################

def getChannelsByTag(title):
	json_data = getTVHeadendJsonOld('channeltags')
	tagList = ObjectContainer(no_cache=True)

	if json_data != False:
		tagList.title1 = L('tagchans')
		tagList.header = None
		tagList.message = None
		for tag in json_data['entries']:
			if debug == True: Log("Getting channellist for tag: " + tag['name'])
			tagList.add(DirectoryObject(key=Callback(getChannels, title=tag['name'], tag=int(tag['identifier'])), title=tag['name']))
	else:
		tagList.title1 = None
		tagList.header = L('error')
		tagList.message = L('error_request_failed') 
	return tagList 

def getChannels(title, tag=int(0)):
	json_data = getTVHeadendJson('getChannelGrid', '')
	json_epg = getEPG()
	channelList = ObjectContainer(no_cache=True)

	if json_data != False:
		channelList.title1 = title
		channelList.header = None
		channelList.message = None
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
	else:
		channelList.title1 = None;
		channelList.header = L('error')
		channelList.message = L('error_request_failed')
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
	url_structure = 'stream/channel'
	url_base = 'http://%s:%s@%s:%s/%s/' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], url_structure)
	url_transcode = '?mux=mpegts&acodec=aac&vcodec=H264&transcode=1'
	vurl = url_base + id + url_transcode

	# Create media object for a 576px resolution.
	mo384 = MediaObject(
		container = 'mpegts',
		video_codec = VideoCodec.H264,
		audio_codec = AudioCodec.AAC,
		audio_channels = 2,
		optimized_for_streaming = False,
		video_resolution = 384,
		parts = [PartObject(key = vurl + "&resolution=384")]
	)
	vco = VideoClipObject(
		key = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, container = True),
		rating_key = id,
		title = name,
		summary = summary,
		duration = chaninfo['epg_duration'],
		thumb = icon,
	)
	vco.add(mo384)

	# Create media object for a 576px resolution.
        mo576 = MediaObject(
                container = 'mpegts',
                video_codec = VideoCodec.H264,
                audio_codec = AudioCodec.AAC,
                audio_channels = 2,
                optimized_for_streaming = False,
        )
	if channel['name'].endswith('HD'):
		mo576.video_resolution = 576
		mo576.parts = [PartObject(key = vurl + "&resolution=576")]
	else:
		mo576.video_resolution = 576
		mo576.parts = [PartObject(key = vurl)]	 
	vco.add(mo576)

	# Create mediaobjects for hd tv-channels.
	if channel['name'].endswith('HD'):
		mo768 = MediaObject(
			container = 'mpegts',
			video_codec = VideoCodec.H264,
			audio_codec = AudioCodec.AAC,
			audio_channels = 2,
			optimized_for_streaming = False,
			video_resolution = 768,
			parts = [PartObject(key = vurl + "&resolution=768")]
		)
		mo1080 = MediaObject(
			container = 'mpegts',
			video_codec = VideoCodec.H264,
			audio_codec = AudioCodec.AAC,
			audio_channels = 2,
			optimized_for_streaming = False,
			video_resolution = 1080,
			parts = [PartObject(key = vurl)]
		)
		vco.add(mo768)
		vco.add(mo1080)

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco
	return vco
