#!/usr/bin/python3

import MySQLdb # To Escape and unescape strings before inserting to DB
from flask_mysqldb import MySQL
import os


# Globals
global DB_TABLE, DB_TABLE_ISSUES, DB_TABLE_FEATURE_REQUEST, DB_TABLE_USERS
DB_TABLE = os.environ.get('MYSQL_DB_TABLE')
DB_TABLE_ISSUES = os.environ.get('MYSQL_DB_TABLE_ISSUES')
DB_TABLE_FEATURE_REQUEST = os.environ.get('MYSQL_DB_TABLE_FEATURE_REQUEST')
DB_TABLE_USERS = os.environ.get('MYSQL_DB_TABLE_USERS')

# Functions for DB
def writeActualLink(mysql,videoUrl, uuid):
    '''
    This Function writes the basic defaults into the DB Table
    '''

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO %s(actual_link,date,uuid) VALUES ('%s',NOW(),'%s')" % (DB_TABLE, videoUrl, uuid))
    mysql.connection.commit()

    # Set Downloaded to false
    cur = mysql.connection.cursor()
    cur.execute("UPDATE %s SET downloaded = false WHERE uuid = '%s'" % (DB_TABLE, uuid))
    mysql.connection.commit()

    cur.close()
    return True

def writeTime(mysql,uuid, sTime, eTime):

    cur = mysql.connection.cursor()

    if sTime is not None:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET start_time = '%s' WHERE uuid = '%s'" % (DB_TABLE, sTime, uuid))
        cur.execute("UPDATE %s SET trimmed = true WHERE uuid = '%s'" % (DB_TABLE, uuid))
        mysql.connection.commit()

    if eTime is not None:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET end_time = '%s' WHERE uuid = '%s'" % (DB_TABLE, eTime, uuid))
        mysql.connection.commit()

    cur.close()
    return True

def writeAudioOnly(mysql,uuid):

    cur = mysql.connection.cursor()
    cur.execute("UPDATE %s SET only_audio = true WHERE uuid = '%s'" % (DB_TABLE, uuid))
    mysql.connection.commit()
    cur.close()
    return True

def writeDownloadSuccess(mysql,uuid,file_location,filename):

    cur = mysql.connection.cursor()
    cur.execute("UPDATE %s SET downloaded = true WHERE uuid = '%s'" % (DB_TABLE, uuid))
    mysql.connection.commit()

    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET downloaded_file_name = '%s' WHERE uuid = '%s'" % (DB_TABLE, filename, uuid))
        mysql.connection.commit()
    except:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET downloaded_file_name = 'UNSUPPORTED_LANGUAGE' WHERE uuid = '%s'" % (DB_TABLE, uuid))
        mysql.connection.commit()

    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET downloaded_location = '%s' WHERE uuid = '%s'" % (DB_TABLE, file_location, uuid))
        mysql.connection.commit()
    except:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET downloaded_location = 'UNSUPPORTED_LANGUAGE' WHERE uuid = '%s'" % (DB_TABLE, uuid))
        mysql.connection.commit()

    cur.close()
    return True

