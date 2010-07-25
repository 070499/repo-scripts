__scriptname__    = "CDArt Manager Script"
__scriptID__      = "script.cdartmanager"
__author__        = "Giftie"
__version__       = "0.9.8"
__credits__       = "Ppic, Reaven, Imaginos"
__XBMC_Revision__ = "32000"
__date__          = "23-07-10"
import sys
import os
import xbmcaddon
import xbmc


BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "skins", "Default" ) )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ))

print BASE_RESOURCE_PATH

__settings__ = xbmcaddon.Addon(__scriptID__)
__language__ = __settings__.getLocalizedString

if ( __name__ == "__main__" ):
    print "############################################################"
    print "#    %-50s    #" % __scriptname__
    print "#    %-50s    #" % __scriptID__
    print "#    %-50s    #" % __author__
    print "#    %-50s    #" % __version__
    print "############################################################"
    import gui
    ui = gui.GUI( "script-cdartmanager.xml" , os.getcwd(), "Default")
    ui.doModal()
    del ui
    sys.modules.clear()