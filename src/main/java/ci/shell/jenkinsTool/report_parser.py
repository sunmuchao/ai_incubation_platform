# -*- coding: utf-8 -*-
"""
集成测试执行结束后会在target/site目录下生成surefire-report.html
此脚本解析surefire-report.html文件中的测试结果信息
生成一个inject_variables.properties文件，用于jenkins注入变量，最后通过企业微信发送通知
用法：此脚本需要放到polars-integration-test目录下，执行python3 polars_report_parser.py
"""
from cgi import test
from lxml import etree
from glob import glob

tests = 0
failures = 0
skipped = 0
success_rate = 0.0


def find_success(path):
    global tests,failures,skipped,success_rate
    try:
        with open("./"+path, "r", encoding="utf8") as f:
            report = f.read()

        html = etree.HTML(report)
        summary = html.xpath('//*[@id="contentBox"]/section[2]/table/tr[2]/td')
        tests += int(summary[0].text)
        errors = int(summary[1].text)
        failures += int(summary[2].text) + int(errors)
        skipped += int(summary[3].text)
        if(int(summary[2].text)!=0):
            print("int(summary[2].text)不为0"+path)
        if(int(errors)!=0):
            print("error不为0"+path)
    except Exception as e:
        print(str(e))

def main():
    global tests,failures,skipped,success_rate
    print("开始找path")
    paths = glob(r'./*/target/site/surefire-report.html')
    for path in paths:
        print(path)
        find_success(path)
    if tests == 0 :
        success_rate=0
    else:
        success_rate = (tests-failures)/tests
        success_rate = round(success_rate,5)
        success_rate = str(success_rate * 100) + '%\n'

    inject_variables = f"Tests={tests}\nFailures={failures}\nSkipped={skipped}\nSuccessRate={success_rate}"
    print(inject_variables)
    with open("inject_variables.properties", 'w', encoding="utf8") as f:
        f.write(inject_variables)


if __name__== "__main__" :
    main()