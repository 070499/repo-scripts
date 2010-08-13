import urllib2, simplejson, md5, unicodedata, re, os, traceback, sys, pickle, socket
from operator import itemgetter, attrgetter

class LoginTokensExceededError(Exception):
	def __init__(self):
		self.value = 'You have created to many tokens. Only 12 are allowed'
	def __str__(self):
		return repr(self.value)
		
class LoginUnknownError(Exception):
	def __init__(self):
		self.value = 'Unable to get a new session ID. Wait a few minutes and try again'
	def __str__(self):
		return repr(self.value)

class SessionIDTryAgainError(Exception):
	def __init__(self):
		self.value = 'Unable to get a new session ID. Wait a few minutes and try again'
	def __str__(self):
		return repr(self.value)

class GrooveAPI:
	def __init__(self, enableDebug = False):
		timeout = 40
		socket.setdefaulttimeout(timeout)
		self.enableDebug = enableDebug
		self.loggedIn = 0
		self.userId = 0
		self.rootDir = os.getcwd()
		self.sessionID = self.getSavedSession()
		self.debug('Saved sessionID: ' + self.sessionID)
		self.sessionID = self.getSessionFromAPI()
		self.debug('API sessionID: ' + self.sessionID)
		if self.sessionID == '':
			self.sessionID = self.startSession()
			self.debug('Start() sessionID: ' + self.sessionID)
			if self.sessionID == '':
				self.debug('Could not get a sessionID. Try again in a few minutes')
				raise SessionIDTryAgainError()
			else:
				self.saveSession()
		
		self.debug('sessionID: ' + self.sessionID)

	def __del__(self):
		if self.loggedIn == 1:
			self.logout()
			
	def debug(self, msg):
		if self.enableDebug == True:
			print msg
			
	def getSavedSession(self):
		sessionID = ''
		path = os.path.join(self.rootDir, 'data', 'session.txt')

		try:
			f = open(path, 'rb')
			sessionID = pickle.load(f)
			f.close()
		except:
			sessionID = ''
			pass		
		
		return sessionID

	def saveSession(self):			
		try:
			dir = os.path.join(self.rootDir, 'data')
			# Create the 'data' directory if it doesn't exist.
			if not os.path.exists(dir):
				os.mkdir(dir)
			path = os.path.join(dir, 'session.txt')
			f = open(path, 'wb')
			pickle.dump(self.sessionID, f, protocol=pickle.HIGHEST_PROTOCOL)
			f.close()
		except IOError, e:
			print 'There was an error while saving the session pickle (%s)' % e
			pass
		except:
			print "An unknown error occured during save session: " + str(sys.exc_info()[0])
			pass
			
	def saveSettings(self):			
		try:
			dir = os.path.join(self.rootDir, 'data')
			# Create the 'data' directory if it doesn't exist.
			if not os.path.exists(dir):
				os.mkdir(dir)
			path = os.path.join(dir, 'settings1.txt')
			f = open(path, 'wb')
			pickle.dump(self.settings, f, protocol=pickle.HIGHEST_PROTOCOL)
			f.close()
		except IOError, e:
			print 'There was an error while saving the settings pickle (%s)' % e
			pass
		except:
			print "An unknown error occured during save settings\n"
			pass

	def callRemote(self, method, params={}):
		data = {'header': {'sessionID': self.sessionID}, 'method': method, 'parameters': params}
		data = simplejson.dumps(data)
		#proxy_support = urllib2.ProxyHandler({"http" : "http://wwwproxy.kom.aau.dk:3128"})
		## build a new opener with proxy details
		#opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
		## install it
		#urllib2.install_opener(opener)
		req = urllib2.Request("http://api.grooveshark.com/ws/1.0/?json")
		req.add_header('Host', 'api.grooveshark.com')
		req.add_header('Content-type', 'text/json')
		req.add_header('Content-length', str(len(data)))
		req.add_data(data)
		response = urllib2.urlopen(req)
		result = response.read()
		result = simplejson.loads(result)
		response.close()
		#self.debug(result)
		return result

	def startSession(self):
		response = urllib2.urlopen("http://www.moovida.com/services/grooveshark/session_start")
		result = response.read()
		result = simplejson.loads(result)
		response.close()
		if 'fault' in result:
			return ''
		else:
			return result['header']['sessionID']

	def sessionDestroy(self):
		return self.callRemote("session.destroy")
			
	def getSessionFromAPI(self):
		result = self.callRemote("session.get")
		if 'fault' in result:
			return ''
		else:
			return result['header']['sessionID']												

	def getStreamURL(self, songID):
		result = self.callRemote("song.getStreamUrlEx", {"songID": songID})
		if 'result' in result:
			return result['result']['url']
		else:
			return ''
	
	def createUserAuthToken(self, username, password):
		hashpass = md5.new(password).hexdigest()
		hashpass = username + hashpass
		hashpass = md5.new(hashpass).hexdigest()
		result = self.callRemote("session.createUserAuthToken", {"username": username, "hashpass": hashpass})
		if 'result' in result:
			return result['result']['token'], result['result']['userID']
		elif 'fault' in result:
			if result['fault']['code'] == 256:
				return -1 # Exceeded the number of allowed tokens. Should not happen
			else:
				return -2 # Unknown error
		else:
			return -2 # Unknown error
	
	def destroyUserAuthToken(self, token):
		self.callRemote("session.destroyAuthToken", {"token": token})
		
	def loginViaAuthToken(self, token):
		result = self.callRemote("session.loginViaAuthToken", {"token": token})
		self.destroyUserAuthToken(token)
		if 'result' in result:
			self.userID = result['result']['userID']
			return result['result']['userID']
		else:
			return 0
	
	def login(self, username, password):
		if self.loggedIn == 1:
			return self.userId
		result = self.createUserAuthToken(username, password)
		if result == -1:
			raise LoginTokensExceededError()
		elif result == -2:
			raise LoginUnknownError()
		else:
			self.token = result[0]
			self.debug('Token:' + self.token)
			self.userId = self.loginViaAuthToken(self.token)
			if self.userId == 0:
				raise LoginUnknownError()
			else:
				self.loggedIn = 1
				return self.userId
				
	def loginBasic(self, username, password):
		if self.loggedIn == 1:
			return self.userId
		result = self.callRemote("session.login", {"username": username, "password": password})
		if 'fault' in result:
			return 0
		else:
			self.loggedIn = 1
			return result['result']['userID']

	def loggedInStatus(self):
		return self.loggedIn
	
	def logout(self):
		self.callRemote("session.logout", {})
		self.loggedIn = 0
		
	def getSongInfo(self, songID):
		return self.callRemote("song.about", {"songID": songID})['result']['song']
	
	def userGetFavoriteSongs(self, userID):
		result = self.callRemote("user.getFavoriteSongs", {"userID": userID})
		list = self.parseSongs(result)
		return list
	
	def userGetPlaylists(self, limit=25):
		if self.loggedIn == 1:
			result = self.callRemote("user.getPlaylists", {"userID": self.userId, "limit": limit})
			if 'result' in result:
				playlists = result['result']['playlists']
			else:
				return []
			i = 0
			list = []
			while(i < len(playlists)):
				p = playlists[i]
				list.append([p['playlistName'].encode('ascii', 'ignore'), p['playlistID']])
				i = i + 1	
			return sorted(list, key=itemgetter(0))
		else:
			return []

	def playlistCreate(self, name, about):
		if self.loggedIn == 1:
			result = self.callRemote("playlist.create", {"name": name, "about": about})
			if 'result' in result:
				return result['result']['playlistID']
			else:
				return 0
		else:
			return 0
			
	def playlistGetSongs(self, playlistId, limit=25):
		if self.loggedIn == 1:
			result = self.callRemote("playlist.getSongs", {"playlistID": playlistId, "limit": limit})
			list = self.parseSongs(result)
			return list
		else:
			return []
			
			
	def playlistDelete(self, playlistId):
		if self.loggedIn == 1:
			return self.callRemote("playlist.delete", {"playlistID": playlistId})

	def playlistRename(self, playlistId, name):
		if self.loggedIn == 1:
			result = self.callRemote("playlist.rename", {"playlistID": playlistId, "name": name})
			if 'fault' in result:
				return 0
			else:
				return 1
		else:
			return 0

	def playlistClearSongs(self, playlistId):
		if self.loggedIn == 1:
			return self.callRemote("playlist.clearSongs", {"playlistID": playlistId})

	def playlistAddSong(self, playlistId, songId, position):
		if self.loggedIn == 1:
			result = self.callRemote("playlist.addSong", {"playlistID": playlistId, "songID": songId, "position": position})
			if 'fault' in result:
				return 0
			else:
				return 1
		else:
			return 0
			
	def playlistReplace(self, playlistId, songIds):
		if self.loggedIn == 1:
			result = self.callRemote("playlist.replace", {"playlistID": playlistId, "songIDs": songIds})
			if 'fault' in result:
				return 0
			else:
				return 1
		else:
			return 0

	def favoriteSong(self, songID):
		return self.callRemote("song.favorite", {"songID": songID})

	def unfavoriteSong(self, songID):
		return self.callRemote("song.unfavorite", {"songID": songID})
		
	def getMethods(self):
		return self.callRemote("service.getMethods")

	def searchSongsExactMatch(self, songName, artistName, albumName):
		result = self.callRemote("search.songExactMatch", {"songName": songName, "artistName": artistName, "albumName": albumName})
		list = self.parseSongs(result)
		return list

	def searchSongs(self, query, limit, page=0, sortKey=6):
		result = self.callRemote("search.songs", {"query": query, "limit": limit, "page:": page, "streamableOnly": 1})
		list = self.parseSongs(result)
		return sorted(list, key=itemgetter(sortKey))

	def searchArtists(self, query, limit, sortKey=0):
		result = self.callRemote("search.artists", {"query": query, "limit": limit, "streamableOnly": 1})
		list = self.parseArtists(result)
		return sorted(list, key=itemgetter(sortKey))

	def searchAlbums(self, query, limit, sortKey=2):
		result = self.callRemote("search.albums", {"query": query, "limit": limit, "streamableOnly": 1})
		list = self.parseAlbums(result)
		return sorted(list, key=itemgetter(sortKey))				

	def popularGetSongs(self, limit):
		result = self.callRemote("popular.getSongs", {"limit": limit})
		list = self.parseSongs(result)
		return list
		
	def popularGetArtists(self, limit):
		result = self.callRemote("popular.getArtists", {"limit": limit})
		list = self.parseArtists(result)
		return list

	def popularGetAlbums(self, limit):
		result = self.callRemote("popular.getAlbums", {"limit": limit})
		list = self.parseAlbums(result)
		return list
		
	def artistGetAlbums(self, artistId, limit, sortKey=2):
		result = self.callRemote("artist.getAlbums", {"artistID": artistId, "limit": limit})
		list = self.parseAlbums(result)
		return sorted(list, key=itemgetter(sortKey))

	def artistGetVerifiedAlbums(self, artistId, limit):
		result = self.callRemote("artist.getVerifiedAlbums", {"artistID": artistId, "limit": limit})
		list = self.parseSongs(result)
		return list

	def albumGetSongs(self, albumId, limit):
		result = self.callRemote("album.getSongs", {"albumID": albumId, "limit": limit})
		list = self.parseSongs(result)
		return list

	def parseSongs(self, items):
		if 'result' in items:
			i = 0
			list = []
			while(i < len(items['result']['songs'])):
				s = items['result']['songs'][i]
				if 'estDurationSecs' in s:
					dur = s['estDurationSecs']
				else:
					dur = 0
				list.append([s['songName'].encode('ascii', 'ignore'),\
				s['songID'],\
				dur,\
				s['albumName'].encode('ascii', 'ignore'),\
				s['albumID'],\
				s['image']['tiny'].encode('ascii', 'ignore'),\
				s['artistName'].encode('ascii', 'ignore'),\
				s['artistID'],\
				s['image']['small'].encode('ascii', 'ignore'),\
				s['image']['medium'].encode('ascii', 'ignore')])
				i = i + 1
			return list
		else:
			return []
			pass


	def parseArtists(self, items):
		if 'result' in items:
			i = 0
			list = []
			artists = items['result']['artists']
			while(i < len(artists)):
				s = artists[i]
				list.append([s['artistName'].encode('ascii', 'ignore'),\
				s['artistID']])
				i = i + 1
			return list
		else:
			return []

	def parseAlbums(self, items):
		if 'result' in items:
			i = 0
			list = []
			albums = items['result']['albums']
			while(i < len(albums)):
				s = albums[i]
				list.append([s['artistName'].encode('ascii', 'ignore'),\
				s['artistID'],\
				s['albumName'].encode('ascii', 'ignore'),\
				s['albumID'],\
				s['image']['tiny'].encode('ascii', 'ignore')])
				i = i + 1
			return list
		else:
			return []
