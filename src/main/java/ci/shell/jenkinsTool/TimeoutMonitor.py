#!/usr/bin/python
#-*-coding:utf-8-*-
import sys
import time

import jenkins
import requests


def monitorTimeOut():
    # dict = {job:lastBuildNumber+"_"+estimatedFinishTime}
    dict = {}
    server = jenkins.Jenkins('http://192.168.5.110:8080', username='Sun.Sun', password='fr305239')
    #jobs = ["polars_test-benchmark","polars_test_feature","polars_test11_feature","polars_test_persist","polars_test11_persist","polars_test_release","polars_test11_release","polars_test_simple_cluster"]
    jobs = ["polars_test-benchmark", "polars_test_feature", "polars_test11_feature", "polars_test_release", "polars_test11_release", "polars_test_simple_cluster"]
    while True:
        for job in jobs:
            if dict.get(job) :
                lastBuildNumber = int(dict.get(job).split("_")[0])
                estimatedFinishTime = int(dict.get(job).split("_")[1])
                if time.time()*1000 >= estimatedFinishTime :
                    print("当前时间:" + str(time.time() * 1000))
                    if lastBuildNumber == server.get_job_info('515Intergration/'+job)['lastBuild']['number'] :
                        print(job+"分支进入阻塞状态")
                        send_message(job+"分支进入阻塞状态")
                        time.sleep(3600)
            else :
                print('515Intergration/'+job)
                lastBuildNumber = server.get_job_info('515Intergration/'+job)['lastBuild']['number']
                if server.get_build_info('515Intergration/'+job, lastBuildNumber)['building'] :
                    estimatedDuration = server.get_build_info('515Intergration/'+job, lastBuildNumber)['estimatedDuration']
                    print("预估持续时间:"+str(estimatedDuration))
                    startTimeTamp = server.get_build_info('515Intergration/'+job, lastBuildNumber)['timestamp']
                    print("启动时间:"+str(startTimeTamp))
                    estimatedFinishTime = startTimeTamp + estimatedDuration + 1200000
                    print("预估结束时间"+str(estimatedFinishTime))
                    dict[job] = str(lastBuildNumber)+"_"+str(estimatedFinishTime)

        time.sleep(10)

def send_message(msg):
    """
    使用机器人api发送消息
    :param msg: markdown格式的文本
    :param key: 机器人key
    """
    webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0e8df370-dac0-45de-84e7-a2ee049ad34a'
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": msg
        }
    }
    requests.post(webhook, json=data)

def main():
    monitorTimeOut()
if __name__ == "__main__" :
    main()