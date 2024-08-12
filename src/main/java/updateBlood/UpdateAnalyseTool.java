/*
package updateBlood;

import base.db.PgDBUtils;
import com.google.common.graph.MutableGraph;
import com.opencsv.CSVReader;
import updateBlood.UpdateProcessor.LayerWidthStatistics;
import updateBlood.UpdateProcessor.LongsetBloodStatistics;
import updateBlood.UpdateProcessor.NodeWaitStatistics;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.SQLException;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

*/
/**
 * @author sunmuchao
 * @date 2023/7/18 5:08 下午
 *//*

public class UpdateAnalyseTool {
    public static void main(String[] args) {
        PgDBUtils dbUtils = new PgDBUtils("jdbc:postgresql://124.70.154.253:5432/sun", "sun", "WLSFKMmt66");
        StringBuffer sql = new StringBuffer();

        //用于记录csv中字段的位置
        Map<String,Integer> csvMapping = new HashMap<>();
        //String dagidPath = args[0];
        String dagidPath = "/Users/sunmuchao/Downloads/csv/csv/";
        try {
            //结果写入的数据库
            //Exportor exportor = new Exportor(dagidPath,csvMapping);
            //exportor.export();

            //将目录下所有文件转成图
            GraphUtils graphUtils = new GraphUtils(dagidPath,csvMapping);

            List<String[]> csvList = new ArrayList<>();

            Map<String, MutableGraph<String>> updateNetworks = graphUtils.updateNetworks;
            NodeWaitStatistics nodeWaitStatistics = new NodeWaitStatistics(graphUtils, csvMapping);
            LayerWidthStatistics layerWidthStatistics = new LayerWidthStatistics(graphUtils, csvMapping);
            LongsetBloodStatistics longsetBloodStatistics = new LongsetBloodStatistics(graphUtils, csvMapping);

            Iterator<Entry<String, MutableGraph<String>>> iterator = updateNetworks.entrySet().iterator();
            int sqlCount = 0;
            while (iterator.hasNext()) {
                Entry<String, MutableGraph<String>> updateNetwork = iterator.next();
                String dagid = updateNetwork.getKey();
                MutableGraph<String> graph = updateNetwork.getValue();
                //从csv文件中获取
                CSVReader csvReader = new CSVReader(Files.newBufferedReader(Paths.get(dagidPath + dagid + ".csv")));
                String[] fields;
                //先放入内存中进行加速
                while ((fields = csvReader.readNext()) != null) {
                    csvList.add(fields);
                }

                //串行执行各个计算方法
                //方法只传递graphUtils，所有处理均在计算中解决
                //1.更新逻辑的合理性 : https://kms.fineres.com/pages/viewpage.action?pageId=735320209
                sql.append(nodeWaitStatistics.process(graph, csvList, dagid));
                sqlCount++;

                //2.层宽统计
                sql.append(layerWidthStatistics.process(graph, csvList, dagid));
                sqlCount++;

                //3.最长血缘统计
                sql.append(longsetBloodStatistics.process(graph, csvList, dagid));
                sqlCount++;

                if (sqlCount >= 1000) {
                    dbUtils.insertData(sql);
                    sql = new StringBuffer();
                    sqlCount = 0;
                }

                //释放内存中存储的数据
                csvList = new ArrayList<>();
            }


        } catch (IOException | SQLException | ParseException e) {
            e.printStackTrace();
        } finally {
            try {
                dbUtils.insertData(sql);
                dbUtils.closeDBConn();
                File directory = new File(dagidPath);
                File[] files = directory.listFiles();
                //删除所有的csv文件
                for (File file : files) {
                    if(file.delete()){
                        System.out.println("删除文件" + file.getName() + "成功!!");
                    }else {
                        //System.out.println("删除文件" + file.getName() + "失败!!");
                    }
                }

            } catch (SQLException throwables) {
                throwables.printStackTrace();
            }
        }
    }
}
*/
