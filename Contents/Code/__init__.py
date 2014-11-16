import urllib2, base64, simplejson, time
json = simplejson

# Static text. 
TEXT_NAME = 'TV-Headend Next Generation'
TEXT_TITLE = 'TV-Headend' 

# Image resources.
ICON_DEFAULT = 'icon-default.png'
ART_DEFAULT = 'art-default.jpg'

ICON_ALLCHANS = R('icon_allchans.png')
ICON_BOUQUETS = R('icon_bouquets.png')

# Other definitions.
PLUGIN_PREFIX = '/video/tvheadend-ng'
debug = True
debug_epg = False 
req_api_version = 15

####################################################################################################

def Start():
	ObjectContainer.art = R(ART_DEFAULT)
	HTTP.CacheTime = 1

####################################################################################################

@handler(PLUGIN_PREFIX, TEXT_TITLE, ICON_DEFAULT, ART_DEFAULT)
def MainMenu():
	oc = ObjectContainer(no_cache=True)	

	result = checkConfig()
	if result['status'] == True:
		if debug == True: Log("Configuration OK!")
		oc.title1 = TEXT_TITLE
		oc.header = None
		oc.message = None 
		oc = ObjectContainer(title1=TEXT_TITLE, no_cache=True)
		if Prefs['tvheadend_allchans'] != False:
			oc.add(DirectoryObject(key=Callback(getChannels, title=L('allchans')), title=L('allchans'), thumb=ICON_ALLCHANS))
		if Prefs['tvheadend_tagchans'] != False:
			oc.add(DirectoryObject(key=Callback(getChannelsByTag, title=L('tagchans')), title=L('tagchans'), thumb=ICON_BOUQUETS))
		oc.add(DirectoryObject(key=Callback(getRecordings, title=L('recordings')), title=L('recordings'), thumb=ICON_BOUQUETS))
		oc.add(PrefsObject(title=L('preferences')))
	else:
		if debug == True: Log("Configuration error! Displaying error message: " + result['message'])
		oc.title1 = None
		oc.header = L('header_attention')
                oc.message = result['message']
		oc.add(PrefsObject(title=L('preferences')))

	return oc

####################################################################################################

def checkConfig():
	global req_api_version
	result = {
		'status':False,
		'message':''
	}

	if Prefs['tvheadend_user'] != "" and Prefs['tvheadend_pass'] != "" and Prefs['tvheadend_host'] != "" and Prefs['tvheadend_web_port'] != "":
		# To validate the tvheadend connection and api version.
		json_data = getTVHeadendJson('getServerVersion', '')
		if json_data != False:
			if json_data['api_version'] == req_api_version:
				result['status'] = True
				result['message'] = ''
				return result
			else:
				result['status'] = False
				result['message'] = L('error_api_version')
				return result
		else:
			result['status'] = False
			result['message'] = L('error_unknown')
			return result
	else:
		result['status'] = False
		result['message'] = L('error_connection')
		return result

def getTVHeadendJson(apirequest, arg1):
	if debug == True: Log("JSON-Request: " + apirequest)
	api = dict(
		getChannelGrid='api/channel/grid?start=0&limit=999999',
		getEpgGrid='api/epg/events/grid?start=0&limit=1000',
		getIdNode='api/idnode/load?uuid=' + arg1,
		getServiceGrid='api/mpegts/service/grid?start=0&limit=999999',
		getMuxGrid='api/mpegts/mux/grid?start=0&limit=999999',
		getChannelTags='api/channeltag/grid?start=0&limit=999999',
		getServerVersion='api/serverinfo',
		getRecordings='api/dvr/entry/grid_finished'
	)

	try:
                base64string = base64.encodestring('%s:%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'])).replace('\n', '')
                request = urllib2.Request("http://%s:%s/%s" % (Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], api[apirequest]))
                request.add_header("Authorization", "Basic %s" % base64string)
                response = urllib2.urlopen(request)

                json_tmp = response.read().decode('utf-8')
                json_data = json.loads(json_tmp)
	except Exception, e:
		if debug == True: Log("JSON-Request failed: " + str(e))
		return False
	if debug == True: Log("JSON-Request successfull!")
	return json_data

####################################################################################################

