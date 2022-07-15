import pymysql

class DBOperator:
    def __init__(self):
        server = 'localhost'
        user='root'
        password = '123456'
        database = 'app'
        self.conn=pymysql.connect(host=server,user=user,password=password,db=database,autocommit=True,charset='utf8')
        if self.conn:
            print("连接成功")
        self.cursor = self.conn.cursor(cursor=pymysql.cursors.DictCursor)

    def addUser(self,userName,password,name,level,email):
        sql = "insert into users(userName, password, name, level,email)values('%s','%s','%s',%d,'%s')" %(userName, password,name,int(level),email)
        self.cursor.execute(sql)

    def deleteUser(self,userName):
        sql="delete from users where userName='%s'"%userName
        self.cursor.execute(sql)

    def setLevel(self,userName,level):
        sql="update users set level=%s where userName='%s'"%(level,userName)
        print(sql)
        self.cursor.execute(sql)

    def checkPassword(self,userName,password):
        sql="select password from users where userName='%s'"%userName
        self.cursor.execute(sql)
        dataList=self.cursor.fetchall()
        if len(dataList)==0:
            return False
        if dataList[0]['password']==password:
            return True
        return False

    def searchUser(self,partOfUserName):
        print("good")
        sql="select * from users where userName like '%"+partOfUserName+"%'"
        print(sql)
        self.cursor.execute(sql)
        dataList=self.cursor.fetchall()
        return dataList

    def selectUser(self):
        sql="select userName,name,level from users"
        self.cursor.execute(sql)
        dataList=self.cursor.fetchall()
        return dataList

    def haveUser(self,user):
        sql="select userName from users"
        self.cursor.execute(sql)
        dataList=self.cursor.fetchall()
        for userName in dataList:
            if userName['userName']==user:
                return True
        return False

    def changePassword(self, userName, password):
        sql = "update users set password ='%s' where userName = '%s'" % (password, userName)
        self.cursor.execute(sql)

    def getUserInformation(self,userName):
        sql="select userName,name,level,email from users where userName='%s'"%(userName)
        self.cursor.execute(sql)
        dataList=self.cursor.fetchall()
        return dataList[0]

    def selectlevel(self,userName):
        sql = "select level from users where  userName = '%s'" % userName
        self.cursor.execute(sql)
        dataList = self.cursor.fetchall()
        return dataList

    def checkEmail(self,Email):
        sql="select email from users where email='%s'"%Email
        self.cursor.execute(sql)
        datalist=self.cursor.fetchall()
        if len(datalist):
            return True
        return False

    def getUserNameByEmail(self,email):
        sql="select userName from users where email='%s'"%email
        self.cursor.execute(sql)
        datalist = self.cursor.fetchall()
        return datalist[0]['userName']
