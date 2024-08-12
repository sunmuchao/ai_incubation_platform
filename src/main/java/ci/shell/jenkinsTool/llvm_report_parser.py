# -*- coding: utf-8 -*-

from xml.dom.minidom import parse

def parser_xml_report(file_path):
    """
    解析xml文件中的类名和测试结果
    :param file_path: 文件路径
    :return: 类名，测试详情(字典)，每条用例结果(列表)
    """
    # 文档根元素
    dom = parse(file_path)
    root = dom.documentElement
    testcase_list = root.getElementsByTagName("testcase")
    run = len(testcase_list)
    failures = 0
    errors = 0
    skipped = 0
    for testcase in testcase_list:
        if len(testcase.getElementsByTagName("failure")):
            failures += 1
        if len(testcase.getElementsByTagName("error")):
            errors += 1
        if len(testcase.getElementsByTagName("skipped")):
            skipped += 1

    test_info = {
        "run": run,
        "Failures": failures,
        "Errors": errors,
        "Skipped": skipped
    }
    return test_info



if __name__ == '__main__':
    test_info = parser_xml_report("./test.xml")
    tests = test_info["run"]
    failures = test_info["Failures"]
    errors = test_info["Errors"]
    skipped = test_info["Skipped"]
    if tests == 0 :
        success_rate=0
    else:
        success_rate = (tests-failures)/tests
        success_rate = round(success_rate,5)
        success_rate = str(success_rate * 100) + '%\n'
    inject_variables = f"Tests={tests}\nFailures={failures}\nSkipped={skipped}\nSuccessRate={success_rate}"
    with open("./inject_variables.properties", "w") as file:
        file.truncate()
        file.write(inject_variables)