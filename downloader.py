#!/usr/bin/python3
from flask import Flask, request, Response, render_template, send_file, redirect, url_for, flash
import flask_login
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
import hashlib

app = Flask(__name__)

# Configs required for mySQL connection
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')

# To maintain sessions via cookies
app.config['SECRET_KEY'] = b')\xcaN.7\x05\x17\x08w\x91\x03\x19\xbfh\x8e\xf8'

UUID = None
BASE_PATH = os.environ.get('HOME') + '/Storage/YouTubeDownloads/'
BASE_PATH_UUID = BASE_PATH

mysql = MySQL(app)

#Flask Login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(userid):

    user = User()
    user.id = userid
    return user

@login_manager.request_loader
def request_loader(request):

    userid = request.form.get('userid') # User inputted
    passwd = request.form.get('password') # User inputted

    user = User()
    user.id = userid

    #Check if User exists
    if not dbhandler.checkIfUserExists(mysql, userid):
        return #User not existing
    else:
        inputPasswordHash = hashPassword(passwd)
        userPasswordHash = dbhandler.retrievePasswordHash(mysql, userid)

    user.is_authenticated = inputPasswordHash == userPasswordHash

    return user


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

def hashPassword(passwd, digest='sha1'):
    '''
    Function to do a SHA1 Hash of a string
    '''

    hashed = None
    if digest == 'sha1':
        hashed = hashlib.sha1(passwd.encode())

    return hashed.hexdigest()


# Views
@app.route("/", methods = ['POST', 'GET'])
def landing():
    return render_template('index.html', title='Free Video Downloader', total_downloaded=dbhandler.getTotalDownloaded(mysql), trimmed_downloaded=dbhandler.getCroppedDownloaded(mysql), only_audio_downloaded=dbhandler.getOnlyAudioDownloaded(mysql))

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

        try:
            dl.getVideoInfo(videoUrl)

            if dl.videoDuration is None:
                dl.videoDuration = 0
                dl.videoInfo['duration'] = 0

            dbhandler.writeVideoInfo(mysql,UUID, dl.videoInfo)
            return render_template('videodetails.html', thumbnail=dl.videoThumbnail, title=dl.videoTitle, duration=str(datetime.timedelta(seconds=int(dl.videoDuration))), uuid=UUID)
        except Exception as e:
            dbhandler.writeError(mysql, UUID, str(e))
            return render_template('error.html', error_message="There was an error when downloading the Video. The Video may not be available for downloading or may require Authentication. Please try with a different Video")

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

    try:
        dl.download(video, sTime, eTime, onlyaudio, BASE_PATH_UUID)
        filename = glob.glob(BASE_PATH_UUID+'*')
        filename = filename[0]
        dbhandler.writeDownloadSuccess(mysql,uuid,BASE_PATH_UUID,filename)
        return send_file(filename, as_attachment=True)
    except Exception as e:
        dbhandler.writeError(mysql, uuid, str(e))
        return render_template('error.html', error_message="There was an error when downloading the Video. The Video may not be available for downloading or may require Authentication. Please try with a different Video")


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


@app.route("/maintenance", methods = ['GET'])
def maintenance():
    return render_template('maintenance.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'GET':
        # If logged in, then logout the user
        if flask_login.current_user.is_authenticated:
            return redirect(url_for('logout'))
        else:
            return render_template('login.html')

    userid = request.form.get('userid') # User inputted
    passwd = request.form.get('password') # User inputted

    #Check if User exists
    if not dbhandler.checkIfUserExists(mysql, userid):
        return render_template('error.html', error_message="User Does not Exist. Please refrain trying again if you are not a valid user")
    else:
        inputPasswordHash = hashPassword(passwd)
        userPasswordHash = dbhandler.retrievePasswordHash(mysql, userid)
        if inputPasswordHash == userPasswordHash:
            user = User()
            user.id = userid
            flask_login.login_user(user)
            return redirect(url_for('reportsSuccessfulDownloads'))
        else:
            return render_template('error.html', error_message="Wrong Credentials. Please refrain trying again if you are not a valid user")


@app.route('/reports/successfuldownloads')
@flask_login.login_required
def reportsSuccessfulDownloads():
    successfulDownloads = dbhandler.reportSuccessfulDownloads(mysql)
    tableStr = ""
    for row in successfulDownloads:
        rowStr = ""
        #date, title, actual_link, downloaded_file_name, trimmed, only_audio, duration
        rowStr = "<tr><td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> </tr>" % (str(row[0]),str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[5]),str(row[6]))
        tableStr = tableStr + rowStr

    return render_template('successfuldownloads.html', table_row=tableStr)


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('landing'))


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('error.html', error_message="Unauthorized Access")

