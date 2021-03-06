import sys
import os

import xbmcgui
import imageDownloader
import xbmcaddon
import xbmc

Addon = sys.modules['__main__'].Addon
getLS = Addon.getLocalizedString
getSetting = Addon.getSetting
setSetting = Addon.setSetting
openSettings = Addon.openSettings


class GUI(xbmcgui.WindowXML):
    # Controls
    CONTROL_MAIN_IMAGE = 100
    IMAGE_LOADING = 101
    LABEL_VISIBLE = 102
    # Actions
    ACTION_CONTEXT_MENU = [117]
    ACTION_MENU = [122]
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_SHOW_INFO = [11]
    ACTION_EXIT_SCRIPT = [13]
    ACTION_DOWN = [4]
    ACTION_UP = [3]
    ACTION_0 = [58, 18]
    ACTION_PLAY = [79]

    def __init__(self, xmlFilename, scriptPath, defaultSkin, defaultRes):
        self.getScraper()

    def getScraper(self):
        addon_path = xbmc.translatePath(Addon.getAddonInfo('path'))
        res_path = os.path.join(addon_path, 'resources', 'lib')
        scrapers_path = os.path.join(res_path, 'scrapers')
        scrapers = [f[:-3] for f in os.listdir(scrapers_path) \
                    if f.endswith('.py')]
        sys.path.insert(0, res_path)
        sys.path.insert(0, scrapers_path)
        imported_modules = [__import__(scraper) for scraper in scrapers]
        self.SOURCES = [m.register() for m in imported_modules]

    def onInit(self):
        self.show_info = True
        self.active_source_id = 0
        aspect_ratio_id = int(getSetting('aspect_ratio2'))
        self.default_aspect = ('scale', 'keep')[aspect_ratio_id]
        self.setSource()
        self.showAlbums()
        self.setFocus(self.getControl(self.CONTROL_MAIN_IMAGE))
        self.showHelp()

    def onFocus(self, controlId):
        pass

    def onAction(self, action):
        if action in self.ACTION_SHOW_INFO:
            self.toggleInfo()
        elif action in self.ACTION_CONTEXT_MENU:
            self.download()
        elif action in self.ACTION_PREVIOUS_MENU:
            # exit the script
            if self.getProperty('type') == 'album':
                self.close()
            # return to previous album
            elif self.getProperty('type') == 'photo':
                self.showAlbums()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()
        elif action in self.ACTION_DOWN and \
             self.getProperty('type') == 'album':
            self.nextSource()
            self.showAlbums()
        elif action in self.ACTION_UP and \
             self.getProperty('type') == 'album':
            self.prevSource()
            self.showAlbums()
        elif action in self.ACTION_0:
            self.toggleAspect()
        elif action in self.ACTION_PLAY:
            pass

    def onClick(self, controlId):
        if controlId == self.CONTROL_MAIN_IMAGE:
            if self.getProperty('type') == 'album':
                self.showPhotos()
            elif self.getProperty('type') == 'photo':
                self.toggleInfo()

    def getProperty(self, property, controlId=CONTROL_MAIN_IMAGE):
        """Returns a property of the selected item"""
        control = self.getControl(controlId)
        return control.getSelectedItem().getProperty(property)

    def toggleInfo(self):
        selectedControl = self.getControl(self.LABEL_VISIBLE)
        if self.show_info:
            selectedControl.setVisible(False)
            self.show_info = False
        else:
            selectedControl.setVisible(True)
            self.show_info = True

    def toggleAspect(self):
        selectedControl = self.getControl(self.CONTROL_MAIN_IMAGE)
        if self.getProperty('aspectratio') == 'scale':
            self.default_aspect = 'keep'
        else:
            self.default_aspect = 'scale'
        for i in range(selectedControl.size()):
            selectedControl.getListItem(i).setProperty('aspectratio',
                                                       self.default_aspect)

    def download(self):
        # get writable directory
        downloadPath = xbmcgui.Dialog().browse(3, ' '.join([getLS(32020),
                                                            getLS(32022)]),
                                               'pictures')
        if downloadPath:
            if self.getProperty('type') == 'photo':
                photos = [{'pic':self.getProperty('pic'), 'title': ''}]
                imageDownloader.Download(photos, downloadPath)
            elif self.getProperty('type') == 'album':
                pDialog = xbmcgui.DialogProgress()
                pDialog.create(self.Source.NAME)
                link = self.getProperty('link')
                pDialog.update(50)
                photos = self.Source.getPhotos(link)
                pDialog.update(100)
                pDialog.close()
                imageDownloader.Download(photos, downloadPath)

    def showPhotos(self):
        self.getControl(self.IMAGE_LOADING).setVisible(True)
        link = self.getProperty('link')
        self.getControl(self.CONTROL_MAIN_IMAGE).reset()
        photos = self.Source.getPhotos(link)
        self.showItems(photos, 'photo')
        self.getControl(self.IMAGE_LOADING).setVisible(False)

    def showAlbums(self):
        self.getControl(self.IMAGE_LOADING).setVisible(True)
        self.getControl(self.CONTROL_MAIN_IMAGE).reset()
        albums = self.Source.getAlbums()
        self.showItems(albums, 'album')
        self.getControl(self.IMAGE_LOADING).setVisible(False)

    def showItems(self, itemSet, type):
        total = len(itemSet)
        for i, item in enumerate(itemSet):
            item['type'] = type
            item['album'] = self.Source.NAME
            item['title'] = item['title']
            item['duration'] = '%s/%s' % (i + 1, total)
            item['aspectratio'] = self.default_aspect
            self.addListItem(self.CONTROL_MAIN_IMAGE, item)

    def addListItem(self, controlId, properties):
        li = xbmcgui.ListItem(label=properties['title'],
                              label2=properties['description'],
                              iconImage=properties['pic'])
        for p in properties.keys():
            li.setProperty(p, properties[p])
        self.getControl(controlId).addItem(li)

    def nextSource(self):
        if len(self.SOURCES) > self.active_source_id + 1:
            self.active_source_id += 1
        else:
            self.active_source_id = 0
        self.setSource()

    def prevSource(self):
        if self.active_source_id == 0:
            self.active_source_id = len(self.SOURCES) - 1
        else:
            self.active_source_id -= 1
        self.setSource()

    def setSource(self):
        self.Source = self.SOURCES[self.active_source_id]

    def showHelp(self):
        if not getSetting('help_already_shown'):
            openSettings()
            setSetting('help_already_shown', 'yes')