def getEPG():
	json_data = getTVHeadendJson('getEpgGrid','')
	if json_data != False:
		if debug_epg == True: Log("Got EPG: " + json.dumps(json_data))
	else:
		if debug_epg == True: Log("Failed to fetch EPG!")	
	return json_data

def getChannelInfo(uuid, services, json_epg):
	result = {
		'iconurl':'',
		'epg_title':'',
		'epg_description':'',
		'epg_duration':0,
		'epg_start':0,
		'epg_stop':0,
		'epg_summary':'',
	}

	json_data = getTVHeadendJson('getIdNode', uuid)
	if json_data['entries'][0]['params'][2].get('value'):
		result['iconurl'] = json_data['entries'][0]['params'][2].get('value')

	# Check if we have data within the json_epg object.
	if json_epg != False and json_epg.get('entries'):
		for epg in json_epg['entries']:
			if epg['channelUuid'] == uuid and time.time() > int(epg['start']) and time.time() < int(epg['stop']):
				if Prefs['tvheadend_channelicons'] == True and epg.get('channelIcon') and epg['channelIcon'].startswith('imagecache'):
					result['iconurl'] = 'http://%s:%s/%s' % (Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], epg['channelIcon'])
				if epg.get('title'):
					 result['epg_title'] = epg['title'];
				if epg.get('description'):
					 result['epg_description'] = epg['description'];
				if epg.get('start'):
					result['epg_start'] = time.strftime("%H:%M", time.localtime(int(epg['start'])));
				if epg.get('stop'):
					result['epg_stop'] = time.strftime("%H:%M", time.localtime(int(epg['stop'])));
				if epg.get('start') and epg.get('stop'):
					result['epg_duration'] = (epg.get('stop')-epg.get('start'))*1000;
	return result

def getRecordingsInfo(uuid):
	result = {
		'iconurl':'',
		'rec_title':'',
		'rec_description':'',
		'rec_duration':0,
		'rec_start':0,
		'rec_stop':0,
		'rec_summary':'',
	}

	json_data = getTVHeadendJson('getIdNode', uuid)
	if json_data['entries'][0]['params'][8].get('value'):
		result['iconurl'] = json_data['entries'][0]['params'][8].get('value')
	if json_data['entries'][0]['params'][11].get('value'):
		result['rec_title'] = json_data['entries'][0]['params'][11].get('value')
	if json_data['entries'][0]['params'][12].get('value'):
		result['rec_description'] = json_data['entries'][0]['params'][12].get('value')		
	if json_data['entries'][0]['params'][6].get('value'):
		result['rec_duration'] = json_data['entries'][0]['params'][6].get('value')	
	return result
	####################################################################################################

def getChannelsByTag(title):
	json_data = getTVHeadendJson('getChannelTags', '')
	tagList = ObjectContainer(no_cache=True)

	if json_data != False:
		tagList.title1 = L('tagchans')
		tagList.header = None
		tagList.message = None
		for tag in sorted(json_data['entries'], key=lambda t: t['name']):
			if debug == True: Log("Getting channellist for tag: " + tag['name'])
			tagList.add(DirectoryObject(key=Callback(getChannels, title=tag['name'], tag=tag['uuid']), title=tag['name']))
	else:
		if debug == True: Log("Could not create tagelist! Showing error.")
		tagList.title1 = None
		tagList.header = L('error')
		tagList.message = L('error_request_failed') 

	if debug == True: Log("Count of configured tags within TV-Headend: " + str(len(tagList)))
	if ( len(tagList) == 0 ):
		tagList.header = L('attention')
		tagList.message = L('error_no_tags')
	return tagList 

def getChannels(title, tag=int(0)):
	json_data = getTVHeadendJson('getChannelGrid', '')
	json_epg = getEPG()
	channelList = ObjectContainer(no_cache=True)

	if json_data != False:
		channelList.title1 = title
		channelList.header = None
		channelList.message = None
		for channel in sorted(json_data['entries'], key=lambda t: t['number']):
			if tag > 0:
				tags = channel['tags']
				for tids in tags:
					if (tag == tids):
						if debug == True: Log("Got channel with tag: " + channel['name'])
						chaninfo = getChannelInfo(channel['uuid'], channel['services'], json_epg)
						channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
			else:
				chaninfo = getChannelInfo(channel['uuid'], channel['services'], json_epg)
				channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
	else:
		if debug == True: Log("Could not create channellist! Showing error.")
		channelList.title1 = None;
		channelList.header = L('error')
		channelList.message = L('error_request_failed')
       	return channelList

