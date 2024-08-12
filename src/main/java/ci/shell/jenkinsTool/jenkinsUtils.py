#!/usr/bin/python3
#-*-coding:utf-8-*-
import sys
import jenkins
def getParallelBranchesNumber(displayId):
    server = jenkins.Jenkins('http://192.168.5.110:8080', username='Sun.Sun', password='sunmuchao980320$$')
    jobs = server.get_all_jobs(1)
    parallelBranchesNumber = 0
    subString = "polars_test_" + displayId
    for job in jobs:
        #根据displayId模糊匹配job名
        if subString in job['name']:
            #print(job['name'])
            parallelBranchesNumber = parallelBranchesNumber + 1
    print(parallelBranchesNumber)

def main():
    #参数: 合并分支 sys.argv[1]
    #displayId = sys.argv[1]
    displayId = "feature"
    getParallelBranchesNumber(displayId)

if __name__ == "__main__" :
    main()