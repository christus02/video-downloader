#!/usr/bin/python3
from flask import Flask, request, Response, render_template, send_file, redirect, url_for
import sys
import os
import time
import subprocess
import shlex
import urllib.parse
import datetime
import uuid
import glob
import os
import MySQLdb # To Escape and unescape strings before inserting to DB
from youtubeDownloader import youtubeDownloader
import dbhandler
from flask_mysqldb import MySQL

app = Flask(__name__)

# Configs required for mySQL connection
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')

UUID = None
BASE_PATH = os.environ.get('HOME') + '/Storage/YouTubeDownloads/'
BASE_PATH_UUID = BASE_PATH

mysql = MySQL(app)

# Utils Functions
def validTimeConverter(time):
    '''
    This Function Converts a time string to datetime object
    '''

    timeformat = "%H:%M:%S"
    try:
        validTime = datetime.datetime.strptime(time, timeformat)
        return validTime
    except:
        return None

def sanitizeInput(field):
    '''
    Function to sanitize the input to be written into the DB
    '''
    
    # TODO SQL Injection checks

    # For now trimming the string to 10K characters
    return field[:10000]


@app.route("/")
def landing():

    return render_template('index.html', title='Free Video Downloader')

@app.route("/videodetails", methods = ['POST', 'GET'])
def getVideoDetails():
    '''
    Function to get the Details of the Video.
    This function first writes the inputs to the DB and then fetches the video details
    '''

    global UUID
    global dl
    global BASE_PATH_UUID
    global BASE_PATH
    UUID = str(uuid.uuid4())
    #Create a directory in the downloads folder with this uuid
    BASE_PATH_UUID = BASE_PATH + UUID + '/'
    os.mkdir(BASE_PATH_UUID)

    if request.method == "GET":
        return redirect(url_for('landing'))

    if request.method == "POST":
        inputError = False

        try:
            videoUrl = request.form.get('video')
        except:
            inputError = True
            return render_template('error.html', error_message="Please enter the Video URL")
        if (videoUrl == ""):
            return render_template('error.html', error_message="Please enter the Video URL")

        dbhandler.writeActualLink(mysql,videoUrl, UUID)

        dl = youtubeDownloader()
        dl.getVideoInfo(videoUrl)

        if dl.videoDuration is None:
            dl.videoDuration = 0
            dl.videoInfo['duration'] = 0

        dbhandler.writeVideoInfo(mysql,UUID, dl.videoInfo)

        return render_template('videodetails.html', thumbnail=dl.videoThumbnail, title=dl.videoTitle, duration=str(datetime.timedelta(seconds=int(dl.videoDuration))), uuid=UUID)

@app.route("/download", methods = ['POST', 'GET'])
def downloadVideo():

    global dl, BASE_PATH_UUID
    uuid = request.form.get('uuid')

    # Check if already downloaded
    alreadyDownloaded = dbhandler.checkDownloaded(mysql, uuid)
    if alreadyDownloaded:
        return redirect(url_for('landing'))

    if request.form.get('trim'):

            # Validate start time and end time
            videoDuration = dbhandler.getDuration(mysql, uuid)

            sTime = request.form.get('stime')
            eTime = request.form.get('etime')

            sTimeValid = validTimeConverter(sTime)
            eTimeValid = validTimeConverter(eTime)

            if sTimeValid is None:
                return render_template('error.html', error_message="Please Enter the Start Time in the Format of HH:MM:SS")
            if eTimeValid is None:
                return render_template('error.html', error_message="Please Enter the End Time in the Format of HH:MM:SS")

            # Validation of Start Time and End Time
            sTimeSplit = sTime.split(":")
            sTimeSeconds = int(datetime.timedelta(hours=int(sTimeSplit[0]),minutes=int(sTimeSplit[1]),seconds=int(sTimeSplit[2])).total_seconds())

            eTimeSplit = eTime.split(":")
            eTimeSeconds = int(datetime.timedelta(hours=int(eTimeSplit[0]),minutes=int(eTimeSplit[1]),seconds=int(eTimeSplit[2])).total_seconds())

            if sTimeSeconds > videoDuration:
                return render_template('error.html', error_message="Please check your Start Time. It is higher than the Video Duration")

            if eTimeSeconds > videoDuration:
                return render_template('error.html', error_message="Please check your End Time. It is higher than the Video Duration")

            if sTimeSeconds > eTimeSeconds:
                return render_template('error.html', error_message="Please check your Start Time and End Time")

    else:
        sTime = None
        eTime = None

    dbhandler.writeTime(mysql,uuid, sTime, eTime)

    onlyaudio = False
    if request.form.get('onlyaudio'):
        onlyaudio = True
        dbhandler.writeAudioOnly(mysql,uuid)

    video = dbhandler.getActualLinkFromUUID(mysql,uuid)
    dl.download(video, sTime, eTime, onlyaudio, BASE_PATH_UUID)
    filename = glob.glob(BASE_PATH_UUID+'*')
    filename = filename[0]
    dbhandler.writeDownloadSuccess(mysql,uuid,BASE_PATH_UUID,filename)

    return send_file(filename, as_attachment=True)

@app.route("/issues", methods = ['POST', 'GET'])
def issues():

    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if (name == "" or email == "" or subject == "" or message == ""):
            return render_template('error.html', error_message="All fields are mandatory. Please fill them")

        data = dict()
        data['name'] = sanitizeInput(name)
        data['email'] = sanitizeInput(email)
        data['subject'] = sanitizeInput(subject)
        data['message'] = sanitizeInput(message)

        dbhandler.writeIssue(mysql, data)
        
        return render_template('acknowledge.html')

    if request.method == "GET":
        return render_template('feedback.html', title='Free Video Downloader')

@app.route("/featurerequest", methods = ['POST', 'GET'])
def featureRequest():

    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if (name == "" or email == "" or subject == "" or message == ""):
            return render_template('error.html', error_message="All fields are mandatory. Please fill them")

        data = dict()
        data['name'] = sanitizeInput(name)
        data['email'] = sanitizeInput(email)
        data['subject'] = sanitizeInput(subject)
        data['message'] = sanitizeInput(message)

        dbhandler.writeFeatureRequest(mysql, data)
        
        return render_template('acknowledge.html')

    if request.method == "GET":
        return render_template('featurerequest.html', title='Free Video Downloader')

