"""
pyq.py

pyq (pronounced "pie Q") is a python client for accessing the Gracenote
eyeQ API, which can retrieve TV providers, channels, and programs.

You will need a Gracenote client ID to use this module. See
developer.gracenote.com for more info.
"""

import xml.etree.ElementTree, urllib2, urllib, simplejson, HTMLParser
json = simplejson

htmlparser = HTMLParser.HTMLParser()

# Set DEBUG to True if you want this module to print out the query and response XML
DEBUG = False 

class gn_provider(dict):
  """
  this class is a dict containing metadata for a GN provider
  """
  def __init__(self):
    self['id'] = ''
    self['name'] = ''
    self['place'] = ''
    self['type']= ''

class gn_channel(dict):
  """
  this class is a dict containing metadata for a GN tv channel
  """
  def __init__(self):
    self['id'] = ''
    self['name'] = ''
    self['name_short'] = ''
    self['num'] = ''
    self['rank'] = 0
    self['logo_url'] = ''

class gn_program(dict):
  """
  this class is a dict containing metadata for a GN tv program
  """
  def __init__(self):
    for k in ['id','title','title_sub','listing','episode_num',
              'season_num','epgproduction_type','rank','groupref',
              'image_url','ipgcategory_image_url']:
      self[k] = ''

    self['ipgcategories'] = []

def register(clientID):
  """
  This function registers an application as a user of the Gracenote service
  
  It takes as a parameter a clientID string in the form of 
  "NNNNNNN-NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN" and returns a userID in a 
  similar format.
  
  As the quota of number of users (installed applications or devices) is 
  typically much lower than the number of queries, best practices are for a
  given installed application to call this only once, store the UserID in 
  persistent storage (e.g. filesystem), and then use these IDs for all 
  subsequent calls to the service.
  """
  
  # Create XML request
  query = gnquery()
  query.addQuery('REGISTER')
  query.addQueryClient(clientID)
  
  queryXML = query.toString()
  
  # POST query
  response = urllib2.urlopen(gnurl(clientID), queryXML)
  responseXML = response.read()
  
  # Parse response
  responseTree = xml.etree.ElementTree.fromstring(responseXML)
  
  responseElem = responseTree.find('RESPONSE')
  if responseElem.attrib['STATUS'] == 'OK':
    userElem = responseElem.find('USER')
    userID = userElem.text
  
  return userID
  
class gnquery:
  """
  A utility class for creating and configuring an XML query for POST'ing to
  the Gracenote service
  """

  def __init__(self):
    self.root = xml.etree.ElementTree.Element('QUERIES')
    
  def addAuth(self, clientID, userID):
    auth = xml.etree.ElementTree.SubElement(self.root, 'AUTH')
    client = xml.etree.ElementTree.SubElement(auth, 'CLIENT')
    user = xml.etree.ElementTree.SubElement(auth, 'USER')
  
    client.text = clientID
    user.text = userID

  def addLang(self,lang='eng'):
    xlang = xml.etree.ElementTree.SubElement(self.root,'LANG')
    xlang.text = lang

  def addCountry(self,country='usa'):
    xcountry = xml.etree.ElementTree.SubElement(self.root,'COUNTRY')
    xcountry.text = country
  
  def addQuery(self, cmd):
    query = xml.etree.ElementTree.SubElement(self.root, 'QUERY')
    query.attrib['CMD'] = cmd

  def addQueryMode(self, modeStr):
    query = self.root.find('QUERY')
    mode = xml.etree.ElementTree.SubElement(query, 'MODE')
    mode.text = modeStr

  def addQueryTextField(self, fieldName, value):
    query = self.root.find('QUERY')
    text = xml.etree.ElementTree.SubElement(query, 'TEXT')
    text.attrib['TYPE'] = fieldName
    text.text = value

  def addQueryOption(self, parameterName, value):
    query = self.root.find('QUERY')
    option = xml.etree.ElementTree.SubElement(query, 'OPTION')
    parameter = xml.etree.ElementTree.SubElement(option, 'PARAMETER')
    parameter.text = parameterName
    valueElem = xml.etree.ElementTree.SubElement(option, 'VALUE')
    valueElem.text = value

  def addQueryGNID(self, GNID):
    query = self.root.find('QUERY')
    GNIDElem = xml.etree.ElementTree.SubElement(query, 'GN_ID')
    GNIDElem.text = GNID

  def addQueryClient(self, clientID):
    query = self.root.find('QUERY')
    client = xml.etree.ElementTree.SubElement(query, 'CLIENT')
    client.text = clientID

  def addQueryTVChannels(self, channelIDs):
    if type(channelIDs) is not list: channelIDs = [channelIDs]
    query = self.root.find('QUERY')
    tvchannel = xml.etree.ElementTree.SubElement(query, 'TVCHANNEL')
    for channelID in channelIDs:
      gn_id = xml.etree.ElementTree.SubElement(tvchannel, 'GN_ID')
      gn_id.text = channelID

  def addQueryDVBIDS(self, dvbriplets):
    query = self.root.find('QUERY')

    for trip in dvbriplets:
      node = xml.etree.ElementTree.SubElement(query, "DVBIDS") 
      xml_onid = xml.etree.ElementTree.SubElement(node, 'ONID')
      xml_onid.text = trip['onid'] 
      xml_tsid = xml.etree.ElementTree.SubElement(node, 'TSID')
      xml_tsid.text = trip['tsid']
      xml_sid = xml.etree.ElementTree.SubElement(node, 'SID')
      xml_sid.text = trip['sid']

  def addQueryCustomNode(self, nodeName, nodeText, attribName=None, attribValue=None):
    query = self.root.find('QUERY')
    node = xml.etree.ElementTree.SubElement(query, nodeName)
    node.text = nodeText
    if attribName and attribValue:
      node.attrib[attribName] = attribValue

  def toString(self):
    return xml.etree.ElementTree.tostring(self.root)

