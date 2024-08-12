package ci.benchMark;

import base.db.JSYDBUtils;
import java.util.List;
import java.util.Map;
import java.util.Queue;

/**
 * @author sunmuchao
 * @date 2023/11/23 2:17 下午
 */

//负责传递给它用例名 old版本 和 new版本 他会得到上升、下降等
public class BenchMarkComparator_bak {

    /*public void rise(String caseName, Queue<PR> prQueue, BenchMarkResult benchMarkResult) {
        ComparateOperator comparateOperator = new ComparateOperator();
        while(prQueue.size() > 0) {
            comparateOperator.rise(caseName, prQueue.poll(), benchMarkResult);
        }
    }*/


    /*public List<Map<String, String>> getFails(String caseName, PR pr){
        caseName = caseName + ".pls";
        List<Map<String, String>> fails = JSYDBUtils.query("select caseName,errorInfo from benchmarkResult where codeType = \"" + pr.getCodeType() + "\" and prid = \"" + pr.getPrId() + "\" and caseName = \"" + caseName +"\" and (conFailedCount > 0 || errorInfo != null || measureTime = 0)","caseName","errorInfo");
        return fails;
    }

    public List<Map<String, String>> getReduceds(String caseName, PR newPr, PR oldPr) {
        caseName = caseName + ".pls";
        List<Map<String, String>> reducedPerfs = JSYDBUtils.query("SELECT br1.caseName, br1.measureTime, br2.measureTime\n" +
                "FROM benchmarkResult br1\n" +
                "JOIN benchmarkResult br2 ON br1.caseName = br2.caseName\n" +
                "WHERE \n" +
                "    caseName = \"" + caseName + "\"\n" +
                "    AND codeType = \"" + newPr.getCodeType() + "\"\n" +
                "    AND (br1.prid = " + oldPr.getPrId() + " AND br1.measureTime != 0)\n" +
                "    AND (br2.prid = " + newPr.getPrId() + " AND br2.measureTime != 0)\n" +
                "    AND (\n" +
                "        SELECT br1.measureTime\n" +
                "        FROM benchmarkResult br1\n" +
                "        WHERE br1.prid = " + oldPr.getPrId() + "\n" +
                "    ) < 0.87 * (\n" +
                "        SELECT br2.measureTime\n" +
                "        FROM benchmarkResult br2\n" +
                "        WHERE br2.prid = " + newPr.getPrId() + "\n" +
                "    )\n" +
                "    AND ABS(\n" +
                "        (\n" +
                "            SELECT br2.measureTime\n" +
                "            FROM benchmarkResult br2\n" +
                "            WHERE br2.prid = " + newPr.getPrId() + "\n" +
                "        ) - (\n" +
                "            SELECT br1.measureTime\n" +
                "            FROM benchmarkResult br1\n" +
                "            WHERE br1.prid = " +oldPr.getPrId() + "\n" +
                "        )\n" +
                "    ) > 100;\n", "caseName", "oldMeasureTime", "newMeasureTime");
        return reducedPerfs;
    }

    public List<Map<String, String>> getRises(String caseName, PR newPr, PR oldPr){
        caseName = caseName + ".pls";
        List<Map<String, String>> risePerfs = JSYDBUtils.query("SELECT br1.caseName, br1.measureTime, br2.measureTime\n" +
                "FROM benchmarkResult br1\n" +
                "JOIN benchmarkResult br2 ON br1.caseName = br2.caseName\n" +
                "WHERE \n" +
                "    caseName = \"" + caseName + "\"\n" +
                "    codeType = \"" + newPr.getCodeType() + "\"\n" +
                "    AND (br1.prid = " + oldPr.getPrId() + " AND br1.measureTime != 0)\n" +
                "    AND (br2.prid = " + newPr.getPrId() + " AND br2.measureTime != 0)\n" +
                "    AND (br1.measureTime * 0.87 > 100)\n" +
                "    AND (\n" +
                "        SELECT br1.measureTime\n" +
                "        FROM benchmarkResult br1\n" +
                "        WHERE br1.prid = " + oldPr.getPrId() + "\n" +
                "    ) > 1.13 * (\n" +
                "        SELECT br2.measureTime\n" +
                "        FROM benchmarkResult br2\n" +
                "        WHERE br2.prid = " + newPr.getPrId() + "\n" +
                "    )\n" +
                "    AND ABS(\n" +
                "        (\n" +
                "            SELECT br2.measureTime\n" +
                "            FROM benchmarkResult br2\n" +
                "            WHERE br2.prid = " + newPr.getPrId() + "\n" +
                "        ) - (\n" +
                "            SELECT br1.measureTime\n" +
                "            FROM benchmarkResult br1\n" +
                "            WHERE br1.prid = " +oldPr.getPrId() + "\n" +
                "        )\n" +
                "    ) > 100;\n", "caseName", "oldMeasureTime", "newMeasureTime");
        return risePerfs;
    }*/

}
