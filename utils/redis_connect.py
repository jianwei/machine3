import redis


class redis_connect ():
    def __init__(self):
        host='127.0.0.1'
        port= 6379
        password= ''
        db= 0
        self.redis_conn = redis.Redis(host=host, port= port, password=password, db= db)
    
    def set(self,key,value,ex=3600):
        self.redis_conn.set(key,value,ex)

    def get (self,key):
        value = self.redis_conn.get(key)
        if value : 
            return value.decode('utf-8')
        else:
            return ""