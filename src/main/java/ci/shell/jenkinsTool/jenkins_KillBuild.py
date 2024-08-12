#!/usr/bin/python3
#-*-coding:utf-8-*-
import sys
import jenkins
def killRepeatBuild(displayId,prId):
    job_names = []
    server = jenkins.Jenkins('http://192.168.5.110:8080', username='Frank.Niu', password='Maxnxl555!')
    if displayId == "feature":
        job_names.append('polars_test11_release','polars_test_release')
    elif displayId == "release":
        job_names.append('polars_test_feature','polars_test11_feature')
    elif displayId == "persist":
        job_names.append('polars_test_persist','polars_test11_persist')

    for job_name in job_names:
        #获取排队任务的prid
        queueItem = server.get_job_info('515Intergration/' + job_name).get('queueItem')
        if queueItem != None:
            build_number = int(queueItem['why'].split("#")[1].split(' ')[0]) + 1
            params = queueItem['params']
            if prId == params.split('\n')[3].split('=')[1]:
                server.delete_build('515Intergration/' + job_name, build_number)

        #获取正在运行的任务的prid
        running_job_number = server.get_job_info('515Intergration/' + job_name).get('lastSuccessfulBuild')['number']
        params = server.get_build_info('515Intergration/' + job_name,running_job_number)['actions'][0]['parameters']
        for param in params:
            if param['name'] == "prId":
                if prId == param['value']:
                    server.delete_build('515Intergration/' + job_name, running_job_number)

def main():
    #参数: 合并分支 sys.argv[1]
    displayId = sys.argv[1]
    prId = sys.argv[2]
    killRepeatBuild(displayId,prId)

if __name__ == "__main__" :
    main()