def gnurl(clientID):
  """
  Helper function to form URL to Gracenote service
  """
  clientIDprefix = clientID.split('-')[0]
  return 'http://c' + clientIDprefix + '.ipg.web.cddbp.net/webapi/xml/1.0/'

def prn_xml(xml_str,is_query=True):
  """
  prints out xml string for debugging
  """
  print '------------'
  if is_query:
    print 'QUERY XML'
  else:
    print 'RESPONSE XML'
  print '------------'
  print xml_str
  
def lookupProviders(clientID, userID, zipcode):
  """
  Queries the Gracenote service for a list of TV providers for the given zip
  code
  """

  if not isinstance(zipcode,str):
    zipcode = str(zipcode)
  
  # Create XML request
  query = gnquery()
  query.addAuth(clientID, userID)
  query.addLang()
  query.addCountry()
  query.addQuery('TVPROVIDER_LOOKUP')
  
  gnquery.addQueryCustomNode(query, 'POSTALCODE', zipcode)
  
  queryXML = query.toString()

  if DEBUG:
    prn_xml(queryXML,is_query=True)
  
  # POST query
  response = urllib2.urlopen(gnurl(clientID), queryXML)
  responseXML = response.read()
  
  if DEBUG:
    prn_xml(responseXML,is_query=False)

  # Create array of all TV providers
  providers = []

  # Parse response XML
  response_tree = xml.etree.ElementTree.fromstring(responseXML)
  responseElem = response_tree.find('RESPONSE')
  
  if responseElem.attrib['STATUS'] == 'OK':
    for tvproviderElem in responseElem.iter('TVPROVIDER'):
      
      # Create gn_provider object
      provider = gn_provider()

      # Parse TV Provider fields
      provider['id'] =  getElemText(tvproviderElem, "GN_ID")
      provider['name'] = getElemText(tvproviderElem, "NAME")
      provider['place'] = getElemText(tvproviderElem, "PLACE")
      provider['type'] = getElemText(tvproviderElem, "PROVIDERTYPE")
      providers.append(provider)
  
  return providers

def lookupChannels(clientID, userID, queryMode, argument):
  """ 
  Queries the Gracenote service for the list of channels offered by
  that provider
  """
  # Create XML request
  query = gnquery()
  query.addAuth(clientID, userID)
  query.addLang()
  query.addCountry()
  query.addQuery('TVCHANNEL_LOOKUP')
  
  gnquery.addQueryMode(query, queryMode)

  # Choose between query modes
  if queryMode == "DVBIDS": 
    gnquery.addQueryDVBIDS(query, argument)
  else:
    # Default goes to mode "TVPROVIDER"
    gnquery.addQueryCustomNode(query, 'GN_ID', argument)

  gnquery.addQueryOption(query, 'SELECT_EXTENDED', 'IMAGE') # Get channel logos
  queryXML = query.toString()

  if DEBUG:
    prn_xml(queryXML,is_query=True)
  
  # POST query
  response = urllib2.urlopen(gnurl(clientID), queryXML)
  responseXML = response.read()
  
  if DEBUG:
    prn_xml(responseXML,is_query=False)

  # Create array of all channels
  channels = []

  # Parse response XML
  response_tree = xml.etree.ElementTree.fromstring(responseXML)
  responseElem = response_tree.find('RESPONSE')
  
  if responseElem.attrib['STATUS'] == 'OK':
    for tvchannelElem in responseElem.iter('TVCHANNEL'):
      
      # Create gn_channel object
      channel = gn_channel()

      # Parse TV Channel fields
      channel['id'] =  getElemText(tvchannelElem, "GN_ID")
      channel['name'] = getElemText(tvchannelElem, "NAME")
      channel['name_short'] = getElemText(tvchannelElem, "NAME_SHORT")
      channel['num'] = getElemText(tvchannelElem, "CHANNEL_NUM")
      channel['rank'] = getElemText(tvchannelElem, "RANK")
      channel['logo_url'] = htmlparser.unescape(getElemText(tvchannelElem, 'URL', 'TYPE', 'IMAGE'))
      channels.append(channel)
  
  return channels

