'''
   Simple Downloader plugin for XBMC
   Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import urllib2
import os
import time
import subprocess
import DialogDownloadProgress


class SimpleDownloader():
    dialog = ""

    def __init__(self):
        self.version = "0.9.1"
        self.plugin = "SimpleDownloader-" + self.version

        if hasattr(sys.modules["__main__"], "common"):
            self.common = sys.modules["__main__"].common
        else:
            import CommonFunctions
            self.common = CommonFunctions

        self.common.log("")

        try:
            import StorageServer
            self.cache = StorageServer.StorageServer("Downloader")
        except:
            import storageserverdummy as StorageServer
            self.cache = StorageServer.StorageServer("Downloader")

        if hasattr(sys.modules["__main__"], "xbmcaddon"):
            self.xbmcaddon = sys.modules["__main__"].xbmcaddon
        else:
            import xbmcaddon
            self.xbmcaddon = xbmcaddon

        self.settings = self.xbmcaddon.Addon(id='script.module.simple.downloader')

        if hasattr(sys.modules["__main__"], "xbmc"):
            self.xbmc = sys.modules["__main__"].xbmc
        else:
            import xbmc
            self.xbmc = xbmc

        if hasattr(sys.modules["__main__"], "xbmcvfs"):
            self.xbmcvfs = sys.modules["__main__"].xbmcvfs
        else:
            try:
                import xbmcvfs
                self.xbmcvfs = xbmcvfs
            except ImportError:
                import xbmcvfsdummy as xbmcvfs
                self.xbmcvfs = xbmcvfs

        if hasattr(sys.modules["__main__"], "dbglevel"):
            self.dbglevel = sys.modules["__main__"].dbglevel
        else:
            self.dbglevel = 3

        if hasattr(sys.modules["__main__"], "dbg"):
            self.dbg = sys.modules["__main__"].dbg
        else:
            self.dbg = True

        self.language = self.settings.getLocalizedString
        self.hide_during_playback = self.settings.getSetting("hideDuringPlayback") == "true"
        self.notification_length = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10][int(self.settings.getSetting("notification_length"))]

        if self.settings.getSetting("rtmp_binary"):
            self.rtmp_binary = self.settings.getSetting("rtmp_binary")
        else:
            self.rtmp_binary = "rtmpdump"

        if self.settings.getSetting("rtmp_binary"):
            self.vlc_binary = self.settings.getSetting("vlc_binary")
        else:
            self.vlc_binary = "vlc"

        if self.settings.getSetting("rtmp_binary"):
            self.mplayer_binary = self.settings.getSetting("mplayer_binary")
        else:
            self.mplayer_binary = "mplayer"

        self.__workersByName = {}

        self.temporary_path = self.xbmc.translatePath(self.settings.getAddonInfo("profile"))
        if not self.xbmcvfs.exists(self.temporary_path):
            os.makedirs(self.temporary_path)

        self.common.log("Done")

    def download(self, filename, params={}, async=True):
        self.common.log("", 5)
        if async:
            self.common.log("Async", 5)
            self._run_async(self._startDownload, filename, params)
        else:
            self.common.log("Normal", 5)
            self._startDownload(filename, params)
        self.common.log("Done", 5)

    def _startDownload(self, filename, params={}):
        self.common.log("", 5)
        if self.cache.lock("SimpleDownloaderLock"):
            self.common.log("Downloader not active, initializing downloader.")
            self._addItemToQueue(filename, params)
            self._processQueue()
            self.cache.unlock("SimpleDownloaderLock")
        else:
            self.common.log("Downloader is active, Queueing item.")
            self._addItemToQueue(filename, params)
        self.common.log("Done", 5)

    def _setPaths(self, filename, params={}):
        self.common.log(filename, 5)
        params["path_incomplete"] = os.path.join(self.temporary_path.decode("utf-8"), self.common.makeUTF8(filename))
        params["path_complete"] = os.path.join(params["download_path"].decode("utf-8"), self.common.makeUTF8(filename))
        self.common.log(params["path_incomplete"], 5)
        self.common.log(params["path_complete"], 5)
        self.common.log("Done", 5)

    def _processQueue(self):
        self.common.log("")
        item = self._getNextItemFromQueue()
        if item:
            (filename, item) = item

            if item:
                if not self.dialog:
                    self.dialog = DialogDownloadProgress.DownloadProgress()
                    self.dialog.create(self.language(201), "")

                while item:
                    status = 500
                    self._setPaths(filename, item)
                    if self.xbmcvfs.exists(item["path_complete"]):
                        self.xbmcvfs.delete(item["path_complete"])

                    if self.xbmcvfs.exists(item["path_incomplete"]):
                        self.xbmcvfs.delete(item["path_incomplete"])

                    if not "url" in item:
                        self.common.log("URL missing : %s" % repr(item))
                    elif item["url"].find("ftp") > -1:
                        self.common.log("Found FTP")
                        status = self._downloadURL(filename, item)
                    elif item["url"].find("http") > -1:
                        self.common.log("Found HTTP")
                        status = self._downloadURL(filename, item)
                    else:
                        self.common.log("Trying to detect media stream")
                        self._detectStream(filename, item)
                        if "cmd_call" in item:
                            status = self._downloadStream(filename, item)
                        else:
                            self._showMessage(self.language(301), filename)

                    if status == 200:
                        if self.xbmcvfs.exists(item["path_incomplete"]):
                            self.xbmcvfs.rename(item["path_incomplete"], item["path_complete"])
                            self._showMessage(self.language(203), filename)
                        else:
                            self.common.log("Couldn't find file: " + item["path_incomplete"])
                            self._showMessage(self.language(204), "ERROR")
                    else:
                        self._showMessage(self.language(204), self.language(302))

                    self._removeItemFromQueue(filename)
                    item = self._getNextItemFromQueue()
                    if item:
                        (filename, item) = item

                self.common.log("Finished download queue.")
                if self.dialog:
                    self.dialog.close()
                    self.common.log("Closed dialog")
                self.dialog = ""

    def _detectStream(self, filename, item):
        get = item.get
        self.common.log(get("url"))

        # RTMPDump
        if get("url").find("rtmp") > -1 or get("use_rtmpdump"):
            self.common.log("Trying rtmpdump")
            # Detect filesize
            probe_args = [self.rtmp_binary, "--stop", "1", "-r", get("url")]

            if get("live"):
                probe_args += ["-v"]

            if get("player_url"):
                probe_args += ["-W", get("player_url")]

            if get("token"):
                probe_args += ["-T", get("token")]

            probe_args += ["-o", item["path_incomplete"]]
            try:
                p = subprocess.Popen(probe_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = p.communicate()[1]
            except:
                self.common.log("Couldn't find rtmpdump binary")
            else:
                if output.find("filesize") > -1:
                    item["total_size"] = int(float(output[output.find("filesize") + len("filesize"):output.find("\n", output.find("filesize"))]))
                elif get("live"):
                    item["total_size"] = 0

                cmd_call = [self.rtmp_binary, "-r", get("url")]

                if get("live"):
                    cmd_call += ["-v"]

                if get("duration"):
                    cmd_call += ["--stop", str(get("duration"))]

                if get("player_url"):
                    cmd_call += ["-W", get("player_url")]

                if get("token"):
                    cmd_call += ["-T", get("token")]

                cmd_call += ["-o", item["path_incomplete"]]
                item["cmd_call"] = cmd_call

        # VLC
        # Fix getting filesize
        if (not "total_size" in item and not "cmd_call" in item) or get("use_vlc"):
            self.common.log("Trying vlc")
            # Detect filesize
            probe_args = [self.vlc_binary, "-I", "dummy", "-v", "-v", "--stop-time", "1", "--sout", "file/avi:" + item["path_incomplete"], item["url"], "vlc://quit"]

            self.common.log(probe_args)

            try:
                p = subprocess.Popen(probe_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = p.communicate()[1]
            except:
                self.common.log("Couldn't find vlc binary")
            else:
                if output.find(get("url") + "' successfully opened") > -1:
                    if output.find("media_length:") > -1 and False:
                        item["total_size"] = int(float(output[output.find("media_length:") + len("media_length:"):output.find("s", output.find("media_length:"))]))
                    elif get("live"):
                        item["total_size"] = 0

                    # Download args
                    cmd_call = [self.vlc_binary, "-I", "dummy", "--sout", "file/avi:" + get("path_incomplete")]

                    if "duration" in item:
                        cmd_call += ["--stop-time", str(get("duration"))]

                    cmd_call += [get("url"), "vlc://quit"]
                    item["cmd_call"] = cmd_call

        # Mplayer
        if (not "total_size" in item and not "cmd_call" in item and not "duration" in item) or get("use_mplayer"):
            self.common.log("Trying mplayer")
            # Detect filesize
            probe_args = [self.mplayer_binary, "-v", "-endpos", "1", "-vo", "null", "-ao", "null", get("url")]

            self.common.log(probe_args)

            try:
                p = subprocess.Popen(probe_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print "XXXXX : " + repr(p.returncode)
                output = p.communicate()[0]
            except:
                self.common.log("Couldn't find mplayer binary")
            else:
                if output.find("filesize") > -1:
                    item["total_size"] = int(float(output[output.find("filesize: ") + len("filesize: "):output.find("\n", output.find("filesize: "))]))
                elif get("live"):
                    item["total_size"] = 0

                while p.returncode == None:
                    time.sleep(0.1)

                print repr(p.returncode)
                if p.returncode == 0:
                    item["cmd_call"] = [self.mplayer_binary, "-v", "-dumpstream", "-dumpfile", item["path_incomplete"], get("url")]

        if not "total_size" in item:
            item["total_size"] = 0

    def _downloadStream(self, filename, item):
        get = item.get
        self.common.log(filename)
        self.common.log(get("cmd_call"))

        p = subprocess.Popen(get("cmd_call"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        same_bytes_count = 0
        retval = 1

        params = {"bytes_so_far": 0, "mark": 0.0, "queue_mark": 0.0, "obytes_so_far": 0}
        item["percent"] = 0.1
        item["old_percent"] = -1
        delay = 0.5
        #for chunk in p.stderr:
        #for chunk in p.stdout:
        #while True:
        while p.returncode == None:
            if self.xbmcvfs.exists(item["path_incomplete"]):
                params["bytes_so_far"] = os.path.getsize(item["path_incomplete"])
                if params["mark"] == 0.0 and params["bytes_so_far"] > 0:
                    params["mark"] = time.time()
                    self.common.log("Mark set")

            if params["bytes_so_far"] == params["obytes_so_far"]:
                same_bytes_count += 1
                delay = delay * 1.2

                if same_bytes_count >= 10 and (item["total_size"] != 0 or params["bytes_so_far"] != 0):
                    self.common.log("Download complete. Same bytes for 10 times in a row.")
                    if (item["total_size"] > 0 and item["total_size"] * 0.998 < params["bytes_so_far"]):
                        self.common.log("Size disrepancy: " + str(item["total_size"] - params["bytes_so_far"]))
                    retval = 0
                    break
                else:
                    self.common.log("Sleeping: " + str(delay) + " - " + str(params["bytes_so_far"]), 5)
                    time.sleep(delay)
                    continue
            else:
                same_bytes_count = 0
                delay = delay * 0.8

            self.common.log("bytes_so_far : " + str(params["bytes_so_far"]))

            self._generatePercent(item, params)

            if item["percent"] > item["old_percent"]:
                self._updateProgress(filename, item, params)
                item["old_percent"] = item["percent"]

            if params["bytes_so_far"] >= item["total_size"] and item["total_size"] != 0:
                self.common.log("Download complete. Matched size")
                retval = 0
                break

            if "duration" in item and params["mark"] > 0.0 and (params["mark"] + int(get("duration")) + 10 < time.time()) and False:
                self.common.log("Download complete. Over duration.")
                retval = 0
                break

            # Some rtmp streams seem abort after ~ 99.8%. Don't complain for those.
            if (item["total_size"] != 0 and get("url").find("rtmp") > -1 and item["total_size"] * 0.998 < params["bytes_so_far"]):
                self.common.log("Download complete. Size disrepancy: " + str(item["total_size"] - params["bytes_so_far"]) + " - " + str(same_bytes_count))
                retval = 0
                break

            params["obytes_so_far"] = params["bytes_so_far"]

        if retval == 1:
            self.common.log("Download failed")
            return 500
        else:
            self.common.log("done")
            return 200

    def _downloadURL(self, filename, item):
        self.common.log(filename)

        url = urllib2.Request(item["url"])
        url.add_header("User-Agent", self.common.USERAGENT)

        file = self.common.openFile(item["path_incomplete"], "wb")
        con = urllib2.urlopen(url)

        item["total_size"] = 0
        chunk_size = 1024 * 8

        if con.info().getheader("Content-Length").strip():
            item["total_size"] = int(con.info().getheader("Content-Length").strip())

        #try:
        if True:
            params = {"bytes_so_far": 0, "mark": 0.0, "queue_mark": 0.0, "obytes_so_far": 0}
            item["percent"] = 0.1
            item["old_percent"] = -1

            while 1:
                chunk = con.read(chunk_size)
                file.write(chunk)
                params["bytes_so_far"] += len(chunk)

                if params["mark"] == 0.0 and params["bytes_so_far"] > 0:
                    params["mark"] = time.time()
                    self.common.log("Mark set")

                self._generatePercent(item, params)

                if item["percent"] > item["old_percent"]:
                    self._updateProgress(filename, item, params)
                    item["old_percent"] = item["percent"]

                params["obytes_so_far"] = params["bytes_so_far"]

                if not chunk:
                    break

            con.close()
            file.close()
        #except:
        else:
            self.common.log("Download failed.")
            try:
                con.close()
                file.close()
            except:
                self.common.log("Failed to close download stream and file handle")

            self._showMessage(self.language(204), "ERROR")
            return 500

        self.common.log("done")
        return 200

    def _generatePercent(self, item, params):
        self.common.log("", 5)
        get = params.get
        iget = item.get

        new_delta = False
        if "last_delta" in item:
            if time.time() - item["last_delta"] > 0.2:
                new_delta = True
        else:
            item["last_delta"] = 0.0
            new_delta = True

        if item["total_size"] > 0 and new_delta:
            self.common.log("total_size", 5)
            item["percent"] = float(get("bytes_so_far")) / float(item["total_size"]) * 100
        elif new_delta:
            self.common.log("cycle - " + str(time.time() - item["last_delta"]), 2)
            delta = time.time() - item["last_delta"]
            if delta > 10 or delta < 0:
                delta = 5

            item["percent"] = iget("old_percent") + delta
            if item["percent"] >= 100:
                item["percent"] -= 100
                item["old_percent"] = item["percent"]

        if new_delta:
            item["last_delta"] = time.time()

    def _getHumanReadable(self, size, precision=2):
        self.common.log(repr(size), 5)
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffixIndex = 0
        while size > 1024:
            suffixIndex += 1  # increment the index of the suffix
            size = size / 1024.0  # apply the division
        result = "%.*f %s" % (precision, size, suffixes[suffixIndex])
        self.common.log(repr(result), 5)
        return result

    def _updateProgress(self, filename, item, params):
        self.common.log("")
        get = params.get
        iget = item.get
        queue = False
        new_mark = time.time()
        speed = int((get("bytes_so_far") / 1024) / (new_mark - get("mark")))
        progress = self._getHumanReadable(get("bytes_so_far"))

        if new_mark - get("queue_mark") > 1.5:
            queue = self.cache.get("SimpleDownloaderQueue")
            self.queue = queue
        elif hasattr(self, "queue"):
            queue = self.queue

        try:
            items = eval(queue)
        except:
            items = {}

        if new_mark - get("queue_mark") > 1.5:
            heading = "[%s] %sKb/s (%.2f%%)" % (len(items), speed, item["percent"])
            self.common.log("Updating %s - %s - %s" % (heading, self.common.makeUTF8(filename), progress), 2)
            params["queue_mark"] = new_mark

        if self.xbmc.Player().isPlaying() and self.xbmc.getCondVisibility("VideoPlayer.IsFullscreen"):
            if self.dialog:
                self.dialog.close()
                self.dialog = ""
        else:
            if not self.dialog:
                self.dialog = DialogDownloadProgress.DownloadProgress()
                self.dialog.create(self.language(201), "")

            if item["total_size"] > 0:
                heading = "[%s] %s - %.2f%%" % (len(items), self.language(202), item["percent"])
            else:
                heading = "[%s] %s - %s" % (len(items), self.language(202), progress)

            if iget("Title"):
                self.dialog.update(percent=item["percent"], heading=heading, label=iget("Title"))
            else:
                self.dialog.update(percent=item["percent"], heading=heading, label=filename)

    #============================= Download Queue =================================
    def _getNextItemFromQueue(self):
        if self.cache.lock("SimpleDownloaderQueueLock"):
            items = []

            queue = self.cache.get("SimpleDownloaderQueue")
            self.common.log("queue loaded : " + repr(queue))

            if queue:
                try:
                    items = eval(queue)
                except:
                    items = False

                item = {}
                if len(items) > 0:
                    item = items[0]
                    self.common.log("returning : " + item[0])

                self.cache.unlock("SimpleDownloaderQueueLock")
                if items:
                    return item
                else:
                    return False
            else:
                self.common.log("Couldn't aquire lock")

    def _addItemToQueue(self, filename, params={}):
        if self.cache.lock("SimpleDownloaderQueueLock"):

            items = []
            if filename:
                queue = self.cache.get("SimpleDownloaderQueue")
                self.common.log("queue loaded : " + repr(queue))

                if queue:
                    try:
                        items = eval(queue)
                    except:
                        items = []

                append = True
                for index, item in enumerate(items):
                    (item_id, item) = item
                    if item_id == filename:
                        append = False
                        del items[index]
                        break

                if append:
                    items.append((filename, params))
                    self.common.log("Added: " + filename + " to queue - " + str(len(items)))
                else:
                    items.insert(1, (filename, params))
                    self.common.log("Moved " + filename + " to front of queue. - " + str(len(items)))

                self.cache.set("SimpleDownloaderQueue", repr(items))

                self.cache.unlock("SimpleDownloaderQueueLock")
                self.common.log("Done")
        else:
            self.common.log("Couldn't lock")

    def _removeItemFromQueue(self, filename):
        if self.cache.lock("SimpleDownloaderQueueLock"):
            items = []

            queue = self.cache.get("SimpleDownloaderQueue")
            self.common.log("queue loaded : " + repr(queue))

            if queue:
                try:
                    items = eval(queue)
                except:
                    items = []

                for index, item in enumerate(items):
                    (item_id, item) = item
                    if item_id == filename:
                        del items[index]
                        self.cache.set("SimpleDownloaderQueue", repr(items))
                        self.common.log("Removed: " + filename + " from queue")

                self.cache.unlock("SimpleDownloaderQueueLock")
                self.common.log("Done")
            else:
                self.common.log("Exception")

    def movieItemToPosition(self, filename, position):
        if position > 0 and  self.cache.lock("SimpleDownloaderQueueLock"):

            items = []
            if filename:
                queue = self.cache.get("SimpleDownloaderQueue")
                self.common.log("queue loaded : " + repr(queue))

                if queue:
                    try:
                        items = eval(queue)
                    except:
                        items = []

                    self.common.log("pre items: %s " % repr(items))
                    for index, item in enumerate(items):
                        (item_id, item) = item
                        if item_id == filename:
                            print "FOUND ID"
                            del items[index]
                            items = items[:position] + [(filename, item)] + items[position:]
                            break
                    self.common.log("post items: %s " % repr(items))

                    self.cache.set("SimpleDownloaderQueue", repr(items))

                    self.cache.unlock("SimpleDownloaderQueueLock")
                    self.common.log("Done")
        else:
            self.common.log("Couldn't lock")

    def isRTMPInstalled(self):
        basic_args = ["rtmpdump", "-V"]

        try:
            p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()[1]
            return output.find("RTMPDump") > -1
        except:
            return False

    def isVLCInstalled(self):
        basic_args = ["vlc", "--version"]

        try:
            p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()[0]
            self.common.log(repr(output))
            return output.find("VLC") > -1
        except:
            return False

    def isMPlayerInstalled(self):
        basic_args = ["mplayer"]

        try:
            p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()[0]
            self.common.log(repr(output))
            return output.find("MPlayer") > -1
        except:
            return False

    def _run_async(self, func, *args, **kwargs):
        from threading import Thread
        worker = Thread(target=func, args=args, kwargs=kwargs)
        self.__workersByName[worker.getName()] = worker
        worker.start()
        return worker

    # Shows a more user-friendly notification
    def _showMessage(self, heading, message):
        self.xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % (heading, self.common.makeUTF8(message), self.notification_length))