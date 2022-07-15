
# check to see if this is the main thread of execution
import string
import threading
import time
import datetime
import random

import cv2
import flask_mail
import mediapipe as mp
from flask import render_template, Response, Flask, request, session, redirect, g
import numpy as np
import os
from PIL import Image

import settings
from database import DBOperator
from echarts import date_count, leida
from globalVarible import setfileInOperating
from redisOp import redisOperator
from videoAlgrithom import image_to_web, faceTraining, video, reviewVideoToWeb, readLog, singleDataEntry, delYml, \
    makeReviewVideo, haveVideo

app=Flask(__name__)
app.config.from_object(settings)
mail_obj=flask_mail.Mail(app)
db=DBOperator()
red=redisOperator()
detector=faceTraining()


@app.route("/videoRealTime")
def videoRealTime():
    if g.userName is None:
        return redirect('/')
    if g.userName=='admin':
        return render_template("superUser/videoRealTime.html")
    else:
        return render_template("user/videoRealTime.html",userName=g.userName)

@app.route("/video_play")
def video_play():
    return Response(image_to_web(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.before_request
def setGlobal():
    g.userName=None
    if 'userName' in session:
        g.userName=session['userName']
    g.time = session.get('time')
    g.locate = session.get('locate')

@app.route('/',methods=['POST','GET'])
def Login():
    msg=None
    if request.method=='POST':
        userName=request.form.get('userName')
        password=request.form.get('password')
        print(userName,password)
        if userName=='admin':
            if password=='123456':
                session['userName']='admin'
                return redirect('/videoRealTime')
            else:
                msg="您的账号或密码有误"
        else:
            if(db.checkPassword(userName,password)):
                session['userName']=userName
                return redirect('/selfInformation')
            else:
                msg="您的账号或密码有误"
    return render_template("Login.html",msg=msg)

@app.route('/userCenter',methods=['GET'])
def userCenter():
    if not g.userName:
        return redirect('/')
    msg=None
    searchName=request.args.get('partOfUserName')
    #print(searchName)
    if searchName:
        userList=db.searchUser(searchName)
        #print(userList)
        if len(userList)==0:
            msg="sorry we didnt find any information"
    else:
        userList=db.selectUser()
    return render_template('superUser/userCenter.html',userList=userList,msg=msg)

@app.route('/delUser',methods=['GET'])
def delUser():
    #删除用户
    #之后重定向至video_start
    userName=request.args.get('userName')
    print(userName)
    db.deleteUser(userName)
    try:
        os.remove("static/profile/"+userName)
        setfileInOperating(userName)
        delYml(userName)
    except:
        print("no picture")
    return redirect('/userCenter')

@app.route('/addUser',methods=['GET','POST'])
def addUser():
    if g.userName!='admin':
        return redirect('/')
    msg=None
    if request.method == 'POST':
        userName = request.form.get('userName')
        password = request.form.get('pwd')
        name = request.form.get('name')
        level = request.form.get('level')
        email=request.form.get('theEmail')
        imgData=request.files['image']
        # 查询所有用户
        if db.haveUser(userName):
            msg="已存在该账号"
            return render_template('superUser/addUser.html', msg=msg)
        db.addUser(userName,password,name,level,email)
        imgName=imgData.filename
        suffix=imgName.split(".")[1]
        os.mkdir("static/profile/" +userName)
        path = "static/profile/" +userName+'/1.'+ userName+'.'+suffix
        imgData.save(path)
        setfileInOperating(userName)
        singleDataEntry(userName,detector)
        return redirect('/userCenter')
    return render_template('superUser/addUser.html', msg=msg)

@app.route('/selfInformation', methods=['POST','GET'])
def selfInformation():
    #显示个人信息并提供修改密码
    if g.userName is None:
        return
    msg=None
    informationList=db.getUserInformation(g.userName)
    if request.method == 'POST':
        password = request.form.get('pwd')
        repassword = request.form.get('oldPwd')
        if db.checkPassword(g.userName,repassword):
            db.changePassword(g.userName, password)
            msg="修改成功"
        else:
            msg="密码错误"
    return render_template('user/selfInformation.html',msg=msg,userName=g.userName,userList=informationList)

@app.route('/setUserLevel',methods=['GET'])
def setUserLevel():
    userName=request.args.get('userName')
    level=request.args.get('level')
    db.setLevel(userName,level)
    return redirect('/userCenter')

@app.route('/logOut',methods=['GET'])
def logOut():
    session.pop('userName',None)
    return redirect('/')

@app.route("/video_review_start")
def video_review_start():
    print(str(g.time)+"  shit")
    return Response(reviewVideoToWeb(g.time), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/videoReview")
def videoReview():
    if g.userName != 'admin':
        return redirect('/')
    locate=request.args.get('locate')
    iTime=request.args.get('time')
    LogList=readLog()
    #print()
    if locate is None or iTime is None:
        return render_template('superUser/videoReview.html',haveVideo=None,LogList=LogList)
    else:
        iTime = int(iTime.replace("-", "").replace(" ", "").replace(":", "").replace("'", ""))
        session['time']=iTime
        session['locate']=locate
        nowTime=int(str(datetime.datetime.now())[0:19].replace(" ", "").replace("-", "").replace(":", ""))
        if nowTime-iTime<40:
            return render_template('superUser/videoReview.html', haveVideo=False, LogList=LogList,loading='your video is loading')
        if not haveVideo(iTime):
            makeReviewVideo(iTime,locate)
        return render_template('superUser/videoReview.html',haveVideo=True,LogList=LogList)


@app.route('/statistic')
def statistic():
    #画出相关图像并以模板渲染
    if g.userName!='admin':
        return redirect('/')
    data = {
        'daily_count_line':date_count(),
        'count_leida':leida(),
    }
    return render_template('superUser/statistic.html',data=data)

def send_async_email(msg):
        with app.app_context():
            mail_obj.send(msg)

@app.route('/emailLogin',methods=['GET','POST'])
def emailLogin():
    if request.method=='GET':
        email=request.args.get('email')
        if email is None:
            return render_template('Email.html')
        if(db.checkEmail(email)):
            str = ""
            for i in range(6):
                ch = chr(random.randrange(ord('0'), ord('9') + 1))
                str += ch
            red.setValue(email,str)
            recipients=[]
            recipients.append(email)
            msgobject = flask_mail.Message(subject="您的验证码", body="欢迎来到入侵检测系统,验证码是 " + str, sender='2462546443@qq.com',
                                           recipients=recipients)
            send_async_email(msgobject)
            return render_template('Email.html',email=email,msg='已发送')
        return render_template('Email.html',msg='错误邮箱')
    else:
        email=request.form['email']
        code=request.form['code']
        print(email,code)
        if code is None or email is None:
            return render_template('Email.html',msg='请填写邮箱和验证码后再提交')
        else:
            if(red.Judge(email,code)):
                session['userName']=db.getUserNameByEmail(email)
                return redirect('/selfInformation')
            return render_template('Email.html',msg='验证码错误')


if __name__ == '__main__':     # construct the argument parser and parse command line arguments
    t=video(detector,2)
    t.daemon=True
    t.start()
    app.run(threaded=True,host='0.0.0.0')