import xbmc, xbmcgui

import os

import util, config, dialogbase
from util import *
from configxmlwriter import *

ACTION_CANCEL_DIALOG = (9,10,51,92,110)

CONTROL_BUTTON_EXIT = 5101
CONTROL_BUTTON_SAVE = 6000
CONTROL_BUTTON_CANCEL = 6010

CONTROL_LIST_ROMCOLLECTIONS = 5210
CONTROL_BUTTON_RC_DOWN = 5211
CONTROL_BUTTON_RC_UP = 5212

#Import Games
CONTROL_BUTTON_ROMPATH = 5240
CONTROL_BUTTON_FILEMASK = 5250
CONTROL_BUTTON_IGNOREONSCAN = 5330
CONTROL_BUTTON_ALLOWUPDATE = 5400
CONTROL_BUTTON_MAXFOLDERDEPTH = 5410
CONTROL_BUTTON_DISKINDICATOR = 5420
CONTROL_BUTTON_USEFOLDERASGAMENAME = 5430

#Import Game data
CONTROL_LIST_SCRAPER1 = 5290
CONTROL_LIST_SCRAPER2 = 5300
CONTROL_LIST_SCRAPER3 = 5310
CONTROL_LIST_MEDIATYPES = 5260
CONTROL_BUTTON_MEDIA_DOWN = 5261
CONTROL_BUTTON_MEDIA_UP = 5262
CONTROL_BUTTON_MEDIAPATH = 5270
CONTROL_BUTTON_MEDIAFILEMASK = 5280
CONTROL_BUTTON_REMOVEMEDIAPATH = 5490
CONTROL_BUTTON_ADDMEDIAPATH = 5500


#Browse Games
CONTROL_LIST_IMAGEPLACING_MAIN = 5320
CONTROL_LIST_IMAGEPLACING_INFO = 5340
CONTROL_BUTTON_AUTOPLAYVIDEO_MAIN = 5350
CONTROL_BUTTON_AUTOPLAYVIDEO_INFO = 5360


#Launch Games
CONTROL_BUTTON_EMUCMD = 5220
CONTROL_BUTTON_PARAMS = 5230
CONTROL_BUTTON_USEEMUSOLO = 5440
CONTROL_BUTTON_DONTEXTRACTZIP = 5450
CONTROL_BUTTON_SAVESTATEPATH = 5460
CONTROL_BUTTON_SAVESTATEMASK = 5470
CONTROL_BUTTON_SAVESTATEPARAMS = 5480


