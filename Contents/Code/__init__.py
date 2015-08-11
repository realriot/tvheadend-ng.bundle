import base64, simplejson, time, datetime
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
		if Prefs['tvheadend_recordings'] != False:
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

def ValidatePrefs():
	return True

def checkConfig():
	global req_api_version
	result = {
		'status':False,
		'message':''
	}

	if Prefs['tvheadend_user'] != "" and Prefs['tvheadend_pass'] != "" and Prefs['tvheadend_host'] != "" and Prefs['tvheadend_web_port'] != "" and Prefs['tvheadend_user'] != None and Prefs['tvheadend_pass'] != None and Prefs['tvheadend_host'] != None and Prefs['tvheadend_web_port'] != None:
		# To validate the tvheadend connection and api version.
		json_data = getTVHeadendJson('getServerVersion', '')
		if json_data != False:
			# if debug == True: Log("Server running API version: " + json_data['api_version'])
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
			result['message'] = L('error_connection')
			return result
	else:
		if Prefs['tvheadend_user'] == "" or Prefs['tvheadend_pass'] == "" or Prefs['tvheadend_user'] == None or Prefs['tvheadend_pass'] == None:
			result['status'] = False
			result['message'] = L('error_no_anonymous')
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
		url = 'http://%s:%s%s%s' % (Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], Prefs['tvheadend_web_rootpath'], api[apirequest])
		authstring = base64.encodestring('%s:%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'])).replace('\n', '')
		headers = dict()
		headers['Authorization'] = "Basic %s" % (authstring)
		json_data = JSON.ObjectFromURL(url=url, headers=headers, values=None)
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

def getServices():
	json_data = getTVHeadendJson('getServiceGrid','')
	if json_data == False:
		if debug == True: Log("Failed to fetch DVB services!")
	return json_data

def getChannelInfo(uuid, services, json_epg, json_services):
	result = {
		'service_encrypted':None,
		'service_type':'',
		'epg_title':'',
		'epg_description':'',
		'epg_duration':0,
		'epg_start':0,
		'epg_stop':0,
		'epg_summary':'',
	}

	# Get dvb informations.
	for service in json_services['entries']:
		if service['uuid'] == services[0]:
			result['service_type'] = str(service['dvb_servicetype'])
			result['service_encrypted'] = service['encrypted']

	# Check if we have data within the json_epg object.
	if json_epg != False and json_epg.get('entries'):
		for epg in json_epg['entries']:
			if epg['channelUuid'] == uuid and time.time() > int(epg['start']) and time.time() < int(epg['stop']):
				if epg.get('title'):
					 result['epg_title'] = epg['title']
				if epg.get('description'):
					 result['epg_description'] = epg['description']
				if epg.get('start'):
					result['epg_start'] = time.strftime("%H:%M", time.localtime(int(epg['start'])));
				if epg.get('stop'):
					result['epg_stop'] = time.strftime("%H:%M", time.localtime(int(epg['stop'])));
				if epg.get('start') and epg.get('stop'):
					result['epg_duration'] = (epg.get('stop')-epg.get('start'))*1000;
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
			if tag['internal'] == False:
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
	json_services = getServices()
	channelList = ObjectContainer(no_cache=True)

	if json_data != False and json_epg != False and json_services != False:
		channelList.title1 = title
		channelList.header = None
		channelList.message = None
		for channel in sorted(json_data['entries'], key=lambda t: t['number']):
			if tag > 0:
				tags = channel['tags']
				for tids in tags:
					if (tag == tids):
						if debug == True: Log("Got channel with tag: " + channel['name'])
						chaninfo = getChannelInfo(channel['uuid'], channel['services'], json_epg, json_services)
						channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
			else:
				chaninfo = getChannelInfo(channel['uuid'], channel['services'], json_epg, json_services)
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
			if debug == True: Log("Got recording with title: " + str(recording['title']))
			recordingsList.add(createRecordingObject(recording, Client.Product, Client.Platform))
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

def PlayMedia(url):
	return Redirect(url)

def createMediaContainer(mctype, args):
	mco = None
	if debug == True: Log("Building VideoClip object")
	if mctype == 'videoclip':
		mco = VideoClipObject(
			key = args['key'],
			rating_key = args['rating_key'],
			title = args['title'],
			summary = args['summary'],
			duration = args['duration'],
			thumb = args['thumb'],
		)
	if debug == True: Log("Building AudioTrack object")
	if mctype == 'audiotrack':
		mco = TrackObject(
			key = args['key'],
			rating_key = args['rating_key'],
			title = args['title'],
			summary = args['summary'],
			duration = args['duration'],
			thumb = args['thumb'],
			artist = args['artist'],
			album = args['album'],
		)

	stream_defined = False
	# Decide if we have to stream for native streaming devices or if we have to transcode the content.
	if (Prefs['tvheadend_mpegts_passthrough'] == True) or (stream_defined == False and (cproduct == "Plex Home Theater" or cproduct == "PlexConnect")):
		mco = addMediaObject(mco, args['url'] + '?profile=pass')
		stream_defined = True

	# Custom streaming profile for iOS.
	if stream_defined == False and (Prefs['tvheadend_custprof_ios'] != None and cplatform == "iOS"):
		mco = addMediaObject(mco, args['url'] + '?profile=' + Prefs['tvheadend_custprof_ios'])
		stream_defined = True

	# Custom streaming profile for Android.
	if stream_defined == False and (Prefs['tvheadend_custprof_android'] != None and cplatform == "Android"):
		mco = addMediaObject(mco, args['url'] + '?profile=' + Prefs['tvheadend_custprof_android'])
		stream_defined = True

	# Custom default streaming.
	if stream_defined == False and (Prefs['tvheadend_custprof_default']):
		mco = addMediaObject(mco, args['url'] + '?profile=' + Prefs['tvheadend_custprof_default'])
		stream_defined = True

	# Default streaming.
	if stream_defined == False:
		mco = addMediaObject(mco, args['url'])
		stream_defined = True

	# Log the product and platform which requested a stream.
	if args['cproduct'] != None and args['cplatform'] != None:
		if debug == True: Log("Created MediaObject for plex product: " + args['cproduct'] + " on " + args['cplatform'])
	else:
		if debug == True: Log("Created MediaObject for plex product: UNDEFINED")

	return mco

