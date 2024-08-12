/*
package updateBlood.UpdateProcessor;
import com.google.common.graph.MutableGraph;
import updateBlood.GraphUtils;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

*/
/**
 * @author sunmuchao
 * @date 2023/7/19 2:14 下午
 *//*

public class NodeWaitStatistics implements UpdateProcessor {
    private GraphUtils graphUtils;
    private Map<String,Integer> csvMapping;

    public NodeWaitStatistics(GraphUtils graphUtils, Map<String,Integer> csvMapping) {
        this.graphUtils = graphUtils;
        this.csvMapping = csvMapping;
    }

    @Override
    public StringBuffer process(MutableGraph<String> graph, List<String[]> csvList, String dagid) throws ParseException {
        StringBuffer sql = new StringBuffer();
        for (String[] fields : csvList) {
            String curTableId = fields[csvMapping.get("tableId")] + "_" + fields[csvMapping.get("dataModify")];
            Set<String> successors = graphUtils.getAllpredecessors(graph, curTableId);
            Iterator it = successors.iterator();
            long latestPreTableTs = Integer.MIN_VALUE;
            String latestPreTableId = null;
            SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

            while (it.hasNext()) {
                String preTableId = (String) it.next();
                for (String[] fields3 : csvList) {
                    String tableId = fields3[csvMapping.get("tableId")];
                    if (preTableId.contains(tableId)) {
                        //获取tableid的耗时，
                        long endTime = simpleDateFormat.parse(fields3[csvMapping.get("endTime")]).getTime();
                        if (endTime > latestPreTableTs) {
                            latestPreTableTs = endTime;
                            latestPreTableId = preTableId;
                        }

                        break;
                    }
                }
            }

            //插入当天时间，用于之后的数据分析
            if (latestPreTableId != null) {
                sql.append("INSERT INTO  updatepredecessors (time, dagid, latestPreTableId, curTableId, latestPreTableTs, beginTime) VALUES('" +
                        new SimpleDateFormat("YYYY-MM-dd").format(new Date()) + "','"  + dagid + "','" + latestPreTableId + "','" + curTableId + "','" + latestPreTableTs + "','" + fields[csvMapping.get("beginTime")] + "');\n");
                System.out.println("INSERT INTO  updatepredecessors (time, dagid, latestPreTableId, curTableId, latestPreTableTs, beginTime) VALUES('" +
                        new SimpleDateFormat("YYYY-MM-dd").format(new Date()) + "','"  + dagid + "','" + latestPreTableId + "','" + curTableId + "','" + latestPreTableTs + "','" + fields[csvMapping.get("beginTime")] + "');\n");
            }
        }
        return sql;
    }
}
*/