def getRecordings(title):
	json_data = getTVHeadendJson('getRecordings', '')
	recordingsList = ObjectContainer(no_cache=True)

	if json_data != False:
		recordingsList.title1 = L('recordings')
		recordingsList.header = None
		recordingsList.message = None
		for recording in sorted(json_data['entries'], key=lambda t: t['title']):
			if debug == True: Log("Got recordings with title: " + recording['title'])
			recordinginfo = getRecordingsInfo(recordings['uuid'])
			recordingsList.add(createRecordingObject(recording, recordinginfo, Client.Product, Client.Platform))
	else:
		if debug == True: Log("Could not create recordings list! Showing error.")
		recordingsList.title1 = None
		recordingsList.header = L('error')
		recordingsList.message = L('error_request_failed') 

	if debug == True: Log("Count of recordings within TV-Headend: " + str(len(recordingsList)))
	if ( len(recordingsList) == 0 ):
		recordingsList.header = L('attention')
		recordingsList.message = L('error_no_recordings')
	return recordingsList 

####################################################################################################

def PlayVideo(url):
	return Redirect(url)

def addMediaObject(vco, vurl):
	media = MediaObject(
			optimized_for_streaming = True,
			#parts = [PartObject(key = vurl)],
			parts = [PartObject(key = Callback(PlayVideo, url=vurl))],
			video_codec = VideoCodec.H264,
			audio_codec = AudioCodec.AAC,
		)
	vco.add(media)
	if debug == True: Log("Creating MediaObject for streaming with URL: " + vurl)
	return vco

def createTVChannelObject(channel, chaninfo, cproduct, cplatform, container = False):
	if debug == True: Log("Creating TVChannelObject. Container: " + str(container))
	name = channel['name'] 
	icon = ""
	if chaninfo['iconurl'] != "":
		icon = chaninfo['iconurl']
	id = channel['uuid'] 
	summary = ''
	duration = 0

	# Add epg data. Otherwise leave the fields blank by default.
	if debug == True: Log("Info for mediaobject: " + str(chaninfo))
	if chaninfo['epg_title'] != "" and chaninfo['epg_start'] != 0 and chaninfo['epg_stop'] != 0 and chaninfo['epg_duration'] != 0:
		if container == False:
			name = name + " (" + chaninfo['epg_title'] + ") - (" + chaninfo['epg_start'] + " - " + chaninfo['epg_stop'] + ")"
			summary = ""
		if container == True:
			summary = chaninfo['epg_title'] + "\n" + chaninfo['epg_start'] + " - " + chaninfo['epg_stop'] + "\n\n" + chaninfo['epg_description'] 
		duration = chaninfo['epg_duration']
		#summary = '%s (%s-%s)\n\n%s' % (chaninfo['epg_title'],chaninfo['epg_start'],chaninfo['epg_stop'], chaninfo['epg_description'])

	# Build streaming url.
	url_structure = 'stream/channel'
	url_base = 'http://%s:%s@%s:%s/%s/' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], url_structure)

	# Create raw VideoClipObject.
	vco = VideoClipObject(
		key = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, cproduct = cproduct, cplatform = cplatform, container = True),
		rating_key = id,
		title = name,
		summary = summary,
		duration = duration,
		thumb = icon,
	)

	stream_defined = False
	# Decide if we have to stream for native streaming devices or if we have to transcode the content.
	if (Prefs['tvheadend_mpegts_passthrough'] == True) or (stream_defined == False and (cproduct == "Plex Home Theater" or cproduct == "PlexConnect")):
		vco = addMediaObject(vco, url_base + id + '?profile=pass')
		stream_defined = True

	# Custom streaming profile for iOS.
	if stream_defined == False and (Prefs['tvheadend_custprof_ios'] != None and cplatform == "iOS"):
		vco = addMediaObject(vco, url_base + id + '?profile=' + Prefs['tvheadend_custprof_ios'])
		stream_defined = True

        # Custom streaming profile for Android.
	if stream_defined == False and (Prefs['tvheadend_custprof_android'] != None and cplatform == "Android"):
		vco = addMediaObject(vco, url_base + id + '?profile=' + Prefs['tvheadend_custprof_android'])
		stream_defined = True

        # Custom default streaming.
	if stream_defined == False and (Prefs['tvheadend_custprof_default']):
		vco = addMediaObject(vco, url_base + id + '?profile=' + Prefs['tvheadend_custprof_default'])
		stream_defined = True

	# Default streaming.
	if stream_defined == False:
		vco = addMediaObject(vco, url_base + id)
		stream_defined = True

	# Log the product and platform which requested a stream.
	if cproduct != None and cplatform != None:
		if debug == True: Log("Created VideoObject for plex product: " + cproduct + " on " + cplatform)
	else:
		if debug == True: Log("Created VideoObject for plex product: UNDEFINED")

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco
	return vco