class EditRomCollectionDialog(dialogbase.DialogBaseEdit):
		
	selectedControlId = 0
	selectedRomCollection = None	
	romCollections = None
	scraperSites = None
	
	def __init__(self, *args, **kwargs):
		Logutil.log('init Edit Rom Collection', util.LOG_LEVEL_INFO)
		
		self.gui = kwargs[ "gui" ]
		self.romCollections = self.gui.config.romCollections
		self.scraperSites = self.gui.config.scraperSites
		
		self.doModal()
	
	
	def onInit(self):
		Logutil.log('onInit Edit Rom Collection', util.LOG_LEVEL_INFO)
		
		#Rom Collections
		Logutil.log('build rom collection list', util.LOG_LEVEL_INFO)
		romCollectionList = []
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			romCollectionList.append(romCollection.name)
		self.addItemsToList(CONTROL_LIST_ROMCOLLECTIONS, romCollectionList)
		
		Logutil.log('build scraper lists', util.LOG_LEVEL_INFO)
		self.availableScrapers = self.getAvailableScrapers(False)
		self.addItemsToList(CONTROL_LIST_SCRAPER1, self.availableScrapers)
		self.addItemsToList(CONTROL_LIST_SCRAPER2, self.availableScrapers)
		self.addItemsToList(CONTROL_LIST_SCRAPER3, self.availableScrapers)

		Logutil.log('build imagePlacing list', util.LOG_LEVEL_INFO)		
		self.imagePlacingList = []
		imagePlacingRows = self.gui.config.tree.findall('ImagePlacing/fileTypeFor')
		for imagePlacing in imagePlacingRows:
			Logutil.log('add image placing: ' +str(imagePlacing.attrib.get('name')), util.LOG_LEVEL_INFO)
			option = imagePlacing.attrib.get('name')
			#HACK: remove all video options from config
			if(option.upper().find('VIDEO') >= 0):
				continue
			try:
				option = config.imagePlacingDict[option]
			except:
				pass
			self.imagePlacingList.append(option)
		self.addItemsToList(CONTROL_LIST_IMAGEPLACING_MAIN, self.imagePlacingList)
		self.addItemsToList(CONTROL_LIST_IMAGEPLACING_INFO, self.imagePlacingList)
		
		self.updateRomCollectionControls()
		
		
	def onAction(self, action):		
		if (action.getId() in ACTION_CANCEL_DIALOG):
			self.close()
		
	
	def onClick(self, controlID):
		
		Logutil.log('onClick', util.LOG_LEVEL_INFO)
		
		if (controlID == CONTROL_BUTTON_EXIT): # Close window button
			Logutil.log('close', util.LOG_LEVEL_INFO)
			self.close()
		#OK
		elif (controlID == CONTROL_BUTTON_SAVE):
			Logutil.log('save', util.LOG_LEVEL_INFO)
			#store selectedRomCollection
			if(self.selectedRomCollection != None):
				self.updateSelectedRomCollection()
				self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
						
			configWriter = ConfigXmlWriter(False)
			success, message = configWriter.writeRomCollections(self.romCollections, True)
			
			if not success:
				xbmcgui.Dialog().ok('Configuration Error', message)
			self.close()
			
		#Cancel
		elif (controlID == CONTROL_BUTTON_CANCEL):
			self.close()
		#Rom Collection list
		elif(self.selectedControlId in (CONTROL_BUTTON_RC_DOWN, CONTROL_BUTTON_RC_UP)):
			if(self.selectedRomCollection != None):
				#save current values to selected Rom Collection
				self.updateSelectedRomCollection()
				#store previous selectedRomCollections state
				self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
			
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateRomCollectionControls()
		
		#Media Path
		elif(self.selectedControlId in (CONTROL_BUTTON_MEDIA_DOWN, CONTROL_BUTTON_MEDIA_UP)):
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateMediaPathControls()
			
		elif (controlID == CONTROL_BUTTON_EMUCMD):
			if (self.selectedRomCollection.name == 'Linux' or self.selectedRomCollection.name == 'Macintosh' or self.selectedRomCollection.name == 'Windows'):
				emulatorPath = self.editTextProperty(CONTROL_BUTTON_EMUCMD, 'emulator command')
			else:	
				dialog = xbmcgui.Dialog()
				
				emulatorPath = dialog.browse(1, '%s Emulator' %self.selectedRomCollection.name, 'files')
				if(emulatorPath == ''):
					return
							
			self.selectedRomCollection.emulatorCmd = emulatorPath
			control = self.getControlById(CONTROL_BUTTON_EMUCMD)
			control.setLabel(emulatorPath)
			
		elif (controlID == CONTROL_BUTTON_PARAMS):
			emulatorParams = self.editTextProperty(CONTROL_BUTTON_PARAMS, 'emulator params')
			self.selectedRomCollection.emulatorParams = emulatorParams 			
			
		elif (controlID == CONTROL_BUTTON_ROMPATH):
			self.editRomPath()
			
		elif (controlID == CONTROL_BUTTON_FILEMASK):
			self.editRomFileMask()
			
		elif (controlID == CONTROL_BUTTON_MEDIAPATH):
			self.editMediaPath()
		
		elif (controlID == CONTROL_BUTTON_MEDIAFILEMASK):
			self.editMediaFileMask()
		
		elif (controlID == CONTROL_BUTTON_ADDMEDIAPATH):
			self.addMediaPath()
			
		elif (controlID == CONTROL_BUTTON_REMOVEMEDIAPATH):
			self.removeMediaPath()
			
		elif (controlID == CONTROL_BUTTON_MAXFOLDERDEPTH):
			maxFolderDepth = self.editTextProperty(CONTROL_BUTTON_MAXFOLDERDEPTH, 'max folder depth')
			self.selectedRomCollection.maxFolderDepth = maxFolderDepth
			
		elif (controlID == CONTROL_BUTTON_DISKINDICATOR):
			diskIndicator = self.editTextProperty(CONTROL_BUTTON_DISKINDICATOR, 'disk indicator')
			self.selectedRomCollection.diskPrefix = diskIndicator
						
		elif (controlID == CONTROL_BUTTON_SAVESTATEPATH):
			saveStatePathComplete = self.editPathWithFileMask(CONTROL_BUTTON_SAVESTATEPATH, '%s savestate path' %self.selectedRomCollection.name, CONTROL_BUTTON_SAVESTATEMASK)
			if(saveStatePathComplete != ''):
				self.selectedRomCollection.saveStatePath = saveStatePathComplete
				
		elif (controlID == CONTROL_BUTTON_SAVESTATEMASK):
			self.selectedRomCollection.saveStatePath = self.editFilemask(CONTROL_BUTTON_SAVESTATEMASK, 'savestate filemask', self.selectedRomCollection.saveStatePath)
			
		elif (controlID == CONTROL_BUTTON_SAVESTATEPARAMS):
			saveStateParams = self.editTextProperty(CONTROL_BUTTON_SAVESTATEPARAMS, 'savestate params')
			self.selectedRomCollection.saveStateParams = saveStateParams
			
	
	def onFocus(self, controlId):
		self.selectedControlId = controlId
	
	
	def updateRomCollectionControls(self):
		
		Logutil.log('updateRomCollectionControls', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(CONTROL_LIST_ROMCOLLECTIONS)
		selectedRomCollectionName = str(control.getSelectedItem().getLabel())
				
		Logutil.log('selected rom collection: ' +str(selectedRomCollectionName), util.LOG_LEVEL_INFO)
				
		self.selectedRomCollection = None
		
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			if romCollection.name == selectedRomCollectionName:
				self.selectedRomCollection = romCollection
				break
			
		if(self.selectedRomCollection == None):
			return
				
		#Import Games
		#HACK: split romPath and fileMask
		firstRomPath = ''
		fileMask = ''
		for romPath in self.selectedRomCollection.romPaths:
			
			pathParts = os.path.split(romPath)			 
			if(firstRomPath == ''):				
				firstRomPath = pathParts[0]
				fileMask = pathParts[1]
			elif(firstRomPath == pathParts[0]):
				fileMask = fileMask +',' +pathParts[1]
								
		control = self.getControlById(CONTROL_BUTTON_ROMPATH)
		control.setLabel(firstRomPath)
		
		control = self.getControlById(CONTROL_BUTTON_FILEMASK)
		control.setLabel(fileMask)
		
		control = self.getControlById(CONTROL_BUTTON_IGNOREONSCAN)		
		control.setSelected(self.selectedRomCollection.ignoreOnScan)
		
		control = self.getControlById(CONTROL_BUTTON_ALLOWUPDATE)
		control.setSelected(self.selectedRomCollection.allowUpdate)
		
		control = self.getControlById(CONTROL_BUTTON_DISKINDICATOR)
		control.setLabel(self.selectedRomCollection.diskPrefix)
		
		control = self.getControlById(CONTROL_BUTTON_MAXFOLDERDEPTH)
		control.setLabel(str(self.selectedRomCollection.maxFolderDepth))
		
		control = self.getControlById(CONTROL_BUTTON_USEFOLDERASGAMENAME)
		control.setSelected(self.selectedRomCollection.useFoldernameAsGamename)
		
		#Import Game Data
		#Media Types
		mediaTypeList = []
		firstMediaPath = ''
		firstMediaFileMask = ''
		for mediaPath in self.selectedRomCollection.mediaPaths:
			mediaTypeList.append(mediaPath.fileType.name)
			if(firstMediaPath == ''):
				pathParts = os.path.split(mediaPath.path)
				firstMediaPath = pathParts[0]
				firstMediaFileMask = pathParts[1]
				
		self.addItemsToList(CONTROL_LIST_MEDIATYPES, mediaTypeList)
		
		control = self.getControlById(CONTROL_BUTTON_MEDIAPATH)
		control.setLabel(firstMediaPath)
		
		control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
		control.setLabel(firstMediaFileMask)
						
		self.selectScrapersInList(self.selectedRomCollection.scraperSites, self.availableScrapers)
		
		#Browse Games
		optionMain = self.selectedRomCollection.imagePlacingMain.name
		try:
			optionMain = config.imagePlacingDict[optionMain]
		except:
			pass
		self.selectItemInList(optionMain, CONTROL_LIST_IMAGEPLACING_MAIN)
		
		optionInfo = self.selectedRomCollection.imagePlacingInfo.name
		try:
			optionInfo = config.imagePlacingDict[optionInfo]
		except:			
			pass		
		self.selectItemInList(optionInfo, CONTROL_LIST_IMAGEPLACING_INFO)
		
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_MAIN)
		if(control != None):
			control.setSelected(self.selectedRomCollection.autoplayVideoMain)
		
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_INFO)
		if(control != None):
			control.setSelected(self.selectedRomCollection.autoplayVideoInfo)
		
		#Launch Games
		control = self.getControlById(CONTROL_BUTTON_EMUCMD)		
		control.setLabel(self.selectedRomCollection.emulatorCmd)
		
		control = self.getControlById(CONTROL_BUTTON_PARAMS)
		control.setLabel(self.selectedRomCollection.emulatorParams)
		
		control = self.getControlById(CONTROL_BUTTON_USEEMUSOLO)
		control.setSelected(self.selectedRomCollection.useEmuSolo)
		
		pathParts = os.path.split(self.selectedRomCollection.saveStatePath)
		saveStatePath = pathParts[0]
		saveStateFileMask = pathParts[1]
		
		control = self.getControlById(CONTROL_BUTTON_SAVESTATEPATH)
		control.setLabel(saveStatePath)
		
		control = self.getControlById(CONTROL_BUTTON_SAVESTATEMASK)
		control.setLabel(saveStateFileMask)
		
		control = self.getControlById(CONTROL_BUTTON_SAVESTATEPARAMS)
		control.setLabel(self.selectedRomCollection.saveStateParams)
		
		control = self.getControlById(CONTROL_BUTTON_DONTEXTRACTZIP)
		control.setSelected(self.selectedRomCollection.doNotExtractZipFiles)
	
	
	def updateMediaPathControls(self):
		
		control = self.getControlById(CONTROL_LIST_MEDIATYPES)
		selectedMediaType = str(control.getSelectedItem().getLabel())
		
		for mediaPath in self.selectedRomCollection.mediaPaths:
			if mediaPath.fileType.name == selectedMediaType:
				
				pathParts = os.path.split(mediaPath.path)
				control = self.getControlById(CONTROL_BUTTON_MEDIAPATH)
				control.setLabel(pathParts[0])				
				control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
				control.setLabel(pathParts[1])
				
				break
	
	
	def updateSelectedRomCollection(self):
		
		Logutil.log('updateSelectedRomCollection', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(CONTROL_BUTTON_IGNOREONSCAN)
		self.selectedRomCollection.ignoreOnScan = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_ALLOWUPDATE)
		self.selectedRomCollection.allowUpdate = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_USEFOLDERASGAMENAME)
		self.selectedRomCollection.useFoldernameAsGamename = bool(control.isSelected())
		
		sites = []
		sites = self.addScraperToSiteList(CONTROL_LIST_SCRAPER1, sites, self.selectedRomCollection)
		sites = self.addScraperToSiteList(CONTROL_LIST_SCRAPER2, sites, self.selectedRomCollection)
		sites = self.addScraperToSiteList(CONTROL_LIST_SCRAPER3, sites, self.selectedRomCollection)
			
		self.selectedRomCollection.scraperSites = sites		
		
		#Image Placing Main
		control = self.getControlById(CONTROL_LIST_IMAGEPLACING_MAIN)
		imgPlacingItem = control.getSelectedItem()
		imgPlacingName = imgPlacingItem.getLabel()
		#HACK search key by value
		for item in config.imagePlacingDict.items():
			if(item[1] == imgPlacingName):
				imgPlacingName = item[0]
		imgPlacing, errorMsg = self.gui.config.readImagePlacing(imgPlacingName, self.gui.config.tree)
		self.selectedRomCollection.imagePlacingMain = imgPlacing
		
		#Image Placing Info
		control = self.getControlById(CONTROL_LIST_IMAGEPLACING_INFO)
		imgPlacingItem = control.getSelectedItem()
		imgPlacingName = imgPlacingItem.getLabel()
		#HACK search key by value
		for item in config.imagePlacingDict.items():
			if(item[1] == imgPlacingName):
				imgPlacingName = item[0]
		imgPlacing, errorMsg = self.gui.config.readImagePlacing(imgPlacingName, self.gui.config.tree)
		self.selectedRomCollection.imagePlacingInfo = imgPlacing
		
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_MAIN)
		if(control != None):
			self.selectedRomCollection.autoplayVideoMain = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_INFO)
		if(control != None):
			self.selectedRomCollection.autoplayVideoInfo = bool(control.isSelected())
		
		control = self.getControlById(CONTROL_BUTTON_USEEMUSOLO)
		self.selectedRomCollection.useEmuSolo = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_DONTEXTRACTZIP)
		self.selectedRomCollection.doNotExtractZipFiles = bool(control.isSelected())
	
	
	def editRomPath(self):
		
		dialog = xbmcgui.Dialog()
			
		romPath = dialog.browse(0, '%s Roms' %self.selectedRomCollection.name, 'files')
		if(romPath == ''):
			return
					
		control = self.getControlById(CONTROL_BUTTON_FILEMASK)
		fileMaskInput = control.getLabel()
		fileMasks = fileMaskInput.split(',')
		romPaths = []
		for fileMask in fileMasks:
			romPathComplete = os.path.join(romPath, fileMask.strip())					
			romPaths.append(romPathComplete)
					
		self.selectedRomCollection.romPaths = romPaths
		control = self.getControlById(CONTROL_BUTTON_ROMPATH)
		control.setLabel(romPath)
		
		
	def editRomFileMask(self):
		
		control = self.getControlById(CONTROL_BUTTON_FILEMASK)
		romFileMask = control.getLabel()
		
		keyboard = xbmc.Keyboard()
		keyboard.setHeading('Enter Rom File Mask')
		keyboard.setDefault(romFileMask)			
		keyboard.doModal()
		if (keyboard.isConfirmed()):
			romFileMask = keyboard.getText()
								
		#HACK: this only handles 1 base rom path
		romPath = self.selectedRomCollection.romPaths[0]
		pathParts = os.path.split(romPath)
		romPath = pathParts[0]
		fileMasks = romFileMask.split(',')
		romPaths = []
		for fileMask in fileMasks:				
			romPathComplete = os.path.join(romPath, fileMask.strip())					
			romPaths.append(romPathComplete)
		
		self.selectedRomCollection.romPaths = romPaths
		control.setLabel(romFileMask)
		
		
	def editMediaPath(self):
		
		#get selected medias type			
		control = self.getControlById(CONTROL_LIST_MEDIATYPES)
		selectedMediaType = str(control.getSelectedItem().getLabel())
		
		#get current media path
		currentMediaPath = None
		currentMediaPathIndex = -1;
		for i in range(0, len(self.selectedRomCollection.mediaPaths)):
			mediaPath = self.selectedRomCollection.mediaPaths[i]
			if(mediaPath.fileType.name == selectedMediaType):
				currentMediaPath = mediaPath
				currentMediaPathIndex = i
				break
		
		mediaPathComplete = self.editPathWithFileMask(CONTROL_BUTTON_MEDIAPATH, '%s Path' %currentMediaPath.fileType.name, CONTROL_BUTTON_MEDIAFILEMASK)
		
		if(mediaPathComplete != ''):
			currentMediaPath.path = mediaPathComplete
			self.selectedRomCollection.mediaPaths[currentMediaPathIndex] = currentMediaPath
	
	
	def editMediaFileMask(self):
		
		#get selected medias type			
		control = self.getControlById(CONTROL_LIST_MEDIATYPES)
		selectedMediaType = str(control.getSelectedItem().getLabel())
		
		#get current media path
		currentMediaPath = None
		currentMediaPathIndex = -1;
		for i in range(0, len(self.selectedRomCollection.mediaPaths)):
			mediaPath = self.selectedRomCollection.mediaPaths[i]
			if(mediaPath.fileType.name == selectedMediaType):
				currentMediaPath = mediaPath
				currentMediaPathIndex = i
				break							
			
		mediaPathComplete = self.editFilemask(CONTROL_BUTTON_MEDIAFILEMASK, 'media filemask', currentMediaPath.path)
					
		currentMediaPath.path = mediaPathComplete
		self.selectedRomCollection.mediaPaths[currentMediaPathIndex] = currentMediaPath
		
		
	def addMediaPath(self):
		
		mediaTypes = self.gui.config.tree.findall('FileTypes/FileType')
			
		mediaTypeList = []
		
		for mediaType in mediaTypes:
			name = mediaType.attrib.get('name')
			if(name != None):
				type = mediaType.find('type')
				if(type != None and type.text == 'video'):
					name = name +' (video)'
				
				#check if media type is already in use for selected RC
				isMediaTypeInUse = False
				for mediaPath in self.selectedRomCollection.mediaPaths:
					if(mediaPath.fileType.name == name):
						isMediaTypeInUse = True
				
				if(not isMediaTypeInUse):
					mediaTypeList.append(name)
		
		mediaTypeIndex = xbmcgui.Dialog().select('Choose a media path to add', mediaTypeList)
		if(mediaTypeIndex == -1):
			return
		
		mediaType = mediaTypeList[mediaTypeIndex]
		mediaType = mediaType.replace(' (video)', '')
				
		mediaPathComplete = self.editPathWithFileMask(CONTROL_BUTTON_MEDIAPATH, '%s Path' %mediaType, CONTROL_BUTTON_MEDIAFILEMASK)
		#TODO: use default value in editFilemask
		control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
		control.setLabel('%GAME%.*')
		mediaPathComplete = self.editFilemask(CONTROL_BUTTON_MEDIAFILEMASK, 'media filemask', mediaPathComplete)
		
		mediaPath = MediaPath()
		fileType = FileType()
		fileType.name = mediaType
		mediaPath.fileType = fileType
		mediaPath.path = mediaPathComplete
		self.selectedRomCollection.mediaPaths.append(mediaPath)			
		
		control = self.getControlById(CONTROL_LIST_MEDIATYPES)
		item = xbmcgui.ListItem(mediaType, '', '', '')
		control.addItem(item)
		
		self.selectItemInList(mediaType, CONTROL_LIST_MEDIATYPES)
		
		xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
		self.updateMediaPathControls()
		
		
	def removeMediaPath(self):
		
		mediaTypeList = []
		for mediaPath in self.selectedRomCollection.mediaPaths:
			mediaTypeList.append(mediaPath.fileType.name)
		
		mediaTypeIndex = xbmcgui.Dialog().select('Choose a media path to remove', mediaTypeList)
		if(mediaTypeIndex == -1):
			return
					
		mediaType = mediaTypeList[mediaTypeIndex]
		for mediaPath in self.selectedRomCollection.mediaPaths:
			if(mediaPath.fileType.name == mediaType):
				self.selectedRomCollection.mediaPaths.remove(mediaPath)
				break
			
		if(self.selectedRomCollection != None):
			#save current values to selected Rom Collection
			self.updateSelectedRomCollection()
			#store previous selectedRomCollections state
			self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
			
		self.updateRomCollectionControls()
	
	
	def selectScrapersInList(self, sitesInRomCollection, sitesInList):
		
		Logutil.log('selectScrapersInList', util.LOG_LEVEL_INFO)
		
		if(len(sitesInRomCollection) >= 1):
			self.selectItemInList(sitesInRomCollection[0].name, CONTROL_LIST_SCRAPER1)			
		else:
			self.selectItemInList('None', CONTROL_LIST_SCRAPER1)
		if(len(sitesInRomCollection) >= 2):
			self.selectItemInList(sitesInRomCollection[1].name, CONTROL_LIST_SCRAPER2)
		else:
			self.selectItemInList('None', CONTROL_LIST_SCRAPER2)
		if(len(sitesInRomCollection) >= 3):
			self.selectItemInList(sitesInRomCollection[2].name, CONTROL_LIST_SCRAPER3)
		else:
			self.selectItemInList('None', CONTROL_LIST_SCRAPER3)
			
			
	def addScraperToSiteList(self, controlId, sites, romCollection):				

		Logutil.log('addScraperToSiteList', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(controlId)
		scraperItem = control.getSelectedItem()
		scraper = scraperItem.getLabel()
		
		if(scraper == 'None'):
			return sites
		
		#check if this site is already available for current RC
		for site in romCollection.scraperSites:
			if(site.name == scraper):
				sites.append(site)
				return sites
		
		siteRow = None
		siteRows = self.gui.config.tree.findall('Scrapers/Site')
		for element in siteRows:
			if(element.attrib.get('name') == scraper):
				siteRow = element
				break
		
		if(siteRow == None):
			xbmcgui.Dialog().ok('Configuration Error', 'Site %s does not exist in config.xml' %scraper)
			return None
		
		site, errorMsg = self.gui.config.readScraper(siteRow, romCollection.name, '', '', True, self.gui.config.tree)
		if(site != None):
			sites.append(site)
			
		return sites