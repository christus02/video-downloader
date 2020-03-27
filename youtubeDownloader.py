#!/usr/bin/python3

from __future__ import unicode_literals
import youtube_dl
import logging
import os

class youtubeDownloader:
    '''
    Class to download YouTube Videos
    '''

    def __init__(self):
        # create logger with 'downloader'
        logger = logging.getLogger('downloader')
        logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.FileHandler('/var/log/downloader/youtubeDownloader.log')
        fh.setLevel(logging.DEBUG)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

        # Add logger to Object
        self.logger = logger

        self.sTime = None
        self.eTime = None
        self.url = None
        self.uuid = None
        
        self.outputLocation = os.environ.get('HOME') + '/Storage/YouTubeDownloads/'
        self.outputTemplate = os.environ.get('HOME') + '/Storage/YouTubeDownloads/%(title)s.%(ext)s'    

        self.ydlOpts = {
            'logger': self.logger,
            'progress_hooks': [self.progress],
            'outtmpl': self.outputTemplate,
            'noplaylist':True,
        }

    def download(self, url, sTime=None, eTime=None, onlyAudio=False, downloadPath=None):
        '''
        Function to download the Video and store in the specified location
        '''

        if self.url == None:
            self.url = url

        # Add support for only Start Time or End Time
        if ((sTime is not None) and (eTime is not None)):
            self.sTime = sTime
            self.eTime = eTime
            self.ydlOpts['postprocessor_args'] = ["-ss", str(self.sTime), "-to", str(self.eTime)]
            #self.ydlOpts['format'] = 'bestvideo[ext=mp4]/best[ext=mp4]/best'

        if onlyAudio:
            self.logger.debug("Audio Only Option Selected")
            self.ydlOpts['format'] = 'bestaudio/best'
            self.ydlOpts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        if downloadPath is not None:
            self.ydlOpts['outtmpl'] = downloadPath + '%(title)s.%(ext)s'

        with youtube_dl.YoutubeDL(self.ydlOpts) as ydl:
            self.logger.debug("The Output Template is "+str(self.ydlOpts['outtmpl']))
            ydl.download([self.url])

            # Generate the Filename 
            videoInfo = ydl.extract_info(self.url, download=False)
            self.filename = ydl.prepare_filename(videoInfo)

    def progress(self, d):
        if d['status'] == 'downloading':
            self.logger.debug("Downloading the video, please wait ...")
        if d['status'] == 'error':
            self.logger.debug("There is an error when downloading the video. Please try again. ")
        if d['status'] == 'finished':
            self.logger.debug('Done downloading, now converting ...')

    def getVideoInfo(self, url):
        '''
        Function to get Info about the Video
        '''

        if self.url == None:
            self.url = url

        with youtube_dl.YoutubeDL(self.ydlOpts) as ydl:
            self.videoInfo = ydl.extract_info(self.url, download=False)
            self.videoURL = self.videoInfo.get("url", None)
            self.videoId = self.videoInfo.get("id", None)
            self.videoTitle = self.videoInfo.get('title', None)
            self.videoThumbnail = self.videoInfo.get("thumbnail", None)
            self.videoDescription = self.videoInfo.get("description", None)
            self.videoDuration = self.videoInfo.get("duration", None)

