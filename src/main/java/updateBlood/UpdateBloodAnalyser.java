/*
package updateBlood;

import base.db.PgDBUtils;
import com.google.common.graph.MutableGraph;
import com.opencsv.CSVReader;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.SQLException;
import java.util.Map;

public class UpdateBloodAnalyser {

    public static void main(String[] args) throws IOException, SQLException {
        int sqlCount = 0;
        //String csvPath = "/Users/sunmuchao/Downloads/fine_intelli_consume_point_datalake_4.csv";
        String csvPath = args[0];
        GraphUtils graphUtils = new GraphUtils();
        Map<String, MutableGraph<String>> updateNetworks = graphUtils.createGraphs(csvPath);
        PgDBUtils dbUtils = new PgDBUtils("jdbc:postgresql://124.70.154.253:5432/coding","jsyread","xOS3LVk1qsXN2pgf");
        CSVReader csvReader = new CSVReader(Files.newBufferedReader(Paths.get(csvPath)));
        String[] fields = csvReader.readNext();
        StringBuffer sql = new StringBuffer();
        while ((fields = csvReader.readNext()) != null) {
            String dagid = fields[0];
            MutableGraph<String> graph = updateNetworks.get(dagid);
            String curTableId = fields[2];
            graphUtils.traverseSuccessor(graph, curTableId, 0);
            //获取当前表的所有血缘路径所包含的节点数
            Map<String, Integer> successorNodes = graphUtils.successorNodes;
            for (Map.Entry<String, Integer> entry : successorNodes.entrySet()) {
                String leftNodeTableId = entry.getKey();
                int pathContainNodes  = entry.getValue();
                sql.append("INSERT INTO updateBlood (dagid,tableid,leafnode_tableid,path_contain_nodes) VALUES('" +  dagid + "','" +  curTableId + "','" + leftNodeTableId + "'," + pathContainNodes + ");\n");
                sqlCount++;
            }
            //获取父表数
            int parenttableNumber = graphUtils.getAllPredecessors(graph, curTableId, 0);
            sql.append("INSERT INTO updateParentBlood (dagid,tableid,parenttables) VALUES('" +  dagid + "','" +  curTableId + "'," + parenttableNumber + ");\n");
            sqlCount++;
            if(sqlCount >= 100000){
                dbUtils.insertData(sql);
                sql = new StringBuffer();
            }
        }
        dbUtils.insertData(sql);
        dbUtils.closeDBConn();
    }
}
*/