def addMediaObject(mco, vurl):
	media = MediaObject(
			optimized_for_streaming = True,
			#parts = [PartObject(key = vurl)],
			parts = [PartObject(key = Callback(PlayMedia, url=vurl))],
			#video_codec = VideoCodec.H264,
			#audio_codec = AudioCodec.AAC,
		)
	mco.add(media)
	if debug == True: Log("Creating MediaObject for streaming with URL: " + vurl)
	return mco

def createTVChannelObject(channel, chaninfo, cproduct, cplatform, container = False):
	if debug == True: Log("Creating TVChannelObject. Container: " + str(container))
	name = channel['name'] 
	id = channel['uuid']
	summary = None
	duration = None

	# Handle channel icon.
	icon = None 
	try:
		if Prefs['tvheadend_channelicons'] == True and channel['icon_public_url'].startswith('imagecache'):
			icon = 'http://%s:%s@%s:%s%s%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], Prefs['tvheadend_web_rootpath'], channel['icon_public_url'])
	except KeyError:
		pass

	# Add epg data. Otherwise leave the fields blank by default.
	if debug == True: Log("Info for mediaobject: " + str(chaninfo))
	if chaninfo['epg_title'] != "" and chaninfo['epg_start'] != 0 and chaninfo['epg_stop'] != 0 and chaninfo['epg_duration'] != 0:
		if container == False:
			name = name + " (" + chaninfo['epg_title'] + ") - (" + chaninfo['epg_start'] + " - " + chaninfo['epg_stop'] + ")"
			summary = chaninfo['epg_title'] + "\n\n" + chaninfo['epg_description'] 
		if container == True:
			summary = chaninfo['epg_title'] + "\n\n" + chaninfo['epg_description'] + "\n\n" + chaninfo['epg_start'] + " - " + chaninfo['epg_stop']
		duration = chaninfo['epg_duration']

	# Build streaming url.
	url_structure = 'stream/channel'
	url = 'http://%s:%s@%s:%s%s%s/%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], Prefs['tvheadend_web_rootpath'], url_structure, id)

	# Create and return MediaContainer.
	mco = None
	args = dict()
	args['cproduct'] = cproduct
	args['cplatform'] = cplatform
	args['url'] = url
	if chaninfo['service_type'] != '2':
		if debug == True: Log("Creating media object with type: VIDEO")
		args['key'] = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, cproduct = cproduct, cplatform = cplatform, container = True)
		args['rating_key'] = id
		args['title'] = name
		args['summary'] = summary
		args['duration'] = duration
		args['thumb'] = icon
		mco = createMediaContainer('videoclip', args)
	else:
		if debug == True: Log("Creating media object with type: AUDIO")
		args['key'] = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, cproduct = cproduct, cplatform = cplatform, container = True)
		args['rating_key'] = id
		args['title'] = name
		args['summary'] = summary
		args['duration'] = duration
		args['thumb'] = icon
		args['artist'] = ' '
		args['album'] = chaninfo['epg_title']
		mco = createMediaContainer('audiotrack', args)

	if container:
		return ObjectContainer(objects = [mco])
	else:
		return mco
	return mco

def createRecordingObject(recording, cproduct, cplatform, container = False):
	if debug == True: Log("Creating RecordingObject. Container: " + str(container))
	name = recording['disp_title']
	id = recording['uuid'] 
	summary = None
	duration = None 

	# Handle recording icon.
	icon = None
	if Prefs['tvheadend_channelicons'] == True and recording['channel_icon'].startswith('imagecache'):
		icon = 'http://%s:%s@%s:%s%s%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], Prefs['tvheadend_web_rootpath'], recording['channel_icon'])

	# Add recording informations. Otherwise leave the fields blank by default.
	if debug == True: Log("Info for mediaobject: " + str(recording))
	if recording['disp_title'] != "" and recording['start'] != 0 and recording['stop'] != 0:
		start = datetime.datetime.fromtimestamp(recording['start']).strftime('%d-%m-%Y %H:%M')
		stop = datetime.datetime.fromtimestamp(recording['stop']).strftime('%d-%m-%Y %H:%M')
		duration = (recording['stop']-recording['start'])*1000
		if container == False:
			name = name + " (" + start + ")"
			summary = recording['disp_subtitle']
		if container == True:
			summary = recording['disp_subtitle'] + "\n\n" + recording['disp_description'] + "\n\n" + start

	# Build streaming url.
	url_structure = 'dvrfile'
	url = 'http://%s:%s@%s:%s%s%s/%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], Prefs['tvheadend_web_rootpath'], url_structure, id)

	# Create and return MediaContainer.
	mco = None
	args = dict()
	args['cproduct'] = cproduct
	args['cplatform'] = cplatform
	args['url'] = url

	if debug == True: Log("Creating media object with type: VIDEO")
	args['key'] = Callback(createRecordingObject, recording = recording, cproduct = cproduct, cplatform = cplatform, container = True)
	args['rating_key'] = id
	args['title'] = name
	args['summary'] = summary
	args['duration'] = duration
	args['thumb'] = icon
	mco = createMediaContainer('videoclip', args)

	if container:
		return ObjectContainer(objects = [mco])
	else:
		return mco
	return mco
