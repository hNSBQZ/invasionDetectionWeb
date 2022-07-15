import redis
class redisOperator():
    def __init__(self):
        self.r = redis.StrictRedis(host="127.0.0.1", port=6379, db=0,decode_responses=True)

    def setValue(self,email,code):
        self.r.hset(name=email, key="code", value=code)
        self.r.expire(email,120)

    def Judge(self,email,code):
        print("in redis")
        print(email,code)
        datalist=self.r.hmget(email, "code")
        if datalist[0]==code:
            self.r.hdel("code", code)
            return True
        return False