def createRecordingObject(recording, recordinginfo, cproduct, cplatform, container = False):
	if debug == True: Log("Creating RecordingObject. Container: " + str(container))
	name = recording['title'] 
	icon = ""
	if recordinginfo['iconurl'] != "":
		icon = recordinginfo['iconurl']
	id = recording['uuid'] 
	summary = ''
	duration = 0

	# Add epg data. Otherwise leave the fields blank by default.
	if debug == True: Log("Info for mediaobject: " + str(recordinginfo))
	if recordinginfo['rec_title'] != "" and recordinginfo['rec_start'] != 0 and recordinginfo['rec_stop'] != 0 and recordinginfo['rec_duration'] != 0:
		if container == False:
			name = name + " (" + recordinginfo['rec_title'] + ") - (" + recordinginfo['rec_start'] + " - " + recordinginfo['rec_stop'] + ")"
			summary = ""
		if container == True:
			summary = recordinginfo['rec_title'] + "\n" + recordinginfo['rec_start'] + " - " + recordinginfo['rec_stop'] + "\n\n" + recordinginfo['rec_description'] 
		duration = recordinginfo['rec_duration']
		#summary = '%s (%s-%s)\n\n%s' % (chaninfo['epg_title'],chaninfo['epg_start'],chaninfo['epg_stop'], chaninfo['epg_description'])

	# Build streaming url.
	url_structure = 'stream/channel'
	url_base = 'http://%s:%s@%s:%s/%s/' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], url_structure)

	# Create raw VideoClipObject.
	vco = VideoClipObject(
		key = Callback(createRecordingObject, recording = recording, recordinginfo = recordinginfo, cproduct = cproduct, cplatform = cplatform, container = True),
		rating_key = id,
		title = name,
		summary = summary,
		duration = duration,
		thumb = icon,
	)

	stream_defined = False
	# Decide if we have to stream for native streaming devices or if we have to transcode the content.
	if (Prefs['tvheadend_mpegts_passthrough'] == True) or (stream_defined == False and (cproduct == "Plex Home Theater" or cproduct == "PlexConnect")):
		vco = addMediaObject(vco, url_base + id + '?profile=pass')
		stream_defined = True

	# Custom streaming profile for iOS.
	if stream_defined == False and (Prefs['tvheadend_custprof_ios'] != None and cplatform == "iOS"):
		vco = addMediaObject(vco, url_base + id + '?profile=' + Prefs['tvheadend_custprof_ios'])
		stream_defined = True

        # Custom streaming profile for Android.
	if stream_defined == False and (Prefs['tvheadend_custprof_android'] != None and cplatform == "Android"):
		vco = addMediaObject(vco, url_base + id + '?profile=' + Prefs['tvheadend_custprof_android'])
		stream_defined = True

        # Custom default streaming.
	if stream_defined == False and (Prefs['tvheadend_custprof_default']):
		vco = addMediaObject(vco, url_base + id + '?profile=' + Prefs['tvheadend_custprof_default'])
		stream_defined = True

	# Default streaming.
	if stream_defined == False:
		vco = addMediaObject(vco, url_base + id)
		stream_defined = True

	# Log the product and platform which requested a stream.
	if cproduct != None and cplatform != None:
		if debug == True: Log("Created VideoObject for plex product: " + cproduct + " on " + cplatform)
	else:
		if debug == True: Log("Created VideoObject for plex product: UNDEFINED")

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco
	return vco