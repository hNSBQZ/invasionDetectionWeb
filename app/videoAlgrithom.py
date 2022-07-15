# check to see if this is the main thread of execution
import threading
import time
import datetime

import cv2
import mediapipe as mp
from flask import render_template, Response, Flask
import numpy as np
import os
from PIL import Image

import fcntl
from database import DBOperator
from globalVarible import setfileInOperating,getfileInOperating

outputFrame=None
lock=threading.Lock()
lock1=threading.Lock()
detector=None


class FaceDetector():
    def __init__(self, minDetectionCon=0.5):#初始化人脸识别模型
        self.minDetectionCon = minDetectionCon
        self.mpFaceDetection = mp.solutions.face_detection
        self.mpDraw = mp.solutions.drawing_utils
        self.faceDetection = self.mpFaceDetection.FaceDetection(model_selection=1, min_detection_confidence=0.8)

    def findFaces(self, img, draw=True):#找人脸
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)#将图像改成RGB格式
        self.results = self.faceDetection.process(imgRGB)#获取人脸特征点坐标以及人脸识别框坐标
        # print(self.results)
        bboxs = []
        if self.results.detections:
            for id, detection in enumerate(self.results.detections):#循环遍历将坐标存储，id是摄像头参数（0或1）
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, ic = img.shape
                bbox = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                       int(bboxC.width * iw), int(bboxC.height * ih)
                bboxs.append([id, bbox, detection.score])
                #print(id)
        return img, bboxs