def lookupProgramsByChannels(clientID, userID, channelIDs, startDateTime=None, endDateTime=None):
  """ 
  Queries the Gracenote service for the list of programs airing on
  a set of channels, during a specified time window
  """

  # We expect channelIDs to be a list of strings. 
  # If channelIDs is a single string, create a list of one string
  if type(channelIDs) is not list: channelIDs = [channelIDs]

  # Create XML request
  query = gnquery()
  query.addAuth(clientID, userID)
  query.addLang()
  query.addCountry()
  query.addQuery('TVGRID_LOOKUP')
  
  gnquery.addQueryTVChannels(query, channelIDs)
  if startDateTime and endDateTime:
    gnquery.addQueryCustomNode(query, 'DATE', startDateTime, 'TYPE', 'START')
    gnquery.addQueryCustomNode(query, 'DATE', endDateTime, 'TYPE', 'END')
  gnquery.addQueryOption(query, 'SELECT_EXTENDED', 'TVPROGRAM_IMAGE,IPGCATEGORY_IMAGE') # Get channel logos
  
  queryXML = query.toString()

  if DEBUG:
    prn_xml(queryXML,is_query=True)
  
  # POST query
  response = urllib2.urlopen(gnurl(clientID), queryXML)
  responseXML = response.read()
  
  if DEBUG:
    prn_xml(responseXML,is_query=False)

  # Create array of all programs
  programs = []

  # Parse response XML
  response_tree = xml.etree.ElementTree.fromstring(responseXML)
  responseElem = response_tree.find('RESPONSE')
  
  if responseElem.attrib['STATUS'] == 'OK':
    for tvprogramElem in responseElem.iter('TVPROGRAM'):
      
      # Create gn_program object
      program = gn_program()

      # Parse TV Program fields
      program['id'] =  getElemText(tvprogramElem, "GN_ID")
      program['title'] = getElemText(tvprogramElem, "TITLE")
      program['title_sub'] = getElemText(tvprogramElem, "TITLE_SUB")
      program['listing'] = getElemText(tvprogramElem, "LISTING")
      program['episode_num'] = getElemText(tvprogramElem, "EPISODE_NUM")
      program['season_num'] = getElemText(tvprogramElem, "SEASON_NUM")
      program['epgproduction_type'] = getElemText(tvprogramElem, "EPGPRODUCTION_TYPE")
      program['rank'] = getElemText(tvprogramElem, "RANK")
      program['groupref'] = getElemText(tvprogramElem, "GROUPREF")
      program['image_url'] = htmlparser.unescape(getElemText(tvprogramElem, 'URL', 'TYPE', 'IMAGE'))
      program['ipgcategory_image_url'] = htmlparser.unescape(getElemText(tvprogramElem, 'URL', 'TYPE', 'IPGCATEGORY_IMAGE'))
      for ipgcategoryElem in tvprogramElem.iter('IPGCATEGORY'):
        program['ipgcategories'].append({'ipgcategory_l1': getElemText(ipgcategoryElem, "IPGCATEGORY_L1"),
                                    'ipgcategory_l2': getElemText(ipgcategoryElem, "IPGCATEGORY_L2")})
      programs.append(program)
  
  return programs

def getElemText(parentElem, elemName, elemAttribName=None, elemAttribValue=None):
  """
  XML parsing helper function to find child element with a specific name, 
  and return the text value
  """
  elems = parentElem.findall(elemName)
  for elem in elems:
    if elemAttribName is not None and elemAttribValue is not None:
      if elem.attrib[elemAttribName] == elemAttribValue:
        return urllib.unquote(elem.text)
      else:
        continue
    else: # Just return the first one
      return urllib.unquote(elem.text)
  return ''

def getElemAttrib(parentElem, elemName, elemAttribName):
  """
  XML parsing helper function to find child element with a specific name, 
  and return the value of a specified attribute
  """
  elem = parentElem.find(elemName)
  if elem is not None:
    return elem.attrib[elemAttribName]

def getMultiElemText(parentElem, elemName, topKey, bottomKey):
  """
  XML parsing helper function to return a 2-level dict of multiple elements
  by a specified name, using topKey as the first key, and bottomKey as the second key
  """
  elems = parentElem.findall(elemName)
  result = {} # 2-level dictionary of items, keyed by topKey and then bottomKey
  if elems is not None:
    for elem in elems:
      if topKey in elem.attrib:
        result[elem.attrib[topKey]] = {bottomKey:elem.attrib[bottomKey], 'TEXT':elem.text}
      else:
        result['0'] = {bottomKey:elem.attrib[bottomKey], 'TEXT':elem.text}
  return result

def etree_to_dict(t):
  if t.getchildren():
    d = {t.tag : map(etree_to_dict, t.getchildren())}
  else:
    d = {t.tag : t.text}

  return d