def checkDownloaded(mysql, uuid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT downloaded FROM %s WHERE uuid = '%s'" % (DB_TABLE, uuid))
    downloaded = cur.fetchone()
    cur.close()
    if downloaded[0] == 1:
        return True
    else:
        return False

def getDuration(mysql, uuid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT duration FROM %s WHERE uuid = '%s'" % (DB_TABLE, uuid))
    duration = cur.fetchone()
    cur.close()
    return int(duration[0])

def getActualLinkFromUUID(mysql,uuid):

    cur = mysql.connection.cursor()
    cur.execute("SELECT actual_link FROM %s WHERE uuid = '%s'" % (DB_TABLE, uuid))
    actual_link = cur.fetchone()
    cur.close()
    return actual_link[0]

def getTotalDownloaded(mysql):

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM %s WHERE downloaded = 1" % (DB_TABLE))
    total_downloaded = cur.fetchone()
    cur.close()
    return total_downloaded[0]


def reportSuccessfulDownloads(mysql):
    cur = mysql.connection.cursor()
    cur.execute("SELECT date, title, actual_link, downloaded_file_name, trimmed, only_audio, duration FROM %s WHERE downloaded = 1" % (DB_TABLE))
    successfulDownloads = cur.fetchall()
    cur.close()
    return successfulDownloads

def getCroppedDownloaded(mysql):

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM %s WHERE downloaded = 1 and trimmed = 1" % (DB_TABLE))
    cropped_downloaded = cur.fetchone()
    cur.close()
    return cropped_downloaded[0]

def getOnlyAudioDownloaded(mysql):

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM %s WHERE downloaded = 1 and only_audio = 1" % (DB_TABLE))
    only_audio_downloaded = cur.fetchone()
    cur.close()
    return only_audio_downloaded[0]

def writeVideoInfo(mysql,uuid, videoInfo):
    '''
    Function to write Video Info to the DB
    '''
 
    videoId = videoInfo.get("id", None)
    thumbnail = videoInfo.get("thumbnail", None)
    description = videoInfo.get("description", None)
    title = videoInfo.get("title", None)
    duration = videoInfo.get("duration", None)

    if videoId is not None:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET unique_id = '%s' WHERE uuid = '%s'" % (DB_TABLE, videoId, uuid))
        mysql.connection.commit()

    if thumbnail is not None:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET thumbnail = '%s' WHERE uuid = '%s'" % (DB_TABLE, thumbnail, uuid))
        mysql.connection.commit()

    if title is not None:
        try:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE %s SET title = '%s' WHERE uuid = '%s'" % (DB_TABLE, MySQLdb.escape_string(title).decode(), uuid))
            mysql.connection.commit()
        except:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE %s SET title = 'UNSUPPORTED LANGUAGE' WHERE uuid = '%s'" % (DB_TABLE, uuid))
            mysql.connection.commit()

    if duration is not None:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE %s SET duration = '%d' WHERE uuid = '%s'" % (DB_TABLE, int(duration), uuid))
        mysql.connection.commit()

    cur.close()
    return True

def writeIssue(mysql, data):
    '''
    Function to write the bug report
    '''

    cur = mysql.connection.cursor()
    if 'uuid' in data:
        cur.execute("INSERT INTO %s(date,name,email,subject,message,uuid) VALUES (NOW(),'%s','%s','%s','%s','%s')" % (DB_TABLE_ISSUES, data['name'],data['email'],data['subject'],data['message'],data['uuid']))
    else:
        cur.execute("INSERT INTO %s(date,name,email,subject,message) VALUES (NOW(),'%s','%s','%s','%s')" % (DB_TABLE_ISSUES, data['name'],data['email'],data['subject'],data['message']))
    mysql.connection.commit()
    cur.close()

def writeFeatureRequest(mysql, data):
    '''
    Function to write the Feature Request
    '''

    cur = mysql.connection.cursor()
    if 'uuid' in data:
        cur.execute("INSERT INTO %s(date,name,email,subject,message,uuid) VALUES (NOW(),'%s','%s','%s','%s','%s')" % (DB_TABLE_FEATURE_REQUEST, data['name'],data['email'],data['subject'],data['message'],data['uuid']))
    else:
        cur.execute("INSERT INTO %s(date,name,email,subject,message) VALUES (NOW(),'%s','%s','%s','%s')" % (DB_TABLE_FEATURE_REQUEST, data['name'],data['email'],data['subject'],data['message']))
    mysql.connection.commit()
    cur.close()

def checkIfUserExists(mysql, userid):
    '''
    Function to check if a user exists in our database;
    '''

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(userid) FROM %s WHERE userid='%s'" % (DB_TABLE_USERS, userid))
    userStatus = cur.fetchone()[0]
    cur.close()
    if int(userStatus) == 1:
        return True
    else:
        return False

def retrievePasswordHash(mysql, userid):
    '''
    Function to retrieve Password Hash for a specific User
    '''
    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM %s WHERE userid='%s'" % (DB_TABLE_USERS, userid))
    passwordHash = cur.fetchone()[0]
    cur.close()
    return passwordHash









