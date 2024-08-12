#!/usr/bin/python
#-*-coding:utf-8-*-
import sys
import jenkins

def loginjenkins1(job,builder,prId,displayId,dataType):
    server = jenkins.Jenkins('http://192.168.5.110:8080', username='Huijie', password='58342And5306@')
    displayId = displayId.split('/')[0]
    param_dict = {"builder": builder, "prId": prId, "displayId": displayId, "dataType": dataType}
    ret = server.build_job('515Intergration/' + job, param_dict)
    print(ret)

def loginjenkins2(job,builder,prId,displayId,isOnlyHihidataChange):
    server = jenkins.Jenkins('http://192.168.5.110:8080', username='Huijie', password='58342And5306@')
    param_dict = {"builder": builder, "prId": prId, "branch": displayId, "isOnlyHihidataChange": isOnlyHihidataChange}
    ret = server.build_job('515Intergration/' + job, param_dict)
    print(ret)

def main():
    #参数: job 构建触发者 prId 合并分支 数据类型
    if "benchmark" in sys.argv[1]:
        loginjenkins1(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
    else:
        loginjenkins2(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
if __name__ == "__main__" :
    main()