class video(threading.Thread):
    def __init__(self,detector,m):
        threading.Thread.__init__(self)
        self.camera=cv2.VideoCapture('rtmp://117.78.8.76:1935/test/demo')
        #self.camera=cv2.VideoCapture(0)
        self.T1=time.time()
        self.fourcc = cv2.VideoWriter_fourcc('X', 'V', 'I', 'D')
        timeStr = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        path='video/'+timeStr+".avi"
        self.video_out=cv2.VideoWriter(path, self.fourcc, 5, (1280, 720))
        self.mincredit = []
        self.waringtimes = 0
        self.lunshu = 0
        self.names = []
        self.Messagetimewrong = 0
        self.Messagetimeright = 0
        self.Warningsms = 0
        self.img_copy = []
        self.img_copy2 = []
        self.img = []
        self.pTime = 0
        self.detector=detector
        self.m=m
        self.locate=0
        self.level=0
        self.db=DBOperator()
        self.ix=0
        self.iy=0
        self.nameInUsing=None

    def run(self):
        global outputFrame,lock
        while True:
            self.nameInUsing=getfileInOperating()
            success,self.img=self.camera.read()
            if not success:
                break
                print('No camera')
            else:
                self.img_copy = self.gaibian(self.img, self.ix, self.iy)  # 右半部分>=2
                frame = self.face_check(self.img_copy, self.m, self.detector)
                self.img_copy2 = self.gaibian2(self.img, self.ix, self.iy)  # 左半部分=3
                frame2 = self.face_check2(self.img_copy2, self.m, self.detector)
                cTime = time.time()
                if (cTime - self.pTime) != 0:
                    fps = 1 / (cTime - self.pTime)
                    self.pTime = cTime
                else:
                    fps = 1 / cTime
                    self.pTime = cTime

                cv2.putText(self.img, f'FPS:{int(fps)}', (20, 70), cv2.FONT_HERSHEY_PLAIN, 3, (0, 255, 0), 2)#将fps信息写在图片上

                if frame is None and frame2 is None:
                    self.saveVideoToDisk(self.img)
                    with lock:
                        outputFrame=self.img.copy()
                else:
                    self.chongxie(frame, self.img, self.ix, self.iy)
                    self.chongxie2(frame2, self.img, self.ix, self.iy)
                    cv2.rectangle(self.img, (self.ix + 720, self.iy), (self.ix + 1440, self.iy + 1280), color=(0, 255, 0), thickness=2)
                    cv2.rectangle(self.img, (self.ix, self.iy), (self.ix + 720, self.iy + 1280), color=(0, 0, 255), thickness=2)
                    self.saveVideoToDisk(self.img)
                    with lock:
                        outputFrame=self.img.copy()

    def saveVideoToDisk(self,frame):
        self.video_out.write(frame)
        self.locate+=1
        if time.time() - self.T1 > 30:
            self.video_out.release()
            TimeStr = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            Path = 'video/'+TimeStr + ".avi"
            self.video_out = cv2.VideoWriter(Path, self.fourcc, 5, (1280, 720))
            self.locate=0
            self.T1 = time.time()

    def face_check(self,img, m, detector):  # 面部智能识别函数
        path='models/'
        fileNames,m=getfiles(path)
        for file in fileNames:  # 循环遍历特征文件
            name = file.split('.')[0]
            if name==self.nameInUsing:
                m-=1
                continue
            recogizer = cv2.face.LBPHFaceRecognizer_create()
            strd = path+file
            recogizer.read(strd)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face, bboxse = detector.findFaces(img)  # 获取置信度
            if bboxse:
                str1 = bboxse[0]
                str2 = str1[1]
                str3 = []
                str4 = []
                for x in range(len(str2)):
                    str3.append(str2[x - 1])
                str4.append(str3)  # 以上是获取图片信息的，不用管
                for h, x, y, w in str4:
                    ids, confidence = recogizer.predict(gray)
                    #print(confidence)
                    if confidence > 80:  # 如果置信分数大于45，报警（可以改，不过不好把握）
                        self.waringtimes += 1  # 遍历值，假如特征文件有6个，且它最后等于6，证明该图片与6个特征文件都没有比对上，则将其判断为陌生人
                        break
                    else:
                        if self.lunshu == 0:  # 如果通过特征文件找到第一个相似的人，则将其信息与置信分数记录下来
                            self.mincredit.append(confidence)
                            self.mincredit.append(x)
                            self.mincredit.append(y)
                            self.mincredit.append(w)
                            self.mincredit.append(h)
                            self.mincredit.append(ids)
                            self.mincredit.append(img)
                            self.mincredit.append(name)
                            self.lunshu += 1
                        else:
                            if confidence < self.mincredit[0]:  # 如果有置信分数更低的，则判断此人为置信分数更低的人，比如这个人跟我比43分，跟小明比33分，则判断他为小明
                                self.mincredit[0] = confidence
                                self.mincredit[1] = x
                                self.mincredit[2] = y
                                self.mincredit[3] = w
                                self.mincredit[4] = h
                                self.mincredit[5] = ids
                                self.mincredit[6] = img
                                self.mincredit[7] = name
                        self.waringtimes = 0
            else:
                return img
        if self.waringtimes == m:  # 如果一个也没比对上，则绘制不认识的人的识别框（红色）
            self.Warningsms += 1  # 短信报警参数，到100短信报警一次。我在这里注释掉了
            print(self.Warningsms)
            if self.Warningsms == 100:
                self.warning()
                self.Warningsms = 0
            img = self.drawWorng(img, x, y, w, h)
        else:
            #print(self.waringtimes)
            level = self.db.selectlevel(self.mincredit[7])
            if len(level) == 0:
                self.mincredit.clear()  # 将所用参数置为0
                self.waringtimes = 0
                self.lunshu = 0
                self.Warningsms += 1
                if self.Warningsms == 100:
                    self.warning()
                    self.Warningsms = 0
                img = self.drawWorng(img, x, y, w, h)
                # print("One  point")
                return img
            grades = level[0]
            for k in grades:
                grade = grades[k]
            if grade >= 2:
                img = self.drawRight(self.mincredit[6], self.mincredit[1], self.mincredit[2], self.mincredit[3], self.mincredit[4], self.mincredit[5],
                                 self.mincredit[7])
            else:
                self.Warningsms += 1  # 短信报警参数，到100短信报警一次。我在这里注释掉了
                if self.Warningsms == 100:
                    self.warning()
                    self.Warningsms = 0
                img = self.drawWorng(img, x, y, w, h)
        self.mincredit.clear()  # 将所用参数置为0
        self.waringtimes = 0
        self.lunshu = 0
        # print("One  point")
        return img

    def face_check2(self,img, m, detector):  # 面部智能识别函数
        path='models/'
        fileNames,m=getfiles(path)
        for file in fileNames:  # 循环遍历特征文件
            name = file.split('.')[0]
            if name == self.nameInUsing:
                m-=1
                continue
            recogizer = cv2.face.LBPHFaceRecognizer_create()
            strd = path+file
            recogizer.read(strd)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face, bboxse = detector.findFaces(img)  # 获取置信度
            if bboxse:
                str1 = bboxse[0]
                str2 = str1[1]
                str3 = []
                str4 = []
                for x in range(len(str2)):
                    str3.append(str2[x - 1])
                str4.append(str3)  # 以上是获取图片信息的，不用管
                for h, x, y, w in str4:
                    ids, confidence = recogizer.predict(gray)
                    print(confidence)
                    if confidence > 80:  # 如果置信分数大于45，报警（可以改，不过不好把握）
                        self.waringtimes += 1  # 遍历值，假如特征文件有6个，且它最后等于6，证明该图片与6个特征文件都没有比对上，则将其判断为陌生人
                        break
                    else:
                        if self.lunshu == 0:  # 如果通过特征文件找到第一个相似的人，则将其信息与置信分数记录下来
                            self.mincredit.append(confidence)
                            self.mincredit.append(x)
                            self.mincredit.append(y)
                            self.mincredit.append(w)
                            self.mincredit.append(h)
                            self.mincredit.append(ids)
                            self.mincredit.append(img)
                            self.mincredit.append(name)
                            self.lunshu += 1
                        else:
                            if confidence < self.mincredit[0]:  # 如果有置信分数更低的，则判断此人为置信分数更低的人，比如这个人跟我比43分，跟小明比33分，则判断他为小明
                                self.mincredit[0] = confidence
                                self.mincredit[1] = x
                                self.mincredit[2] = y
                                self.mincredit[3] = w
                                self.mincredit[4] = h
                                self.mincredit[5] = ids
                                self.mincredit[6] = img
                                self.mincredit[7] = name
                        self.waringtimes = 0
            else:
                return img
        if self.waringtimes == m:  # 如果一个也没比对上，则绘制不认识的人的识别框（红色）
            self.Warningsms += 1  # 短信报警参数，到100短信报警一次。我在这里注释掉了
            #print(self.Warningsms)
            if self.Warningsms == 100:
                self.warning()
                self.Warningsms = 0
            img = self.drawWorng(img, x, y, w, h)
        else:
            level = self.db.selectlevel(self.mincredit[7])
            if len(level)==0:
                self.mincredit.clear()  # 将所用参数置为0
                self.waringtimes = 0
                self.lunshu = 0
                self.Warningsms+=1
                if self.Warningsms == 100:
                    self.warning()
                    self.Warningsms = 0
                img = self.drawWorng(img, x, y, w, h)
                # print("One  point")
                return img
            grades = level[0]
            for k in grades:
                grade = grades[k]
            if grade <3:
                self.Warningsms += 1  # 短信报警参数，到100短信报警一次。我在这里注释掉了
                if self.Warningsms == 100:
                    self.warning()
                    self.Warningsms = 0
                img = self.drawWorng(img, x, y, w, h)
            else:
                img = self.drawRight(self.mincredit[6], self.mincredit[1], self.mincredit[2], self.mincredit[3], self.mincredit[4], self.mincredit[5],
                                 self.mincredit[7])
        self.mincredit.clear()  # 将所用参数置为0
        self.waringtimes = 0
        self.lunshu = 0
        # print("One  point")
        return img

    def warning(self):
        import requests
        content = str("【警报】您的所属区域已经被入侵，请尽快查看视频监控或视频回放确定入侵者身份")
        url = 'https://api.smsbao.com/sms?u=gqshixun&p=48a9534bd386447f97c72c58e07005d2&m=18101079627&c=' + str(content)
        requests = requests.get(url)
        print(requests.content)

    def drawRight(self,img, x, y, w, h, ids, name):  # 识别出是对的人，画出头像框，并写入日志（我给注释掉了）
        cv2.rectangle(img, (x, y), (x + w, y + h), color=(0, 255, 0), thickness=2)
        cv2.circle(img, center=(x + w // 2, y + h // 2), radius=w // 2, color=(0, 255, 0), thickness=2)
        cv2.putText(img, str(name), (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                    (0, 255, 0), 1)
        self.Messagetimeright += 5
        if self.Messagetimeright > 225:
            self.writelog(name)
            self.Messagetimeright = 0
        return img

    def writelog(self,name):  # 将报警时间和内容写入日志
        # 记录不同用户的进入时间和陌生人入侵时间
        # now = str(datetime.datetime.now())[:19].replace(':', '_')
        # 时间也一并传输？
        now = datetime.datetime.now()
        now20 = str(now).split(' ')[0]
        now2 = str(now).split(' ')[1]
        now3 = str(now2).split(':')[2]
        now31 = str(now2).split(':')[0]
        now32 = str(now2).split(':')[1]
        now4 = str(now3).split('.')[0]
        now = str(now20 + ' ' + now31 + '_' + now32 + "_" + now4)
        print(now)
        timesd = now.split()
        with open('log.txt','a') as f:
            fcntl.flock(f.fileno(),fcntl.LOCK_EX)
            f.write(str(now) + ' ' + str(name) +' '+str(self.locate)+'\n')

    def drawWorng(self,img, x, y, w, h):  # 识别出是错的人，画出头像框，并写入日志（我给注释掉了）
        cv2.rectangle(img, (x, y), (x + w, y + h), color=(0, 0, 255), thickness=2)
        cv2.circle(img, center=(x + w // 2, y + h // 2), radius=w // 2, color=(0, 0, 255), thickness=2)
        cv2.putText(img, 'WARING!STRANGER INVASION', (0, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 1)
        self.Messagetimewrong
        self.Messagetimewrong += 5
        if self.Messagetimewrong > 225:
            self.writelog("stranger")
            self.Messagetimewrong = 0
        return img

    def gaibian(self,img, ix0, iy0):
        img2 = img[iy0:iy0 + 1280, ix0 + 720:ix0 + 1440]
        return img2

    def gaibian2(self,img, ix0, iy0):
        img2 = img[iy0:iy0 + 1280, ix0:ix0 + 720]
        return img2

    def chongxie(self,frame, img, ix, iy):
        img[iy:iy + 1280, ix + 720:ix + 1440] = frame

    def chongxie2(self,frame, img, ix, iy):
        img[iy:iy + 1280, ix:ix + 720] = frame


def faceTraining():
    detector=FaceDetector(0.4)
    dataEntrry(detector)
    return detector

def dataEntrry(detector):#调用getImageAndLables函数，将人脸特征提取并写入yml文件中
    path='static/profile/'
    fileNames,m=getfiles(path)
    for file in fileNames:
        newPath = path+file
        faces, ids = getImageAndLables(newPath, detector)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(ids))
        strd = 'models/'+file+'.yml'
        #print(strd)
        recognizer.write(strd)

def getImageAndLables(path, detector):#识别文件夹中的每张图片的人脸，然后将其特征信息，id（比如图片为1.guoqi.jpg的id是1）提取出来
    facesSamples = []
    ids = []
    imagrPaths = [os.path.join(path, f) for f in os.listdir(path)]
    for imagrPath in imagrPaths:
        print(imagrPath)
        cap = cv2.VideoCapture(imagrPath)
        success, frame = cap.read()
        if not success:
            break
        else:
            PIL_img = Image.open(imagrPath).convert('L')
            img_numpy = np.array(PIL_img, 'uint8')
            faces, bboxse = detector.findFaces(frame)
            id = int(os.path.split(imagrPath)[1].split('.')[0])
            str1 = bboxse[0]
            str2 = str1[1]
            str3 = []
            str4 = []
            for i in range(len(str2)):
                str3.append(str2[i - 1])
            str4.append(str3)
            # print(str4)
            for x, y, w, h in str4:
                ids.append(id)
                facesSamples.append(img_numpy)
    # print('id:',id)
    # print('fs:', facesSamples)
    return facesSamples, ids

def singleDataEntry(userName,detector):
    faces, ids = getImageAndLables('static/profile/'+userName, detector)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(ids))
    strd = 'models/' + userName + '.yml'
    # print(strd)
    recognizer.write(strd)
    setfileInOperating(None)

def delYml(userName):
    os.remove('models/'+userName+'.yml')
    setfileInOperating(None)

def getfiles(path):
    filenames=os.listdir(path)
    return filenames,len(filenames)

def image_to_web():
    global outputFrame,lock
    while True:
        with lock:
            if outputFrame is None:
                continue
            ret,buffer=cv2.imencode('.jpg',outputFrame)
            if not ret:
                continue
        frame=buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def readLog() :
    # 返回当天记录中的内容
    date = str(datetime.datetime.now())[:10]
    str1 = ""
    infoList=[]
    with open('log.txt','r') as check:
        fcntl.flock(check.fileno(),fcntl.LOCK_EX)
        while True:
            line=check.readline()
            ck=line[0:10]
            if ck==date:
                s=line.replace('\n', '').replace('_', ':')
                str_time = s.split(" ")[0] + " " + s.split(" ")[1]
                str_people = s.split(" ")[2]
                str_locate = s.split(" ")[3]

                str_dict = '{"invasionTime":"' + str_time \
                           + '","invasionPeople":"' + str_people \
                           + '","videoLocation":"' + str_locate + '"}'
                dict = eval(str_dict)
                infoList.append(dict)
            elif ck:
                continue
            else:
                break
    return infoList

def makeReviewVideo(time,location):
    # time = '2022-07-10 09-09-3'
    location = int(location)
    # time = int(time.strftime('%Y%m%d%H%M%S'))
    # location = 40
    dir = 'video'
    FileList = []

    for s in os.listdir(dir):
        subdir = os.path.join(dir, s)
        FileList.append(os.path.basename(subdir))
    # print(FileList)
    for path in FileList:
        t = int(path[0:14])
        if 0 < time - t < 30:  # 根据数字计算：123121到124121，过十分钟但是数字差1000
            break
        else:
            continue
    rec_dir = os.path.join(dir, path)
    print(rec_dir)
    print(str(time) + '   1')
    cap = cv2.VideoCapture(rec_dir)  # 打开视频文件


    # 创建保存视频文件类对象
    os.makedirs('record', exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc('X', 'V', 'I', 'D')
    out = cv2.VideoWriter('record/output-' + str(time) + '.avi', fourcc, 5, (1280,720))

    i = 0
    while True:
        success, frame = cap.read()
        if success:
            i += 1
            if i >= location - 30 and i <= location + 30:
                out.write(frame)
        else:
            break
    print('videoOK')
    cap.release()
    out.release()


def reviewVideoToWeb(iTime): #传入字符串类型时间 ‘2022-07-12 17_34_05’
    #将视频传到网页
    cap = cv2.VideoCapture('record/output-'+str(iTime)+'.avi')
    print(str(iTime)+'   1')
    while True:
        print(str(iTime)+'   2')
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame = buffer.tobytes()

            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def haveVideo(itime):
    filenames = os.listdir('record')
    for file in filenames:
        if file=='output-'+str(itime):
            return True
    return False