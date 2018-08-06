import qiniu

access_key = "yV4GmNBLOgQK-1Sn3o4jktGLFdFSrlywR2C-hvsW"
secret_key = "bixMURPL6tHjrb8QKVg2tm7n9k8C7vaOeQ4MEoeW"
bucket_name = "ihome"


def storage(data):
    try:
        q = qiniu.Auth(access_key, secret_key)
        key = None
        token = q.upload_token(bucket_name)
        ret, info = qiniu.put_data(token, key, data)
    except Exception as e:
        raise e
    if info.status_code != 200:
        raise Exception("上传图片失败")
    # 返回图片的key保存到本地的数据库，当做照片名称，通过key来查找图片
    return ret["key"]


if __name__ == '__main__':
    file = input("请输入文件路径：")
    with open(file, "rb") as f:
        storage(f.read())
